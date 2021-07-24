import logging
import shutil
from pathlib import Path

import urllib3

from connectors import Connector
import yaml  # type: ignore
import argparse
import time
import os
import subprocess
import validators


log = logging.getLogger(__name__)


def get_processing_func(storage_dir: str, connector: Connector, result_queue_name: str):
    async def processing_function(
            req: dict,
    ):
        print("Got request:", req)
        thumbs_dir = os.path.join(storage_dir, req['thumbs_dir'])
        is_link = validators.url(req['input_fname'])
        if not is_link:
            input_fname = os.path.join(storage_dir, req['input_fname'])
        else:
            input_fname = req['input_fname']
        input_fname_stem = req['input_fname_stem']
        img_ext = req['img_ext']
        print({
            "thumbs_dir": thumbs_dir,
            "input_fname": input_fname,
            "input_fname+stem": input_fname_stem
        })

        # ToDo загрузка видео по ссылке
        path_input_fname = Path(input_fname)
        file_path = os.path.join(storage_dir, req['id'], path_input_fname.name)
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
        print("Subprocess finished")

        connector.run_send_function(
            {
                "id": req["id"],
                "cat": req["cat"],
                "description": req["description"],
                "title": req["title"],
                "video_id": req["video_id"]
            },
            result_queue_name
        )

    return processing_function


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config_name', type=str, default='config.yml')

    args = parser.parse_args()

    with open(args.config_name, 'r') as file:
        config = yaml.safe_load(file)

    connector = Connector(
        config["rabbit_login"],
        config["rabbit_passw"],
        config["rabbit_port"],
        config["rabbit_host"]
    )

    processing_function = get_processing_func(config["storage_path"], connector, config["result_queue_name"])

    connector.run_async_rabbitmq_connection(config["queue_name"], processing_function)


if __name__ == '__main__':
    log.info('Try to start')
    time.sleep(10)
    log.info('Started')
    main()
