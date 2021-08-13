import logging
from math import ceil
from multiprocessing import Pool
from typing import Iterable, List

import numpy as np
import cv2

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def save_image(img: np.ndarray, filepath: str):
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    cv2.imwrite(filepath, img)


def save_all(images: Iterable[np.ndarray], filepaths: Iterable[str]):
    for img, filepath in zip(images, filepaths):
        try:
            save_image(img, filepath)
            logging.info(f"Saved image to {filepath}")
        except Exception as err:
            logging.error(f"Error while saving: {str(err)}")


def unpack_func_for_saving(argument):
    images, filepaths = argument
    return save_all(images, filepaths)


def save_multiprocess(
    images: List[np.ndarray],
    filepaths: List[str],
    pool_size: int,
    storage_path: str
) -> List[str]:
    """Save input images to the storage in 'task_id' folder

    Function uses multiprocessing pool for saving image by chunks.
    Args:
        images (List[np.ndarray]): input images
        filepaths (List[str]): filenames of images in same order
        task_id (str): name of folder to save images in
        pool_size (int): count of processes
        storage_path (str): path to storage

    Returns:
        List[str]: new path to save images
    """
    assert len(images) == len(filepaths), RuntimeError("Lengths of images and filepaths are different")
    log.info(f"Saving {len(images)} into storage {storage_path}")

    chunk_size = ceil(len(images) / pool_size)
    if chunk_size == 0:
        log.warning(f"No images to save")
        return []

    chunks = []

    for i in range(0, len(images), chunk_size):
        chunks.append((
            images[i:i + chunk_size],
            filepaths[i:i + chunk_size]
        ))

    pool = Pool(pool_size)
    pool.map(unpack_func_for_saving, chunks)
    pool.close()

    parted_filenames = []
    for filename in filepaths:
        filename = filename.replace(storage_path, '') 
        parted_filenames.append(filename)

    return parted_filenames
