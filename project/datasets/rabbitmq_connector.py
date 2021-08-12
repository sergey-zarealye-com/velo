from typing import Dict, List
import asyncio
from typing import Any

import logging

from project import db
from project.models import Deduplication
from project.models import Version, DataItems, TmpTable

log = logging.getLogger(__name__)


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


def send_message(queue):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def func(queue):
        while True:
            print('waiting for message...')
            task_id, celery_task_id, create_missing_categories, cat_id = queue.get()  # blocking operation

            print("Add new image processing entry")
            new_task_entry = Deduplication(
                task_uid=task_id,
                celery_task_id=celery_task_id,
                create_missing_categories=create_missing_categories,
                set_category=cat_id
            )
            db.session.add(new_task_entry)
            db.session.commit()
            print("Added")

    loop.run_until_complete(func(queue))
