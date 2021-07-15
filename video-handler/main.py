from connectors import Connector
import yaml  # type: ignore
import argparse
import time


async def processing_function(
    request: dict,
):
    # TODO process request
    print("Got request:", request)


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
