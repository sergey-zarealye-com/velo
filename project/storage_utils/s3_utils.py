import os
import time
import logging
from pathlib import Path

from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO)


def download_bucket_to_dir(s3_bucket, local_dir: str, prefix='') -> None:
    logging.info(f'Downloading... bucket {s3_bucket.name} to {local_dir}')
    download_start = time.time()
    for obj in s3_bucket.objects.filter(Prefix=prefix).all():
        file_relpath = obj.key
        if prefix:
            file_relpath = os.path.relpath(obj.key, prefix)
        if not file_relpath.strip('./') or obj.size == 0:
            continue
        destination = os.path.join(local_dir, file_relpath)
        logging.info(f'-- {s3_bucket.name} -> {local_dir}: Downloading... {obj.key} to {destination}')
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        file_download_start = time.time()
        s3_bucket.download_file(
            Key=obj.key,
            Filename=destination
        )
        file_download_elapsed = round(time.time() - file_download_start, 2)
        logging.info(f'-- {s3_bucket.name} -> {local_dir}: Downloaded {obj.key} to {destination} '
                     f'in {file_download_elapsed}s')
    download_elapsed = round(time.time() - download_start, 2)
    logging.info(f'Downloaded bucket {s3_bucket.name} to {local_dir} in {download_elapsed}s')


def upload_dir_to_bucket(s3_bucket, local_dir: str, prefix: str = '') -> None:
    logging.info(f'Uploading... {local_dir} to s3://{s3_bucket.name}/{prefix}')
    upload_start = time.time()
    for root, dirs, files in os.walk(local_dir):
        for filename in files:
            file_path = os.path.join(root, filename)
            file_relpath = os.path.relpath(file_path, local_dir)
            bucket_key = os.path.join(prefix, file_relpath)
            logging.info(f'-- {local_dir} -> {s3_bucket.name}: '
                         f'Uploading... file {file_path} to s3://{s3_bucket.name}/{bucket_key}')
            file_upload_start = time.time()
            s3_bucket.upload_file(
                Filename=file_path,
                Key=bucket_key
            )
            file_upload_elapsed = round(time.time() - file_upload_start, 2)
            logging.info(f'-- {local_dir} -> {s3_bucket.name}: '
                         f'Uploaded file {file_path} to s3://{s3_bucket.name}/{bucket_key} in {file_upload_elapsed}s')
    upload_elapsed = round(time.time() - upload_start, 2)
    logging.info(f'Uploaded {local_dir} to bucket s3://{s3_bucket.name}/{prefix} in {upload_elapsed}s')

def upload_file_to_bucket(s3_bucket, file_path: str, prefix: str = '') -> None:
    logging.info(f'Uploading... {file_path} to s3://{s3_bucket.name}/{prefix}')
    upload_start = time.time()
    bucket_key = os.path.join(prefix, Path(file_path).name)
    logging.info(f'-- {file_path} -> {s3_bucket.name}: '
                 f'Uploading... file {file_path} to s3://{s3_bucket.name}/{bucket_key}')
    file_upload_start = time.time()
    s3_bucket.upload_file(
        Filename=file_path,
        Key=bucket_key
    )
    file_upload_elapsed = round(time.time() - file_upload_start, 2)
    logging.info(f'-- {file_path} -> {s3_bucket.name}: '
                 f'Uploaded file {file_path} to s3://{s3_bucket.name}/{bucket_key} in {file_upload_elapsed}s')
    upload_elapsed = round(time.time() - upload_start, 2)
    logging.info(f'Uploaded {file_path} to bucket s3://{s3_bucket.name}/{prefix} in {upload_elapsed}s')


def create_bucket_if_not_exists(s3_resource, bucket_name):
    try:
        bucket = s3_resource.create_bucket(Bucket=bucket_name)
    except ClientError as err:
        if err.response['Error']['Code'] not in ['EntityAlreadyExists', 'BucketAlreadyOwnedByYou']:
            raise
        bucket = s3_resource.Bucket(bucket_name)
    return bucket


def download_file_to_dir(s3_resource, bucket_name, file_name, output):
    bucket = s3_resource.Bucket(bucket_name)
    target_file = None
    for obj in bucket.objects.all():
        name = obj.key.split('/')[-1]
        if name == file_name:
            target_file = obj
            break
    try:
        bucket.download_file(target_file.key, output)
    except ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
        else:
            raise
    logging.info(f'Downloaded model {file_name} to {output}')
