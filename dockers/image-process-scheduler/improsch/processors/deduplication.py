"""Module to handle deduplication of images.
Includes model for features extraction and model for neighbours searching."""
from functools import partial
import logging
from multiprocessing import Pool
import os
from threading import Thread
from typing import Dict, List, Optional, Tuple, Union

import cv2
import faiss
import json
import numpy as np
import torch
import torchvision
from torchvision import transforms
import imagehash
from copy import deepcopy
import logging
import argparse
import json
import torch


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


CONFIG_NAME = 'config.json'
FILENAMES_JSON_NAME = 'ids_to_filenames.json'
TMP_FILENAMES_JSON_NAME = 'tmp_ids_to_filenames.json'


class FeatureExtractor:
    pass


class NNfeatureExtractor(FeatureExtractor, torch.nn.Module):
    def __init__(self, torch_model_name: str, repo: str = 'pytorch/vision:v0.10.0'):
        if torch_model_name != 'googlenet':
            raise AttributeError("Not supported model:", torch_model_name)

        torch.nn.Module.__init__(self)
        print('\t\tIS CUDA AVAILABLE', torch.cuda.is_available())

        # self.model = torch.hub.load(
        #     repo,
        #     torch_model_name,
        #     pretrained=True
        # )
        self.model = torchvision.models.googlenet(pretrained=True)
        self.model.eval()
        self.model.fc = torch.nn.Identity()

        self.preprocess = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])

    def get_embeddings(
            self,
            images: np.ndarray,
            batch_size: int,
            device: str = 'cpu'
            # device: str = 'cpu'
    ) -> np.ndarray:
        # if not isinstance(images, torch.Tensor):
        #     images = torch.Tensor(images).permute(0, 3, 1, 2)
        print('\tCalculating on', device)
        import sys
        sys.stdout.flush()

        print('\tTRYING TO PREPROCESS')
        print('\tCONUT OF IMAGES:', len(images))
        print('\tSHAPES:', images[0].shape, images[1].shape)
        sys.stdout.flush()
        images = torch.stack([self.preprocess(img) for img in images])
        print('\tIMAGES STACK')
        sys.stdout.flush()

        dataset = torch.utils.data.TensorDataset(images)
        print('\tDATASET BUILDED')
        sys.stdout.flush()
        dataloader = torch.utils.data.DataLoader(
            dataset, shuffle=False, drop_last=False,
            batch_size=batch_size  # TODO num_workers and pin_memory
        )
        print('Builded dataloader')
        sys.stdout.flush()

        self.model.to(device)
        embeddings = []
        print('MODEL MOVED TO DEVICE', device)
        sys.stdout.flush()

        print('\tBEFORE NO GRAD')
        sys.stdout.flush()
        with torch.no_grad():
            print('\tAFTER NO GRAD')
            sys.stdout.flush()
            for image_batch, in dataloader:
                print(f'\t\tCalculation iteration')
                sys.stdout.flush()
                image_batch = image_batch.to(device)
                embed = self.model(image_batch).cpu().numpy()
                embeddings.append(embed)

        print('FINISHED CALCULATIONS')
        sys.stdout.flush()

        return np.concatenate(embeddings)


