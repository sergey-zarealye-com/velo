import asyncio
import enum
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generator, Dict, List, Union
from multiprocessing import Process
import multiprocessing
from project.todo.rabbitmq_connector import send_message, get_message
from flask import flash
import os
import uuid
import shutil

from project.video_utils import ffmpeg_job

log = logging.getLogger(__name__)


sending_queue = multiprocessing.Queue()
sending_process = Process(
    target=send_message,
    args=('frames_extraction', sending_queue)
)
sending_process.start()

pulling_queue = multiprocessing.Queue()
print("Объявление ", id(pulling_queue))
pulling_process = Process(
    target=get_message,
    args=('frames_extraction_result', pulling_queue)
)
pulling_process.start()


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


def get_data_samples(data_path_str: str, labels: Dict[str, int], warnings: List[Any]) -> Generator[DataSample, None, None]:
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
                    warnings.append(f"Folder name {label} not in labels of current version")
                    continue
                for file in item.iterdir():
                    if file.is_file():
                        media_type = get_media_type(file)
                        sample = DataSample(str(file), labels[label], media_type)
                        yield sample
