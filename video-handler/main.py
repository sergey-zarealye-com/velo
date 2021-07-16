from connectors import Connector
import yaml  # type: ignore
import argparse
import time
import os
import subprocess
import re


async def processing_function(
    request: dict,
):
    print("Got request:", request)

    thumbs_dir = request['thumbs_dir']
    input_fname = request['input_fname']
    input_fname_stem = request['input_fname_stem']
    img_ext = request['img_ext']

    out = f"{os.path.join(thumbs_dir, f'{input_fname_stem}_frame_' + '%0d' + img_ext)}"
    command = f"""ffmpeg -y -i {str(input_fname)} -vsync vfr -filter_complex "[0:v]select=eq(pict_type\,PICT_TYPE_I)[pre_thumbs];[pre_thumbs]select=gt(scene\,0.2),scale=256:256[thumbs]" -map [thumbs] {out} 2>&1"""

    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        encoding='utf8'
    )
    (output, err) = process.communicate()
    files = []
    for file in os.listdir(thumbs_dir):
        m = re.match(f'{input_fname.stem}_frame_\d+{img_ext}', file)
        if m:
            file_path = os.path.join(thumbs_dir, file)
            files.append(file_path)
    
    # TODO write to database


def main():
    time.sleep(5.)
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
    connector.run_async_rabbitmq_connection(config["queue_name"], processing_function)


if __name__ == '__main__':
    main()
