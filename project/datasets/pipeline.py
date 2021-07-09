from typing import Iterable, Tuple
import cv2
import numpy as np
from collections import namedtuple
import os
import tarfile
import uuid

from .exceptions import (
    ImageProcessingException,
    ResolutionException
)


Neighbours = namedtuple('Neighbours', ['index1', 'index2', 'distance'])


def resize(img: np.ndarray, dst_size: Tuple[int, int]) -> np.ndarray:
    """Resize single image and return it

    Args:
        img (np.ndarray): an image to resize

    Returns:
        np.ndarray: resized copy of image
    """
    return cv2.resize(img, dst_size)


def find_duplicates(images: Iterable) -> Tuple[Neighbours]:
    """Return tuple of pairs of image indexes with its distance

    Args:
        images (Iterable): Iterator over images as np.ndarray

    Returns:
        Tuple[Neighbours]: Containes pairs of image indexes in order of asscending by their distance
    """
    pass


def check_size(img: np.ndarray, min_size: Tuple[int, int]):
    """Raise exception if one of image sizes is less than defined by min_size

    Args:
        img (np.ndarray): image
        min_size (Tuple[int, int]): minimum size HxW

    Raises:
        ResolutionException: Exception contains error message
    """
    if img.shape[0] < min_size[0] or img.shape[1] < min_size[1]:
        raise ResolutionException(f"Wrong image size: {img.shape[:2]}, expected at least {min_size}")


def read(filenames: Iterable[str]) -> Iterable[np.ndarray]:
    """Read images

    Args:
        filenames (Iterable[str]): full path to images

    Returns:
        Iterable[np.ndarray]: np arrays of images
    """
    images = []

    for filename in filenames:
        img = cv2.imread(filename)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        images.append(img)

    return images


def pipeline(path: str, chunk_size: int):
    process_id = str(uuid.uuid4())
    # TODO remove constant path, place config string
    tmp_dir = '/storage1/mrowl/velo/static/tmp/'

    while process_id in os.listdir(tmp_dir):
        process_id = str(uuid.uuid4())

    if os.path.isfile(path):
        if not tarfile.is_tarfile(path):
            raise ValueError('Provided file is not supported. Supported formats:', 'Tar')

        try:
            tar = tarfile.open(path, mode='r')
        except Exception:
            raise ImageProcessingException(f"{path} is not a tar object")

        # TODO safe extraction
        tar.extractall(os.path.join(tmp_dir, process_id))

    elif os.path.isdir(path):
        pass
    # TODO process s3 bucket path
