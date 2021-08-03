from typing import Dict, List, Tuple
import asyncio
from typing import Any

import aio_pika
import json
import os
import logging

from project import db
from project.models import Deduplication, DeduplicationStatus
from project.models import Version, DataItems, TmpTable
from project.datasets.utils import get_data_samples


log = logging.getLogger(__name__)


rabbit_login = os.getenv("RABBIT_LOGIN") or "guest"
rabbit_passw = os.getenv("RABBIT_PASSW") or "guest"
rabbit_port = os.getenv("RABBIT_PORT") or 5672
rabbit_host = os.getenv("RABBIT_HOST") or "127.0.0.1"
rabbit_port = int(rabbit_port)


def import_data(categories: List[str], objects: List[DataItems], selected: str, version: Version) -> None:
    try:
        db.session.bulk_save_objects(objects, return_defaults=True)
        tmp = [TmpTable(item_id=obj.id,
                        node_name=selected,
                        category_id=cat) for obj, cat in zip(objects, categories)]
        db.session.bulk_save_objects(tmp)
    except Exception as ex:
        log.error(ex)
        db.session.rollback()
    else:
        # change status to STAGE which means that version is not empty
        version.status = 2
        db.session.commit()
    return


def fillup_tmp_table(label_ids: Dict[str, int],
                     selected: str,
                     src: str,
                     version: Version,
                     commit_batch: int = 1000) -> None:
    """
    Заполнить временную таблицу
    функция проходит по указанной директории src, добавляет найденные файлы в таблицу DataItems,
    заполняет таблицу TmpTable
    """
    objects, categories = [], []
    warnings = []
    for sample in get_data_samples(src, label_ids, warnings):
        res = DataItems.query.filter_by(path=sample.path).first()
        if res:
            continue
        data_item = DataItems(path=sample.path)
        objects.append(data_item)
        categories.append(sample.category)
        if len(objects) == commit_batch:
            import_data(categories, objects, selected, version)
            objects.clear()
            categories.clear()
    if len(objects):
        import_data(categories, objects, selected, version)
        objects.clear()
        categories.clear()
    return


def send_message(queue_name: str, queue):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def func(loop, queue_name, queue):
        connection: Any = await aio_pika.connect_robust(
            f"amqp://{rabbit_login}:{rabbit_passw}@{rabbit_host}:{rabbit_port}/?heartbeat=3600",
            loop=loop
        )

        async with connection:
            channel = await connection.channel()

            while True:
                print('waiting for message...')
                task_id, message = queue.get()  # blocking operation
                print('got message', message)

                new_task_entry = Deduplication(
                    task_uid=task_id
                )
                db.session.add(new_task_entry)
                db.session.commit()

                await channel.default_exchange.publish(
                    aio_pika.Message(body=message.encode()),
                    routing_key=queue_name,
                )

    loop.run_until_complete(func(loop, queue_name, queue))


def get_message(queue_name: str, queue):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def func(loop, queue_name, queue):
        # TODO: убрать хардкод порта
        connection: Any = await aio_pika.connect_robust(
            f"amqp://{rabbit_login}:{rabbit_passw}@{rabbit_host}:{rabbit_port}/?heartbeat=3600", loop=loop,
            port=5672
        )

        async with connection:
            # Creating channel
            channel = await connection.channel()

            # Declaring queue
            rabbit_queue = await channel.declare_queue(queue_name, auto_delete=False)

            async with rabbit_queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        response = json.loads(message.body.decode('utf-8'))
                        task_id = response['id']
                        task_entry = Deduplication.query.filter_by(task_uid=task_id).first()

                        if task_entry:
                            if response['type'] == 'deduplication_result':
                                print('\tGot result:')
                                print(response)

                                deduplication_result = response['deduplication']
                                path_to_id: Dict[str, int] = {}

                                for path1, path2, _ in deduplication_result:
                                    path_to_id[path1] = DataItems.add_if_not_exists(path1)
                                    path_to_id[path2] = DataItems.add_if_not_exists(path2)

                                updated_deduplication: List[Tuple[str, str, int]] = []

                                for path1, path2, similarity in deduplication_result:
                                    updated_deduplication.append((
                                        path_to_id[path1],
                                        path_to_id[path2],
                                        similarity
                                    ))

                                response['deduplication'] = updated_deduplication

                                task_entry.result = response
                                task_entry.task_status = DeduplicationStatus.finished.value
                                queue.put(response)
                                db.session.commit()
                            elif response['type'] == 'status_update':
                                print('\t Got status update')
                                print(response)
                                task_entry.stages_status = response
                                db.session.commit()
                            elif response['type'] == 'merge_control':
                                print('MERGE CONTROL RESULT')
                            elif response['type'] == 'filtered':
                                print("\t\tFILTERED RESULT MESSAGE")
                                print("Result filenames", response["filenames"])
                                # TODO: handle exceptions, add s3 source
                                # вынести куда нибудь commit_batch
                                storage_dir = os.getenv('STORAGE_DIR')
                                label_ids = response['label_ds']
                                selected_ds = response['selected_ds']
                                version = Version.query.filter_by(name=selected_ds).first()
                                fillup_tmp_table(label_ids, selected_ds, os.path.join(storage_dir, task_id), version)
                                task_entry.task_status = DeduplicationStatus.finished.value
                                db.session.commit()

    loop.run_until_complete(func(loop, queue_name, queue))
