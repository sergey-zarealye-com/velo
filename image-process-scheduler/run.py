from connectors import run_async_rabbitmq_connection
from improsch.pipeline import build_pipeline
from functools import partial
from conveyor import build_conveyor, handle_config
import json
import aio_pika
import asyncio
from argparse import ArgumentParser
import yaml


async def send_message_back(message, loop):
    connection = await aio_pika.connect_robust(
        "amqp://guest:guest@127.0.0.1:5673/",
        loop=loop
    )

    async with connection:
        routing_key = "deduplication_result_1"

        channel = await connection.channel()

        await channel.default_exchange.publish(
            aio_pika.Message(body=message.encode()),
            routing_key=routing_key,
        )


def params_mapper(config):
    kwargs = {
        "filter_by_size": "filter_func" in config["config"],
        "need_resize": "resize" in config["config"],
        "deduplication": "deduplication" in config["config"]
    }

    if kwargs["filter_by_size"]:
        kwargs["filter_args"] = config["config"]["filter_func"].get("args")

    if kwargs["need_resize"]:
        kwargs["resize_args"] = config["config"]["resize"].get("args")

    if kwargs["deduplication"]:
        kwargs["deduplication_args"] = config["config"]["deduplication"].get("args")

    kwargs["graph"] = config

    return kwargs


def run(pipeline, login: str, passw: str, port: int):
    async def print_pipeline_result(request):
        print('\tGot request:')
        print(request)
        img_dir = request["directory"]
        result = pipeline(img_dir, request['id'])

        result['id'] = request['id']
        result['type'] = 'result'

        result_string = json.dumps(result)

        await send_message_back(result_string, asyncio.get_event_loop())

    run_async_rabbitmq_connection('deduplication_1', print_pipeline_result, login, passw, port)


def parse_config(config_path: str):
    with open(config_path) as file:
        config: dict = yaml.safe_load(file)

    return config


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--config', type=str, default='config.yml')
    parser.add_argument('--pipeline', type=str, default='base_pipeline.yml')

    args = parser.parse_args()
    config = parse_config(args.config)

    run_func = partial(
        run,
        login=config['rabbit_login'],
        passw=config['rabbit_passw'],
        port=config['rabbit_port']
    )

    build_conveyor(
        config,
        args.pipeline,
        handle_config,
        params_mapper,
        build_pipeline,
        run_func
    )
