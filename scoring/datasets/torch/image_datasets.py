from torch import Tensor
from torch.utils.data import TensorDataset, DataLoader
import cv2
import os

from .. import read_images


class ImageDataLoader(DataLoader):
    def __init__(
        self,
        dataset_path: str,
        batch_size: int,
        need_resize: bool,
        pin_memory: bool = True,
        num_workers: int = os.cpu_count()
    ) -> None:
        images, self.filepaths = read_images(dataset_path, need_resize)
        images = Tensor(images).permute(0, 3, 1, 2)
        self.dataset = TensorDataset(images)

        super().__init__(
            self.dataset,
            batch_size=batch_size,
            pin_memory=pin_memory,
            num_workers=num_workers,
            shuffle=False
        )
