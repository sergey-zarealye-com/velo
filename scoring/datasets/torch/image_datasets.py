from typing import List
from torch import Tensor
from torch.utils.data import TensorDataset, DataLoader
import cv2
import os


def read_image(filename: str, need_resize: bool):
    image = cv2.imread(filename)

    if image is not None:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        if need_resize:
            image = cv2.resize(image, (256, 256))

    return image


class ImageDataLoader(DataLoader):
    def __init__(
        self,
        filepaths: List[str],
        batch_size: int,
        need_resize: bool,
        pin_memory: bool = True
    ) -> None:
        images = []
        filenames = []
        for name in filepaths:
            image = read_image(name, need_resize)
            if image is not None:
                images.append(image)
                filenames.append(name)

        images = Tensor(images).permute(0, 3, 1, 2)  # type: ignore
        self.dataset = TensorDataset(images)  # type: ignore
        self.filepaths = filenames

        super().__init__(
            self.dataset,
            batch_size=batch_size,
            pin_memory=pin_memory,
            num_workers=0,
            shuffle=False
        )

