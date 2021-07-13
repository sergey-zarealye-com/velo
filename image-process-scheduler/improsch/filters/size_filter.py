"""This module contains filter functions.
Every filter should get one item and return boolean value: True if item is okey and False if it rejects item."""
from typing import Tuple, Union, List
import numpy as np


def get_filter_by_min_size(min_size: Union[Tuple[int, int], List[int]]):
    def filter_func(img: np.ndarray):
        if img.shape[0] < min_size[0] or img.shape[1] < min_size[1]:
            return False
        return True

    return filter_func
