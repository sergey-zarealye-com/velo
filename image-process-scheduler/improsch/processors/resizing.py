from typing import Iterable, List, Tuple, Union
import cv2


def resize(img, dst_size: Union[Tuple[int, int], List[int]]):
    return cv2.resize(img, tuple(dst_size))


def resize_batch(images: Iterable, dst_size: Union[Tuple[int, int], List[int]]) -> Iterable:
    return [resize(img, dst_size) for img in images]
