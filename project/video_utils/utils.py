import os
import re
import subprocess
from pathlib import Path
from typing import List

IMG_EXT = '.png'


def ffmpeg_job(input_fname: Path, thumbs_dir: str) -> List[str]:
    """
    :param input_fname: видео файл
    :param thumbs_dir: путь куда складывать фреймы
    """
    out = f"{os.path.join(thumbs_dir, f'{input_fname.stem}_frame_' + '%0d' + IMG_EXT)}"
    command = f"""ffmpeg -y -i {str(input_fname)} -vsync vfr -vf "select='eq(pict_type,PICT_TYPE_I)" -s 224:224 -frame_pts 1 {out} 2>&1"""

    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        encoding='utf8'
    )
    (output, err) = process.communicate()
    files = []
    for file in os.listdir(thumbs_dir):
        m = re.match(f'{input_fname.stem}_frame_\d+{IMG_EXT}', file)
        if m:
            file_path = Path(os.path.join(thumbs_dir, file)).absolute()
            files.append(str(file_path))
    return files


if __name__ == '__main__':
    file = Path("C:/PyCharmProjects/Video_Annotation_System/nasa.mp4")
    thumbs_dir = "C:/PyCharmProjects/Video_Annotation_System/out"
    ffmpeg_job(file, thumbs_dir)
