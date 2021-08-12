import os
import logging
from typing import List

from .processors import Deduplicator, resize_batch, save_multiprocess, perceptual_hash_detector
from .filters import get_filter_by_min_size
from .readers import read_image_cv2, read_image_pil

logging.basicConfig(level=logging.INFO)


class Preprocessor:
    def __init__(
            self,
            storage_path: str,
            saving_pool_size: int,
            dedup_batch_size: int,
            dedup_index_path: str
    ):
        create_new = True
        if os.path.isdir(dedup_index_path):
            if os.path.isfile(os.path.join(dedup_index_path, 'index.faiss')):
                create_new = False

        self.deduplicator = Deduplicator(dedup_index_path, 8, create_new=create_new)
        self.storage_path = storage_path
        self.dedup_batch_size = dedup_batch_size
        self.saving_pool_size = saving_pool_size

    def process_by_filenames(self, filepaths: List[str], request: dict):
        filter_func = None
        if request.get('is_size_control'):
            min_size = request['min_size']

            if isinstance(min_size, (int, float)):
                min_size = (min_size, min_size)

            filter_func = get_filter_by_min_size(min_size)

        read_image = read_image_cv2
        if request.get('type') == 'merge_control':
            read_image_pil

        images, imagenames = [], []
        for filepath in filepaths:
            image = read_image(filepath, filter_func)
            if image is not None:
                images.append(image)
                imagenames.append(filepath)

        if request.get('merge_check'):
            names_mapping = request['names_mapping']
            imagenames = [names_mapping[name] for name in imagenames]
            adj_relation = perceptual_hash_detector(images, imagenames)
            return [adj_relation]

        if request['is_resize'] or request['deduplication']:
            resized_images = resize_batch(images, request['dst_size'])

        if request['is_resize']:
            parted_filenames = save_multiprocess(
                resized_images,
                imagenames,
                pool_size=3,
                storage_path=self.storage_path
            )
        else:
            parted_filenames = save_multiprocess(
                images,
                imagenames,
                pool_size=3,
                storage_path=self.storage_path
            )

        if request['deduplication']:
            self.deduplicator.add_images_to_index(
                resized_images, parted_filenames,
                self.dedup_batch_size
            )
        return parted_filenames

    def parted_preprocessing(self, request: dict, chunk_size: int):
        data_dir = request['directory']
        print(f'\tReading in {data_dir}')
        filenames = []
        for root, _, files in os.walk(data_dir):
            filepaths = list(map(lambda x: os.path.join(root, x), files))
            filenames.extend(filepaths)
        print(f'\tCount of images: {len(filenames)}')

        internal_result = []
        for i in range(0, len(filenames), chunk_size):
            print('\tProcessing step:', i + 1)
            internal_result.extend(
                self.process_by_filenames(filenames[i: i + chunk_size], request)
            )

        if request['deduplication']:
            dedup_result = self.deduplicator.get_neighbours_by_filenames(internal_result)
            return {
                "status": "done",
                "type": "deduplication_result",
                "deduplication": dedup_result
            }
        elif request.get('merge_check'):
            res_dict = {}
            for d in internal_result:
                for key, value in d.items():
                    res_dict[key] = value
            return res_dict
        else:
            return {
                "status": "done",
                "type": "filtered",
                "filenames": internal_result
            }

    def preprocessing(self, request):
        if request.get('type') == 'merge_indexes':
            filenames = request["files_to_keep"]
            filenames = list(
                map(
                    lambda x: x.replace(self.storage_path, ''),
                    filenames
                )
            )
            self.deduplicator.add_indexes_from_tmp(filenames)
            return {'status': 'done'}

        return self.parted_preprocessing(request, 100)