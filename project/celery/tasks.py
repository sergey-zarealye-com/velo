import os
import shutil
import subprocess
from pathlib import Path

import urllib3
import validators
from celery import Celery

IN_DOCKER = os.environ.get("DOCKER_USE", False)
STORAGE_PATH = os.environ.get("STORAGE_PATH", None)
if IN_DOCKER:
    app = Celery('ffmpeg', backend='redis://redis:6379/0', broker='redis://redis:6379/0')
else:
    app = Celery('ffmpeg', backend='redis://localhost:6379/0', broker='redis://localhost:6379/0')
app.autodiscover_tasks(force=True)
print(f"Celery id = {id(app)}")


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
    # self.update_state(state='STARTED')
    #TODO убрать костыль для докера
    storage_dir = f"{STORAGE_PATH}/{'/'.join(storage_dir.split(sep='/')[-4:])}" if STORAGE_PATH else storage_dir

    thumbs_dir = os.path.join(storage_dir, thumbs_dir)
    is_link = validators.url(input_fname)
    if not is_link:
        input_fname = os.path.join(storage_dir, input_fname)
    else:
        input_fname = input_fname
    input_fname_stem = input_fname_stem
    img_ext = img_ext

    # ToDo загрузка видео по ссылке
    path_input_fname = Path(input_fname)
    file_path = os.path.join(storage_dir, id, path_input_fname.name)
    if not is_link:
        pass
    else:
        # self.update_state(state='DOWNLOADING')
        http = urllib3.PoolManager()
        with open(str(file_path), 'wb') as out:
            r = http.request('GET', input_fname, preload_content=False)
            shutil.copyfileobj(r, out)

    out = f"{os.path.join(thumbs_dir, f'{input_fname_stem}_frame_' + '%0d' + img_ext)}"
    command = f"""ffmpeg -y -i {str(input_fname)} -vsync vfr -filter_complex "[0:v]select=eq(pict_type\,PICT_TYPE_I)[pre_thumbs];[pre_thumbs]select=gt(scene\,0.2),scale=256:256[thumbs]" -map [thumbs] {out} 2>&1"""

    # self.update_state(state='PROCESSING')
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        encoding='utf8'
    )
    (output, err) = process.communicate()
    if not len(os.listdir(thumbs_dir)):
        command = f"""ffmpeg -y -i {str(input_fname)} -vsync vfr -vf "select='eq(pict_type,PICT_TYPE_I)" -s 224:224 -frame_pts 1 {out} 2>&1"""
        # self.update_state(state='PROCESSING')
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            encoding='utf8'
        )
        (output, err) = process.communicate()
    return {
        "id": id,
        "cat": cat,
        "description": description,
        "title": title,
        "video_id": video_id
    }
