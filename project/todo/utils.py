import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Dict

from project.datasets.utils import sending_queue, get_media_type, MediaType


def natural_sort(l):
    convert = lambda text: int(text) if text.isdigit() else text
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', str(key))]
    return sorted(l, key=alphanum_key)


def create_video_task(data_path_str: str, labels: Dict[str, int], cat, description, title, i) -> None:
    link_str = data_path_str
    data_path: Path = Path(data_path_str)
    # если это один файл
    media_type = get_media_type(data_path)
    if media_type == MediaType.VIDEO:
        storage_dir = os.getenv("MODERATION_STORAGE_DIR")
        assert storage_dir, "Variable STORAGE_DIR is not defined in .flaskenv!"

        task_id = str(uuid.uuid4())
        task_dir = os.path.join(storage_dir, task_id)
        os.mkdir(task_dir)

        thumbs_dir = os.path.join(task_dir, 'thumbs')
        os.mkdir(thumbs_dir)

        if data_path.is_file():
            dst_video_path = os.path.join(task_dir, data_path.name)
            shutil.copy(data_path, dst_video_path)
            input_fname = os.path.join(task_id, data_path.name)
        else:
            input_fname = link_str

        # поскольку воркер может быть запущен в контейнере, вмсето абсолютного пути хоста
        # отправляем только путь из task_id и имени файла/папки
        # воркер должен сам подставить абсолютный путь, основываясь на storage_dir из своего конфига
        sending_queue.put({
            "id": task_id,
            "thumbs_dir": os.path.join(task_id, 'thumbs'),
            "input_fname": input_fname,
            "input_fname_stem": data_path.stem,
            "img_ext": ".jpg",
            "cat": cat,
            "description": description,
            "title": title,
            "video_id": i
        })
        # log.info(f"Created task {task_id}")
    else:
        # log.error(f"File is not video")
        pass


