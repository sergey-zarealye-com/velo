import asyncio
import aio_pika
import json


async def main(loop, login, passw, port):
    connection = await aio_pika.connect_robust(
        f"amqp://{login}:{passw}@127.0.0.1:{port}/", loop=loop
    )

    async with connection:
        routing_key = "deduplication_1"

        channel = await connection.channel()

        message = json.dumps({
            'directory': '/storage1/mrowl/smoke/',
            'deduplication': True,
            'filter_size': (224, 224),
            'resize': True,
            'dst_size': (224, 224)
        })

        await channel.default_exchange.publish(
            aio_pika.Message(body=message.encode()),
            routing_key=routing_key,
        )


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        main(
            loop,
            'guest',
            'guest',
            5673
        )
    )
    loop.close()
