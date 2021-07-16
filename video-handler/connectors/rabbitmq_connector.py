from asyncio.events import get_event_loop
from typing import Callable, Any, Union
import asyncio
import aio_pika
import json
import logging
from multiprocessing import Process
import nest_asyncio


nest_asyncio.apply()


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

    def send_message(self, message: Union[str, dict, list], routing_key: str):
        sending_proc = Process(
            target=self.run_send_function,
            args=(message, routing_key)
        )
        sending_proc.start()
        sending_proc.join()
        logging.info("Message is sended")

    def run_send_function(self, message: Union[str, dict, list], routing_key: str):
        try:
            loop = get_event_loop()
        except Exception:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        loop.run_until_complete(self._send_message(message, routing_key, loop))

    async def _send_message(self, message: Union[str, dict, list], routing_key: str, loop):
        connection: Any = await aio_pika.connect_robust(
            f"amqp://{self.login}:{self.passw}@{self.host}:{self.port}/",
            loop=loop
        )

        async with connection:
            channel = await connection.channel()

            if not isinstance(message, str):
                message = json.dumps(message)

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
