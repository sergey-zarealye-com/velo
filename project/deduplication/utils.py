from typing import Any, Dict, List
from celery import Celery
from celery.result import AsyncResult
import os

from project.models import Deduplication, DeduplicationStatus, DataItems, Version
from project.datasets.utils import fillup_tmp_table
from project import db


# TODO config?
redis_port = os.getenv('REDIS_PORT') or 6379
redis_port = int(redis_port)
app = Celery('improsch', backend=f'redis://localhost:{redis_port}/1', broker=f'redis://localhost:{redis_port}/1')


def create_image_processing_task(message) -> str:
    task = app.send_task('run.process', args=(message,))
    return task.task_id


def get_task_result(celery_task_id: str):
    task = AsyncResult(celery_task_id, app=app)

    if task.ready():
        return task.result

    return None


def get_task_state(celery_task_id: str):
    task = AsyncResult(celery_task_id, app=app)
    return task.state


def process_response(response: dict):
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

            updated_deduplication: List[Dict[str, Any]] = []

            for item_index, (path1, path2, similarity) in enumerate(deduplication_result):
                updated_deduplication.append({
                    'item_index': item_index,
                    'image1': path_to_id[path1],
                    'image2': path_to_id[path2],
                    'similarity': similarity,
                    'removed': False
                })

            response['deduplication'] = updated_deduplication

            task_entry.result = response
            task_entry.task_status = DeduplicationStatus.finished.value
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
            assert storage_dir
            label_ids = response['label_ds']
            selected_ds = response['selected_ds']
            version = Version.query.filter_by(name=selected_ds).first()
            fillup_tmp_table(
                label_ids,
                selected_ds,
                os.path.join(storage_dir, task_id),
                version,
                create_missing_categories=task_entry.create_missing_categories,
                version_name=selected_ds
            )
            task_entry.task_status = DeduplicationStatus.finished.value
            db.session.commit()

    return task_entry
