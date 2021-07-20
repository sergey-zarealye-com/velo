import os
import logging

from .processors import Deduplicator, resize_batch, save_multiprocess
from .filters import get_filter_by_min_size
from .readers import get_image_reader

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

    def preprocessing(self, request):
        if request['is_size_control']:
            min_size = request['min_size']

            if isinstance(min_size, (int, float)):
                min_size = (min_size, min_size)

            read_func = get_image_reader(get_filter_by_min_size(min_size))
        else:
            read_func = get_image_reader()

        images, imagenames = read_func(request['directory'])

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
            dedup_result = self.deduplicator(
                resized_images,
                parted_filenames,
                request['directory'],
                batch_size=self.dedup_batch_size
            )

            return {'deduplication': dedup_result}

        return {"status": "done"}
