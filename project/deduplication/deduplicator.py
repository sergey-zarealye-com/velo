"""Module to handle deduplication of images.
Includes model for features extraction and model for neighbours searching."""
from typing import Optional
import torch
import faiss
import numpy as np


class FeatureExtractor:
    pass


class ImageIndex:
    def __init__(self, index_path: Optional[str] = None,  feat_dim: Optional[int] = None):
        if not (index_path or feat_dim is not None):
            raise AttributeError()

        if index_path:
            self.index = faiss.read_index(index_path)
        else:
            self.index = faiss.index_factory(feat_dim, "Flat", faiss.METRIC_INNER_PRODUCT)

    def add_vectors(self, vectors):
        faiss.normalize_L2(np.array(vectors))
        self.index.add(vectors)

    def find_neighbours(self, vectors):
        faiss.normalize_L2(np.array(vectors))
        distances, indexes = self.index.search(vectors, 2)

        neighbours = []
        for i in range(distances.shape[0]):
            neighbours.append((i, indexes[i, 1], distances[i, 1]))

        neighbours.sort(key=lambda x: 1 - x[-1])

        return neighbours
