import os
from distutils.util import strtobool

import boto3


def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url=os.getenv("AWS_ENDPOINT_URL", "http://s3.amazonaws.com"),
        use_ssl=bool(strtobool(os.getenv("AWS_USE_SSL", "false"))),
    )


def download_s3_dir(prefix, local, bucket, client=None):
    """
    params:
    - prefix: pattern to match in s3
    - local: local path to folder in which to place files
    - bucket: s3 bucket with target contents
    - client: initialized s3 client object
    """
    if not client:
        client = get_s3_client()
    keys = []
    dirs = []
    next_token = ''
    base_kwargs = {
        'Bucket': bucket,
        'Prefix': prefix,
    }
    while next_token is not None:
        kwargs = base_kwargs.copy()
        if next_token != '':
            kwargs.update({'ContinuationToken': next_token})
        results = client.list_objects_v2(**kwargs)
        contents = results.get('Contents')
        for i in contents:
            k = i.get('Key')
            if k[-1] != '/':
                keys.append(k)
            else:
                dirs.append(k)
        next_token = results.get('NextContinuationToken')
    for d in dirs:
        dest_pathname = os.path.join(local, d)
        if not os.path.exists(os.path.dirname(dest_pathname)):
            os.makedirs(os.path.dirname(dest_pathname))
    for k in keys:
        dest_pathname = os.path.join(local, k)
        if not os.path.exists(os.path.dirname(dest_pathname)):
            os.makedirs(os.path.dirname(dest_pathname))
        client.download_file(bucket, k, dest_pathname)
    return os.path.join(local, prefix)


def download_file_to_dir(file_name, local, bucket, client=None):
    """
    params:
    - file_name: file name inside bucket (not full path)
    - local: local path to folder in which to place files
    - bucket: s3 bucket with target contents
    - client: initialized s3 client object
    """
    if not client:
        client = get_s3_client()
    keys = []
    dirs = []
    next_token = ''
    base_kwargs = {
        'Bucket': bucket
    }
    find = False
    while next_token is not None:
        if find:
            break
        kwargs = base_kwargs.copy()
        if next_token != '':
            kwargs.update({'ContinuationToken': next_token})
        results = client.list_objects_v2(**kwargs)
        contents = results.get('Contents')
        for i in contents:
            k = i.get('Key')
            if file_name in k and k[-1] != '/':
                keys.append(k)
                find = True
                break
            else:
                dirs.append(k)
        next_token = results.get('NextContinuationToken')
    for k in keys:
        dest_pathname = os.path.join(local, file_name)
        if not os.path.exists(os.path.dirname(dest_pathname)):
            os.makedirs(os.path.dirname(dest_pathname))
        client.download_file(bucket, k, dest_pathname)
    return os.path.join(local, file_name)
