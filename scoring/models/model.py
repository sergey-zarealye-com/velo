"""Contains abstract class and common """

from typing import Any


class ClassificationModel:
    def __init__(self, *args, **kwargs):
        pass

    def score(self, *args, **kwargs) -> Any:
        raise NotImplementedError("Abstract class")
