import enum
import logging
from dataclasses import dataclass
from pathlib import Path
from random import shuffle
from typing import Any, Generator, Dict, List, Union

from project.models import DataItems

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


def get_data_samples(data_path_str: str, labels: Dict[str, int], warnings: List[Any]) -> Generator[
    DataSample, None, None]:
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
        print()

if __name__ == '__main__':
    import pickle

    with open("items.pkl", "rb") as f:
        items = pickle.load(f)

    split_data_items(items)
