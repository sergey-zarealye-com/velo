import asyncio
from typing import Any
import aio_pika
import json
import os


rabbit_login = os.getenv("RABBIT_LOGIN") or "guest"
rabbit_passw = os.getenv("RABBIT_PASSW") or "guest"
rabbit_port = os.getenv("RABBIT_PORT") or 5672
rabbit_host = os.getenv("RABBIT_HOST") or "127.0.0.1"
rabbit_port = int(rabbit_port)


def send_message(queue_name: str, queue):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def func(loop, queue_name, queue):
        connection: Any = await aio_pika.connect_robust(
            f"amqp://{rabbit_login}:{rabbit_passw}@{rabbit_host}:{rabbit_port}/",
            loop=loop
        )

        async with connection:
            channel = await connection.channel()

            while True:
                message = queue.get()  # blocking operation
                if not isinstance(message, str):
                    message = json.dumps(message)

                await channel.default_exchange.publish(
                    aio_pika.Message(body=message.encode()),
                    routing_key=queue_name,
                )

    loop.run_until_complete(func(loop, queue_name, queue))


def get_message(queue_name: str, queue):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def func(loop, queue_name, queue):
        connection: Any = await aio_pika.connect_robust(
            f"amqp://{rabbit_login}:{rabbit_passw}@{rabbit_host}:{rabbit_port}/", loop=loop,
            port=5673
        )

        async with connection:
            # Creating channel
            channel = await connection.channel()

            # Declaring queue
            rabbit_queue = await channel.declare_queue(queue_name, auto_delete=True)

            async with rabbit_queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        response = json.loads(message.body.decode('utf-8'))
                        task_id = response['id']
                        print("\tGot response with task_id:", task_id)
                        # TODO написать реацию на то, что обработка завершена

    loop.run_until_complete(func(loop, queue_name, queue))
