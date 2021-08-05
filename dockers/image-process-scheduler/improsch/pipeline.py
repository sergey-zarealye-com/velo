import os
import logging

from .processors import Deduplicator, resize_batch, save_multiprocess, perceptual_hash_detector
from .filters import get_filter_by_min_size
from .readers import get_image_reader, get_image_reader_pil

logging.basicConfig(level=logging.INFO)


class Preprocessor:
    def __init__(
            self,
            storage_path: str,
            saving_pool_size: int,
            dedup_batch_size: int,
            dedup_index_path: str
    ):
        import sys
        print('\tCREATING PREPROCESSOR')
        sys.stdout.flush()
        create_new = True
        if os.path.isdir(dedup_index_path):
            if os.path.isfile(os.path.join(dedup_index_path, 'index.faiss')):
                create_new = False

        print('\tCREATING DEDUP')
        sys.stdout.flush()
        self.deduplicator = Deduplicator(dedup_index_path, 8, create_new=create_new)
        print('\DEDUP CREATED')
        sys.stdout.flush()
        self.storage_path = storage_path
        self.dedup_batch_size = dedup_batch_size
        self.saving_pool_size = saving_pool_size

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
        if request.get('type') == 'merge_control':
            get_reader_func = get_image_reader_pil
        else:
            get_reader_func = get_image_reader

        if request.get('is_size_control'):
            min_size = request['min_size']

            if isinstance(min_size, (int, float)):
                min_size = (min_size, min_size)

            read_func = get_reader_func(get_filter_by_min_size(min_size))
        else:
            read_func = get_reader_func()

        images, imagenames = read_func(request['directory'])

        if request.get('merge_check'):
            names_mapping = request['names_mapping']
            imagenames = [names_mapping[name] for name in imagenames]
            adj_relation = perceptual_hash_detector(images, imagenames)
            return adj_relation

        if request['is_resize'] or request['deduplication']:
            resized_images = resize_batch(images, request['dst_size'])

        # resized images might be referenced before assiggment
        # TODO: вынести определение resized_images за условия
        if request['is_resize']:
            parted_filenames = save_multiprocess(
                resized_images,
                imagenames,
                request['id'],
                pool_size=3,
                storage_path=self.storage_path
            )
        else:
            parted_filenames = save_multiprocess(
                images,
                imagenames,
                request['id'],
                pool_size=3,
                storage_path=self.storage_path
            )

        if request['deduplication']:
            print('Starting deduplication')
            import sys
            sys.stdout.flush()
            dedup_result = self.deduplicator(
                resized_images,
                parted_filenames,
                request['directory'],
                batch_size=self.dedup_batch_size
            )

            return {
                "status": "done",
                "type": "deduplication_result",
                "deduplication": dedup_result
            }

        return {
            "status": "done",
            "type": "filtered",
            "filenames": parted_filenames
        }
