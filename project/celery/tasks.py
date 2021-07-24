import os
import shutil
import subprocess
from pathlib import Path

import urllib3
import validators
from celery import Celery

app = Celery('ffmpeg', backend='redis://127.0.0.1:6379', broker='amqp://')
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


@app.task
def processing_function(thumbs_dir, input_fname, input_fname_stem, img_ext, id, storage_dir=None, cat=None,
                        description=None, title=None, video_id=None):
    thumbs_dir = os.path.join(storage_dir, thumbs_dir)
    is_link = validators.url(input_fname)
    if not is_link:
        input_fname = os.path.join(storage_dir, input_fname)
    else:
        input_fname = input_fname
    input_fname_stem = input_fname_stem
    img_ext = img_ext
    print({
        "thumbs_dir": thumbs_dir,
        "input_fname": input_fname,
        "input_fname+stem": input_fname_stem
    })

    # ToDo загрузка видео по ссылке
    path_input_fname = Path(input_fname)
    file_path = os.path.join(storage_dir, id, path_input_fname.name)
    if not is_link:
        pass
    else:
        http = urllib3.PoolManager()
        with open(str(file_path), 'wb') as out:
            r = http.request('GET', input_fname, preload_content=False)
            shutil.copyfileobj(r, out)

    out = f"{os.path.join(thumbs_dir, f'{input_fname_stem}_frame_' + '%0d' + img_ext)}"
    command = f"""ffmpeg -y -i {str(input_fname)} -vsync vfr -filter_complex "[0:v]select=eq(pict_type\,PICT_TYPE_I)[pre_thumbs];[pre_thumbs]select=gt(scene\,0.2),scale=256:256[thumbs]" -map [thumbs] {out} 2>&1"""

    print("applying", command)

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
