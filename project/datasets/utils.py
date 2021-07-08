import enum
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, List

from project.video_utils import ffmpeg_job

extensions = ['.jpg', '.png', '.bmp']

# TODO: в конфиг
OUT_DIR = Path("./tmp")
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
    category: str
    media_type: MediaType


def get_files_by_category(data_path: str) -> Tuple[str, List[str]]:
    data_path = Path(data_path)
    for item in data_path.iterdir():
        if item.is_dir():
            label = item.name
            files = []
            for file in item.iterdir():
                if file.is_file() and file.suffix in extensions:
                    files.append(str(file))
            yield label, files


def get_moderation_data(data_path: str):
    # TODO: check for source: s3, http, etc...
    data_path = Path(data_path)
    if data_path.is_file():
        return None, str(data_path)
    else:
        pass


def get_media_type(file: Path):
    if file.suffix in extensions:
        return MediaType.PHOTO
    return MediaType.VIDEO


def get_data_samples(data_path: str):
    data_path = Path(data_path)
    # если это один файл
    if data_path.is_file():
        # todo: check for data type
        media_type = get_media_type(data_path)
        if media_type == MediaType.VIDEO:
            files = ffmpeg_job(data_path, str(OUT_DIR))
            for file in files:
                sample = DataSample(file, str(), MediaType.VIDEO)
                yield sample
    elif data_path.is_dir():
        for item in data_path.iterdir():
            if item.is_dir():
                label = item.name
                for file in item.iterdir():
                    if file.is_file():
                        media_type = get_media_type(data_path)
                        sample = DataSample(str(file), label, media_type)
                        yield sample
