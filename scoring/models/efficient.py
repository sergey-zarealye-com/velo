from typing import Dict, List, Tuple
from torch import nn
import torch
import numpy as np
from efficientnet_pytorch import EfficientNet
import logging

# from .model import ClassificationModel

log = logging.getLogger(__name__)


class EfficientModel(nn.Module):
    def __init__(self, name: str, checkpoint_dir: str, device: str, id_to_classname: Dict[int, str]):
        self.name = name

        nn.Module.__init__(self)
        self.model = EfficientNet.from_pretrained('efficientnet-b3')
        num_ftrs = self.model._fc.in_features
        self.model._fc = torch.nn.Linear(num_ftrs, 10)

        checkpoint = torch.load(checkpoint_dir, map_location=device)
        new_weights = {key.replace('module.', ''): value for key, value in checkpoint['model'].items()}
        self.model.load_state_dict(new_weights)

        self.device = device
        self.id_to_classname = id_to_classname
        self.mapping_classes = np.vectorize(self.id_to_classname.get)

    def forward(self, x):
        return self.model(x)

    def score(self, dataloader, filenames: List[str]) -> Dict[str, Tuple[str, float]]:
        log.info('Scoring...')
        for batch, in dataloader:
            batch = batch.to(self.device)

            with torch.no_grad():
                log.info('Calculating predictions')
                predictions = self(batch).cpu().numpy()
                print(predictions.shape)
                classes = predictions.argmax(-1)

        classnames = self.mapping_classes(predictions)
        scores = predictions[:, classes]

        result = {filename: (classname, score) for filename, classname, score in zip(filenames, classnames, scores)}

        return result
