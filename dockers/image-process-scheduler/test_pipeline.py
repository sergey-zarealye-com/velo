from improsch.pipeline import Preprocessor


processor = Preprocessor(
    storage_path='/storage1/mrowl/image_storage',
    saving_pool_size=3,
    dedup_batch_size=64,
    dedup_index_path='/storage1/mrowl/dedup_index'
)


def test_dedup():
    request = {
        'directory': '/storage1/mrowl/mini_test/mini_test',
        'is_size_control': True,
        'min_size': 256,
        'is_resize': True,
        'dst_size': (256, 256),
        'deduplication': True
    }

    processor.preprocessing(request)


def test_filtering():
    request = {
        'directory': '/storage1/mrowl/mini_test/mini_test',
        'is_size_control': True,
        'min_size': 256,
        'is_resize': True,
        'dst_size': (256, 256),
        'deduplication': False
    }

    processor.preprocessing(request)
