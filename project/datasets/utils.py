from typing import Generator, Dict, List, Optional, Union, Any
import enum
import logging
from dataclasses import dataclass
from pathlib import Path
from random import shuffle
from project import db
from project.models import Version, Category, DataItems, TmpTable
from multiprocessing import Queue
import time
import sys
from random import shuffle
from project.models import Deduplication, DeduplicationStatus
import os


log = logging.getLogger(__name__)


image_extensions = ['.jpg', '.png', '.bmp']
audio_extensions = ['.mp3', '.wav']

# TODO: в конфиг
OUT_DIR = Path("./project/static/images/tmp")
if not OUT_DIR.exists():
    OUT_DIR.mkdir()


class MediaType(str, enum.Enum):
    VIDEO = "VIDEO"
    TEXT = "TEXT"
    PHOTO = "PHOTO"
    AUDIO = "AUDIO"

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_


@dataclass
class DataSample:
    path: str
    category: Union[str, int]
    media_type: MediaType


def get_media_type(file: Path) -> MediaType:
    if file.suffix in image_extensions:
        return MediaType.PHOTO
    elif file.suffix in audio_extensions:
        return MediaType.AUDIO
    return MediaType.VIDEO


def add_cv_catregory(version_name: str, category_name: str) -> int:
    version = Version.query.filter_by(name=version_name).first()

    if not version:
        raise RuntimeError(f"Can't add category to unexisted version {version_name}")

    category = Category(name=category_name, version_id=version.id, task=1)
    db.session.add(category)
    db.session.flush()

    db.session.commit()

    return category.id


def import_data(categories: List[Union[str, int]], objects: List[DataItems], selected: str, version: Version) -> None:
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
    create_missing_categories: bool = False,
    version_name: Optional[str] = None
) -> None:
    """
    Заполнить временную таблицу
    функция проходит по указанной директории src, добавляет найденные файлы в таблицу DataItems,
    заполняет таблицу TmpTable
    """
    objects, categories = [], []
    for sample in get_data_samples(
        src,
        label_ids,
        force_creating_categories=create_missing_categories,
        version_name=version_name
    ):
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


def get_data_samples(
    data_path_str: str,
    labels: Dict[str, int],
    force_creating_categories: bool = False,
    version_name: Optional[str] = None
) -> Generator[DataSample, None, None]:
    data_path: Path = Path(data_path_str)
    # # если это один файл
    if data_path.is_file():
        pass
    # ToDO добавить обработку, если указанная директория без подпапок
    #  (просто хранит файлы заданной категории)
    if data_path.is_dir():
        for item in data_path.iterdir():
            if item.is_dir():
                label = item.name
                if label not in labels:
                    log.warning(f"Folder name {label} not in labels of current version")

                    if force_creating_categories:
                        assert version_name, ValueError(
                            "version_name can't be None or '' if set flag force_creating_categories"
                        )

                    new_category_id = add_cv_catregory(version_name, label)  # type: ignore
                    labels[label] = new_category_id
                for file in item.iterdir():
                    if file.is_file():
                        media_type = get_media_type(file)
                        sample = DataSample(str(file), labels[label], media_type)
                        yield sample


def split_data_items(items: List[DataItems], train_size: float = 0.7, val_size: float = 0.1, test_size: float = 0.2):
    if train_size + val_size + test_size != 1:
        log.error("Sum of train, test, val size must be equal to 1")
    elif len(items) < 5:
        log.error("Too small items")
    else:
        shuffle(items)
        t = int(len(items) * train_size)
        v = int(len(items) * val_size)
        if v == 0:
            v += 1
        train_items = items[0:t]
        val_items = items[t:t + v]
        test_items = items[t + v:]
        return train_items, val_items, test_items


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


class TaskManager:
    def __init__(self, queue):
        self.tasks = []
        self.queue: Queue = queue

    def run(self):
        print('\tTaskManager started!')
        sys.stdout.flush()
        while True:
            while not self.queue.empty():
                print('New task!')
                sys.stdout.flush()
                task = self.queue.get()
                self.tasks.append(task)

            sys.stdout.flush()

            for i, task in enumerate(self.tasks):
                if task.ready():
                    print(f'Task {task} is ready!')
                    response = task.result
                    process_response(response)

                    del self.tasks[i]
                    break

            sys.stdout.flush()
            time.sleep(1.)
