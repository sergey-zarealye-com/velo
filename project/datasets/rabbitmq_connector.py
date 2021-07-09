import asyncio
from typing import Any
import aio_pika
import json

from project import db
from project.models import Deduplication


def send_message(queue_name: str, queue):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def func(loop, queue_name, queue):
        connection: Any = await aio_pika.connect_robust(
            "amqp://guest:guest@127.0.0.1:5673/",
            loop=loop
        )

        async with connection:
            channel = await connection.channel()

            while True:
                task_id, message = queue.get()  # blocking operation

                new_task_entry = Deduplication(
                    task_uid=task_id,
                    status=0
                )
                db.session.add(new_task_entry)
                db.session.commit()

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
            "amqp://guest:guest@127.0.0.1:5673/", loop=loop,
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
                        print("\tGot response:")
                        response = json.loads(message.body.decode('utf-8'))
                        task_id = response['id']
                        task_entry = Deduplication.query.filter_by(task_uid=task_id).first()

                        if task_entry:
                            print(response)
                            task_entry.result = response
                            queue.put(response)
                            db.session.commit()

    loop.run_until_complete(func(loop, queue_name, queue))
