from connectors import run_async_rabbitmq_connection
from improsch.pipeline import Preprocessor
from functools import partial
import json
import aio_pika
import asyncio
from argparse import ArgumentParser
import yaml
import time


async def send_message_back(message, loop, login, passw, port, host):
    connection = await aio_pika.connect_robust(
        f"amqp://{login}:{passw}@{host}:{port}/",
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


def run(pipeline, login: str, passw: str, port: int, host: str):
    async def print_pipeline_result(request):
        print('\tGot request:')
        print(request)
        result = pipeline(request)

        result['id'] = request['id']
        result['type'] = 'result'

        result_string = json.dumps(result)

        await send_message_back(result_string, asyncio.get_event_loop(), login, passw, port, host)

    print("Run async connector")
    run_async_rabbitmq_connection('deduplication_1', print_pipeline_result, login, passw, port, host)


def parse_config(config_path: str):
    with open(config_path) as file:
        config: dict = yaml.safe_load(file)

    return config


if __name__ == '__main__':
    print('Sleeping...')
    time.sleep(5.)
    parser = ArgumentParser()
    parser.add_argument('--config', type=str, default='config.yml')
    parser.add_argument('--pipeline', type=str, default='base_pipeline.yml')

    args = parser.parse_args()
    config = parse_config(args.config)
    processor = Preprocessor(
        storage_path=config['storage_path'],
        saving_pool_size=config['saving_pool_size'],
        dedup_batch_size=config['dedup_batch_size'],
        dedup_index_path=config['dedup_index_path']
    )

    run_func = partial(
        run,
        login=config['rabbit_login'],
        passw=config['rabbit_passw'],
        port=config['rabbit_port']
    )

    run(
        processor.preprocessing,
        login=config['rabbit_login'],
        passw=config['rabbit_passw'],
        port=config['rabbit_port'],
        host=config["rabbit_host"]
    )
