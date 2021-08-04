import os
import uuid
import logging
from typing import NamedTuple

import boto3

from utils import s3_utils


class DownloadedDatasetResult(NamedTuple):
    dataset_id: str
    dataset_path: str


def download_dataset_and_save_to_vault(
        s3_endpoint: str,
        dataset_bucket: str,
        dataset_save_path: str,
        dataset_vault_bucket: str,
        dataset_prefix: str = '',
        save_to_vault: bool = True
) -> DownloadedDatasetResult:
    s3 = boto3.resource(
        service_name='s3',
        endpoint_url=s3_endpoint
    )

    s3_utils.download_bucket_to_dir(
        s3_bucket=s3.Bucket(dataset_bucket),
        local_dir=dataset_save_path,
        prefix=dataset_prefix
    )
    logging.info('Downloaded dataset')

    dataset_id = str(uuid.uuid4())

    if save_to_vault:
        vault_bucket = s3_utils.create_bucket_if_not_exists(s3, dataset_vault_bucket)
        s3_utils.upload_dir_to_bucket(
            vault_bucket,
            local_dir=dataset_save_path,
            prefix=os.path.join(dataset_id, dataset_prefix)
        )
        logging.info(f'Uploaded dataset to vault with id {dataset_id}: '
                     f'{os.path.join(dataset_vault_bucket, dataset_id, dataset_prefix)}')
    else:
        logging.info('NOT saving the dataset to vault')

    return DownloadedDatasetResult(
        dataset_id=dataset_id,
        dataset_path=dataset_save_path
    )


def download_dataset_component(
        data_volume_path: str,
        s3_endpoint: str,
        dataset_bucket: str,
        dataset_prefix: str,
        dataset_vault_bucket: str,
        save_to_vault: bool = True
) -> NamedTuple('DownloadMnistDatasetOutput', [('dataset_id', str), ('dataset_path', str)]):
    import os
    import shutil
    import logging
    from typing import NamedTuple

    from utils.dataset import download_dataset_and_save_to_vault

    logging.basicConfig(level=logging.INFO)

    dataset_save_path = os.path.join(data_volume_path, dataset_prefix)
    logging.info(f'Removing dataset destination path {dataset_save_path} if present')
    shutil.rmtree(dataset_save_path, ignore_errors=True)

    dataset_id, dataset_path = download_dataset_and_save_to_vault(
        s3_endpoint=s3_endpoint,
        dataset_bucket=dataset_bucket,
        dataset_save_path=dataset_save_path,
        dataset_vault_bucket=dataset_vault_bucket,
        dataset_prefix=dataset_prefix,
        save_to_vault=save_to_vault
    )

    return_type = NamedTuple('DownloadMnistDatasetOutput', [('dataset_id', str), ('dataset_path', str)])
    return return_type(dataset_id=dataset_id, dataset_path=dataset_path)
