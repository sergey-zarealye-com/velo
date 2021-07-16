from connectors import Connector
import yaml  # type: ignore
import argparse
import time
import os
import subprocess


def get_processing_func(storage_dir: str, connector: Connector, result_queue_name: str):
    async def processing_function(
        request: dict,
    ):
        print("Got request:", request)

        thumbs_dir = os.path.join(storage_dir, request['thumbs_dir'])
        input_fname = os.path.join(storage_dir, request['input_fname'])
        input_fname_stem = request['input_fname_stem']
        img_ext = request['img_ext']
        print({
            "thumbs_dir": thumbs_dir,
            "input_fname": input_fname,
            "input_fname+stem": input_fname_stem
        })

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

        # files = []
        # for file in os.listdir(thumbs_dir):
        #     m = re.match(f'{input_fname.stem}_frame_\d+{img_ext}', file)
        #     if m:
        #         file_path = os.path.join(thumbs_dir, file)
        #         files.append(file_path)
        
        # TODO write to database or don't? if flask will take it on
        connector.run_send_function(
            {"id": request["id"]},
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
    main()
