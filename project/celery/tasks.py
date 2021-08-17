import os
import random
import shutil
import subprocess
from pathlib import Path
from typing import List, Tuple

import boto3
import urllib3
import validators
import transliterate
from botocore.exceptions import NoCredentialsError
from celery import Celery
from project.celery.exeptions import VideoProcessingError, NoneFramesError

from project.celery.storage_utils.s3_utils import create_bucket_if_not_exists, upload_file_to_bucket

IN_DOCKER = os.environ.get("IN_DOCKER", False)
STORAGE_PATH = os.environ.get("STORAGE", None)
if IN_DOCKER:
    app = Celery('ffmpeg', backend=os.getenv("REDIS"), broker=os.getenv("REDIS"))
else:
    app = Celery('ffmpeg', backend='redis://localhost:6379/0', broker='redis://localhost:6379/0')
app.autodiscover_tasks(force=True)


@app.task
def gen_prime(x):
    multiples = []
    results = []
    for i in range(2, x + 1):
        if i not in multiples:
            results.append(i)
            for j in range(i * i, x + 1, i):
                multiples.append(j)
    return results


@app.task(bind=True)
def processing_function(self, thumbs_dir, input_fname, input_fname_stem, img_ext, id, storage_dir=None, cat=None,
                        description=None, title=None, video_id=None):
    self.update_state(state='STARTED')
    storage_dir = f"{STORAGE_PATH}/tmp/" if STORAGE_PATH else storage_dir

    thumbs_dir = os.path.join(storage_dir, thumbs_dir)
    is_link = validators.url(input_fname)
    if not is_link:
        input_fname = os.path.join(storage_dir, input_fname)
    else:
        input_fname = input_fname
    input_fname_stem = transliterate.translit(input_fname_stem, 'ru', reversed=True)
    img_ext = img_ext

    # ToDo загрузка видео по ссылке
    path_input_fname = Path(input_fname)
    file_path = os.path.join(storage_dir, id, transliterate.translit(path_input_fname.name, 'ru', reversed=True))
    if not is_link:
        pass
    else:
        self.update_state(state='DOWNLOADING')
        http = urllib3.PoolManager()
        with open(str(file_path), 'wb') as out:
            r = http.request('GET', input_fname, preload_content=False)
            shutil.copyfileobj(r, out)

    out = f"{os.path.join(thumbs_dir, f'{input_fname_stem}_frame_' + '%0d' + img_ext)}"
    command = f"""ffmpeg -y -i {str(file_path)} -vsync vfr -filter_complex "[0:v]select=eq(pict_type\,PICT_TYPE_I)[pre_thumbs];[pre_thumbs]select=gt(scene\,0.2),scale=256:256[thumbs]" -map [thumbs] {out} 2>&1"""

    self.update_state(state='PROCESSING')
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        encoding='utf8'
    )
    (output, err) = process.communicate()
    if 'Invalid data found when processing input' in output:
        raise VideoProcessingError('Invalid data found when processing input')
    if not len(os.listdir(thumbs_dir)):
        command = f"""ffmpeg -y -i {str(file_path)} -vsync vfr -vf "select='eq(pict_type,PICT_TYPE_I)" -s 224:224 -frame_pts 1 {out} 2>&1"""
        self.update_state(state='PROCESSING')
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            encoding='utf8'
        )
        (output, err) = process.communicate()
    if not len(os.listdir(thumbs_dir)):
        raise NoneFramesError("Frames were not found in the video")
    return {
        "id": id,
        "cat": cat,
        "description": description,
        "title": title,
        "video_id": video_id
    }


@app.task(bind=True)
def upload_files_to_storage(self, version: str, items: List[Tuple[str, str]]):
    self.update_state(state='STARTED')
    try:
        s3 = boto3.resource(
            service_name='s3',
            endpoint_url=os.getenv("AWS_ENDPOINT_URL", "http://s3.amazonaws.com")
        )
        bucket = create_bucket_if_not_exists(s3, "versions")
        random.shuffle(items)
        train_size = 0.8
        k = int(len(items) * train_size)
        train = items[0:k]
        test = items[k:]
        self.update_state(state='UPLOADING TRAIN')
        upload(bucket, train, version, "train")
        self.update_state(state='UPLOADING VAL')
        upload(bucket, test, version, "val")
    except NoCredentialsError as ex:
        app.log.error(ex)


def upload(bucket, items, version, prefix) -> None:
    for item in items:
        file, label = item
        i = file.find("/image_storage")
        if i >= 0:
            path = file[i:]
            upload_file_to_bucket(bucket, path, f"{version}/{prefix}/{label}")