class ImageIndex:
    def __init__(self, index_dir: Optional[str] = None, feat_dim: Optional[int] = None):
        if not (index_dir or feat_dim is not None):
            raise AttributeError()

        if index_dir:
            self.index = faiss.read_index(os.path.join(index_dir, 'index.faiss'))
            self.tmp_index = faiss.read_index(os.path.join(index_dir, 'tmp_index.faiss'))
            with open(os.path.join(index_dir, CONFIG_NAME)) as file:
                self.index_config = json.load(file)

            with open(os.path.join(index_dir, FILENAMES_JSON_NAME)) as file:
                self.id_to_filename: Dict[int, str] = json.load(file)
                self.id_to_filename = {int(k): v for k, v in self.id_to_filename.items()}

            with open(os.path.join(index_dir, TMP_FILENAMES_JSON_NAME)) as file:
                self.tmp_id_to_filename: Dict[str, int] = json.load(file)
                self.tmp_id_to_filename = {k: int(v) for k, v in self.tmp_id_to_filename.items()}
        else:
            self.index = faiss.index_factory(feat_dim, "Flat", faiss.METRIC_INNER_PRODUCT)
            self.tmp_index = faiss.index_factory(feat_dim, "Flat", faiss.METRIC_INNER_PRODUCT)
            self.index_config = {
                'index_length': 0,
                'tmp_index_length': 0,
                'feat_dim': feat_dim,
                'index_type': 'Flat',
                'metric': 'inner_product'
            }
            self.id_to_filename: Dict[int, str] = {}  # type: ignore
            self.tmp_id_to_filename = {}

    def add_indexes_from_tmp(self, filenames: List[str]):
        """Move vectors from temporary index when dataset is commited

        Args:
            filenames (List[str]): filenames what stays
        """
        for name in filenames:
            image_index = self.tmp_id_to_filename.get(name)

            if not image_index:
                log.info(f"{name} not in current index")
                continue

            # del self.tmp_id_to_filename[name]
            image_vector = self.tmp_index.reconstruct(image_index)

            if len(image_vector.shape) == 1:
                image_vector = image_vector.reshape((1, -1))

            self.index.add(image_vector)
            self.id_to_filename[self.index_config["index_length"]] = name
            self.index_config["index_length"] += 1

        # clear tmp_index
        self.tmp_id_to_filename = {v: k for k, v in self.id_to_filename.items()}
        del self.tmp_index
        self.index_config['tmp_index_length'] = int(self.index_config['index_length'])
        self.tmp_index = deepcopy(self.index)

    def add_vectors(self, vectors, filenames: List[str]):
        # we found cosine similarity using inner product
        # so vectors should be normalized
        self.tmp_index.add(vectors)

        for i, name in enumerate(filenames):
            # self.id_to_filename[i + self.index_config["index_length"]] = name
            self.tmp_id_to_filename[name] = i + self.index_config["tmp_index_length"]

        self.index_config['tmp_index_length'] += len(vectors)

    def _neighbours_indexes_to_filenames(
            self,
            neighbours: List[Tuple[int, int, float]]
    ) -> List[Tuple[str, str, float]]:
        updated_neighbours = []

        tmp_id_to_filename = {v: k for k, v in self.tmp_id_to_filename.items()}
        for item in neighbours:
            similarity = round(item[2], 5)
            similarity = min(1., similarity)
            similarity = max(0., similarity)


            updated_neighbours.append(
                (
                    tmp_id_to_filename[item[0]],
                    tmp_id_to_filename[item[1]],
                    round(float(item[2]), 4)
                )
            )

        return updated_neighbours

    def find_neighbours(self, vectors, imagenames):
        # we found cosine similarity using inner product
        # so vectors shoul be normalized
        # vectors = np.array(vectors)
        # faiss.normalize_L2(vectors)
        distances, indexes = self.tmp_index.search(vectors, 2)

        neighbours = []
        for i, filename in enumerate(imagenames):
            image_index = self.tmp_id_to_filename[filename]
            neighbours.append((image_index, indexes[i, 1], distances[i, 1]))

        # maximum values on top
        neighbours.sort(key=lambda x: 1 - x[-1])

        return self._neighbours_indexes_to_filenames(neighbours)

    def get_index_length(self):
        return self.index_config['index_length']

    def save_on_disk(self, directory_path: str):
        logging.info(f"Saving index to {directory_path}")
        if not os.path.isdir(directory_path):
            logging.warning(f"Can't find directory to save index: {directory_path}, trying to create it...")
            os.mkdir(directory_path)

        faiss.write_index(self.index, os.path.join(directory_path, 'index.faiss'))
        faiss.write_index(self.index, os.path.join(directory_path, 'tmp_index.faiss'))


        with open(os.path.join(directory_path, CONFIG_NAME), 'w') as file:
            json.dump(self.index_config, file)

        with open(os.path.join(directory_path, FILENAMES_JSON_NAME), 'w') as file:
            json.dump(self.id_to_filename, file)

        with open(os.path.join(directory_path, TMP_FILENAMES_JSON_NAME), 'w') as file:
            json.dump(self.tmp_id_to_filename, file)

        logging.info(f"Index saved to {directory_path}")


