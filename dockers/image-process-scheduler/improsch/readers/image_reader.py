from typing import Callable, List, Optional, Tuple
import cv2
import numpy as np
import os
from PIL import Image
import logging


log = logging.getLogger(__name__)


def read_image_cv2(filepath: str, filter_func: Optional[Callable[[np.ndarray], bool]] = None) -> Optional[np.ndarray]:
    image = cv2.imread(filepath)

    if image is not None:
        if not filter_func or filter_func(image):
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            return image

    log.warning(f"Can't load image {filepath}")
    return None


def read_image_pil(filepath: str, filter_func: Optional[Callable[[np.ndarray], bool]] = None):
    try:
        image = Image.open(filepath)
    except Exception:
        return None

    if not filter_func or filter_func(image):
        return image


def get_image_reader(filter_func: Optional[Callable[[np.ndarray], bool]] = None):
    def read(data_dir: str) -> Tuple[List[np.ndarray], List[str]]:
        images: List[np.ndarray] = []
        imagenames = []

        for root, subdirs, files in os.walk(data_dir):
            filenames = map(lambda x: os.path.join(root, x), files)

            for filename in filenames:

                try:
                    img = cv2.imread(filename)
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

                    if not filter_func or filter_func(img):
                        images.append(img)
                        imagenames.append(filename)
                except Exception:
                    # TODO alerting
                    continue

        return images, imagenames

    return read


def get_image_reader_pil(filter_func: Optional[Callable[[np.ndarray], bool]] = None):
    def read(data_dir: str) -> Tuple[List[np.ndarray], List[str]]:
        images = []
        imagenames = []

        for root, subdirs, files in os.walk(data_dir):
            filenames = map(lambda x: os.path.join(root, x), files)

            for filename in filenames:

                try:
                    img = Image.open(filename)

                    if not filter_func or filter_func(img):
                        images.append(img)
                        imagenames.append(filename)
                except Exception:
                    # TODO alerting
                    continue

        return images, imagenames

    return read
