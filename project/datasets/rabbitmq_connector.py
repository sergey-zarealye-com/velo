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


def fillup_tmp_table(
    label_ids: Dict[str, int],
    selected: str,
    src: str,
    version: Version,
    commit_batch: int = 1000,
    
) -> None:
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


def send_message(queue):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def func(queue):
        while True:
            print('waiting for message...')
            task_id, celery_task_id = queue.get()  # blocking operation

            new_task_entry = Deduplication(
                task_uid=task_id,
                celery_task_id=celery_task_id
            )
            db.session.add(new_task_entry)
            db.session.commit()

    loop.run_until_complete(func(queue))
