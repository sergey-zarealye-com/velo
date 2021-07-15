from typing import Callable, Any
import asyncio
import aio_pika
import json
import logging


class Connector:
    def __init__(self, login: str, passw: str, port: int, host: str):
        self.login = login
        self.passw = passw
        self.host = host
        self.port = port

        try:
            self.loop = asyncio.get_event_loop()
        except Exception:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

    async def recieve_message(
        self,
        queue_name: str,
        processing_func: Callable
    ):
        connection: Any = await aio_pika.connect_robust(
            f"amqp://{self.login}:{self.passw}@{self.host}:{self.port}/",
            loop=self.loop
        )
        logging.info("Successful connected to", f"amqp://{self.login}:{self.passw}@{self.host}:{self.port}/")

        async with connection:
            # Creating channel
            channel = await connection.channel()

            # Declaring queue
            queue = await channel.declare_queue(queue_name, auto_delete=True)

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        options = json.loads(message.body.decode('utf-8'))
                        await processing_func(options)

    async def send_message(self, message, routing_key: str):
        connection: Any = await aio_pika.connect_robust(
            f"amqp://{self.login}:{self.passw}@{self.host}:{self.port}/",
            loop=self.loop
        )

        async with connection:
            channel = await connection.channel()

            await channel.default_exchange.publish(
                aio_pika.Message(body=message.encode()),
                routing_key=routing_key,
            )

    def run_async_rabbitmq_connection(
        self,
        queue_name,
        processing_function,
    ):
        self.loop.run_until_complete(
            self.recieve_message(queue_name, processing_function)
        )

        self.loop.close()
