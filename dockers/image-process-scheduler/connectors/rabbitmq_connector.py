import asyncio
from asyncio.events import AbstractEventLoop
from typing import Any, Callable, Optional
import aio_pika
import json

# TODO: импорты по PEP8 (везде)

async def main(
    loop,
    queue_name: str,
    processing_queue: Callable,
    login: str,
    passw: str,
    port: int,
    host: str
):
    # TODO: убрать хардкод 5672
    connection: Any = await aio_pika.connect_robust(
        f"amqp://{login}:{passw}@{host}:{port}/", loop=loop,
        port=5672
    )
    print("Successful connected to", f"amqp://{login}:{passw}@{host}:{port}/")

    async with connection:
        # Creating channel
        channel = await connection.channel()

        # Declaring queue
        queue = await channel.declare_queue(queue_name, auto_delete=False)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    options = json.loads(message.body.decode('utf-8'))
                    processing_queue.put(options)


async def send_message(message, loop, routing_key: str, login, passw, port, host):
    connection: Any = await aio_pika.connect_robust(
        f"amqp://{login}:{passw}@{host}:{port}/",
        loop=loop
    )

    async with connection:
        channel = await connection.channel()

        await channel.default_exchange.publish(
            aio_pika.Message(body=message.encode()),
            routing_key=routing_key,
        )


def run_async_rabbitmq_connection(
    queue_name,
    processing_queue,
    login: str,
    passw: str,
    port: int,
    host: str,
    loop: Optional[AbstractEventLoop] = None,
):
    if not loop:
        loop = asyncio.get_event_loop()

    loop.run_until_complete(
        main(
            loop, queue_name, processing_queue,
            login, passw, port, host
        )
    )
    # loop.close()