class Deduplicator:
    def __init__(self, index_path: Optional[str], pool_size: Optional[int], create_new: bool = False) -> None:
        self.feature_extractor = NNfeatureExtractor('googlenet')

        if create_new:
            self.index = ImageIndex(feat_dim=1024)
        else:
            self.index = ImageIndex(index_path)

        self.pool_size = pool_size or 1
        self.index_path = index_path

    def _get_filepaths(self, data_dir, chunk_size):
        all_filepaths = []
        for root, subdirs, files in os.walk(data_dir):
            for i, filename in enumerate(files):
                if i % chunk_size == 0:
                    all_filepaths.append([])
                all_filepaths[-1].append(os.path.join(root, filename))

        return all_filepaths

    def read_images(self, filepaths, dst_size):
        '''Read group of images, resize and return along with the group mean and std'''
        images = []
        imagenames = []

        img_mean, img_std = 0, 0
        count_images = 0

        for filename in filepaths:
            img = cv2.imread(filename)

            if img is None:
                # probably this file isn't an image
                print("Loading error:", filename[32:])
                continue

            if img.shape[0] < dst_size[0] or img.shape[1] < dst_size[1]:
                print(filename[32:], "size is", img.shape, "less than", dst_size)

            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = cv2.resize(img, dst_size) / 255.
            images.append(img)
            imagenames.append(filename)

            # calculates for every channel
            img_mean += np.mean(img, axis=tuple(range(img.ndim - 1)))
            img_std += np.std(img, axis=tuple(range(img.ndim - 1)))
            count_images += 1

        if not len(images):
            return [], [], 0, 0

        images = np.stack(images)

        img_mean /= count_images
        img_std /= count_images

        return images, imagenames, img_mean, img_std

    def _get_embeddings(self, images, batch_size: int):
        embeddings = self.feature_extractor.get_embeddings(images, batch_size)
        return embeddings

    def _get_embeddings_from_dir(
            self,
            filepaths: List,
            dst_size: Union[Tuple[int, int], List[int]],
            batch_size: int
    ):
        cpu_pool = Pool(min(self.pool_size, len(filepaths)))
        read_func = partial(self.read_images, dst_size=dst_size)
        mp_result: List[Tuple] = cpu_pool.map(read_func, filepaths)
        cpu_pool.terminate()

        images = []
        imagenames = []
        img_mean, img_std = 0., 0.
        count_chunks = 0

        for image_chunk, names_chunk, mean_, std_, in mp_result:
            if len(image_chunk):
                images.extend(image_chunk)
                imagenames.extend(names_chunk)

                img_mean += mean_
                img_std += std_
                count_chunks += 1

        img_mean /= count_chunks
        img_std /= count_chunks
        images = np.stack(images)  # type: ignore

        embeddings = self._get_embeddings(images, batch_size)

        return embeddings, imagenames

    def process_embeddings(self, embeddings, imagenames: List[str], data_dir: str):
        faiss.normalize_L2(embeddings)
        self.index.add_vectors(embeddings, imagenames)
        neighbours = self.index.find_neighbours(embeddings, imagenames)
        return neighbours

    def run_deduplication(
            self,
            data_dir: str,
            dst_size: Union[Tuple[int, int], List[int]],
            chunk_size: Optional[int] = None
    ):
        filepaths = self._get_filepaths(data_dir, chunk_size)
        # TODO batch_size as parameter
        embeddings, imagenames = self._get_embeddings_from_dir(filepaths, dst_size, 64)

        neighbours = self.process_embeddings(embeddings, imagenames, data_dir)
        return neighbours

    def save_index(self):
        saving_index_proc = Thread(
            target=self.index.save_on_disk,
            args=(self.index_path,)
        )
        saving_index_proc.start()

    def __call__(self, images: List[np.ndarray], imagenames: List[str], data_dir: str, batch_size: int) -> None:
        import sys
        print('\tGetting embeddings...')
        sys.stdout.flush()
        embeddings = self._get_embeddings(images, batch_size)
        print('\tGot embeddings')
        sys.stdout.flush()
        neighbours = self.process_embeddings(embeddings, imagenames, data_dir)
        print('\tFinish')
        sys.stdout.flush()
        # save index in parallel thread
        self.save_index()

        return neighbours

    def add_indexes_from_tmp(self, filenames):
        self.index.add_indexes_from_tmp(filenames)
        self.save_index()


def perceptual_hash_detector(images, filenames: List[str]):
    hashes: List[np.ndarray] = []
    adj_relat: Dict[str, List[str]] = {}

    for image, imagename1 in zip(images, filenames):
        image_hash = imagehash.phash(image)
        adj_relat[imagename1] = []

        for previous_image_hash, imagename2 in zip(hashes, filenames):
            if np.all(image_hash == previous_image_hash):
                adj_relat[imagename1].append(imagename2)

        hashes.append(image_hash)

    return adj_relat


def read(data_dir: str) -> Tuple[List[np.ndarray], List[str]]:
        images: List[np.ndarray] = []
        imagenames = []

        for root, subdirs, files in os.walk(data_dir):
            filenames = map(lambda x: os.path.join(root, x), files)

            for filename in filenames:

                try:
                    img = cv2.imread(filename)
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

                    images.append(img)
                    imagenames.append(filename)
                except Exception:
                    # TODO alerting
                    continue

        return images, imagenames


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('id', type=str, help='ID of task')
    parser.add_argument('label_ds', type=str, help='Dict mapper of class names')
    parser.add_argument('selected_ds', type=str, help='Dataset to import in')
    parser.add_argument('index_path', type=str, help='Directory contains index metainfo')
    parser.add_argument('storage_dir', type=str, help='Directory contains task folders')
    parser.add_argument('--batch_size', type=int, default=64, help='GPU batch size')

    args = parser.parse_args()
    directory = os.path.join(args.storage_dir, args.id)

    if not os.path.isdir(directory) or not os.listdir(directory):
        assert argparse.ArgumentError("Directory must exist and contain images!")  # TODO process case, return error code

    # check if index is already exists
    create_new = True
    if os.path.isdir(args.index_path):
        if os.path.isfile(os.path.join(args.index_path, 'index.faiss')):
            create_new = False

    deduplicator = Deduplicator(args.index_path, 8, create_new=create_new)

    images, imagenames = read(directory)
    neighbours = deduplicator(images, imagenames, directory, args.batch_size)

    result = {
        'deduplication': neighbours,
        'type': 'deduplication_result',
        'status': 'done',
        'id': args.id,
        'label_ds': args.label_ds,
        'selected_ds': args.selected_ds
    }
    result = json.dumps(result)
    print(result)
