import enum
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Dict, Union

from project.video_utils import ffmpeg_job

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


def get_data_samples(data_path: str, labels: Dict[str, int]) -> Generator[DataSample, None, None]:
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
    # если папка
    elif data_path.is_dir():
        for item in data_path.iterdir():
            if item.is_dir():
                label = item.name
                if label not in labels:
                    log.warning(f"Folder name {label} not in labels of current version")
                    continue
                for file in item.iterdir():
                    if file.is_file():
                        media_type = get_media_type(file)
                        sample = DataSample(str(file), labels[label], media_type)
                        yield sample
