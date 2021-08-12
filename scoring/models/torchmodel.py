from typing import List
import torch
from torch import nn
import logging


log = logging.getLogger(__name__)


class TorchModel(nn.Module):
    def __init__(self, model_path: str, device: str = 'cuda'):
        super().__init__()
        self.model_path = model_path
        self.device = device
        self.loaded = False

    def load_model(self):
        if not self.loaded:
            log.info(f'Loading model {self.model_path}...')
            self.model = torch.load(self.model_path, map_location=self.device)
            self.loaded = True

    def forward(self, x):
        return self.model(x)

    def score(self, dataloader, filepaths: List[str]):
        log.info('Scoring...')
        for batch, in dataloader:
            batch = batch.to(self.device)

            with torch.no_grad():
                log.info('Calculating predictions')
                predictions = self(batch).cpu().numpy()
                classes = predictions.argmax(-1)

        scores = [pred[cl] for pred, cl in zip(predictions, classes)]

        result = [
            {
                'filename': filename,
                'class': int(class_idx),
                'scores': float(score)
            }
            for filename, class_idx, score in zip(filepaths, classes, scores)
        ]

        return result
