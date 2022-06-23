from pathlib import Path

import click
import requests
import requests.exceptions
import urllib3.exceptions

from lqts.core.config import Configuration


if Path(".env").exists():
    config = Configuration.load_env_file(".env")
else:
    config = Configuration()


@click.command("qsummary")
@click.option("--port", default=config.port, help="The port number of the server")
@click.option("--port", default=config.port, help="The port number of the server")
@click.option(
    "--ip_address", default=config.ip_address, help="The IP address of the server"
)
def qsummary(port=config.port, ip_address=config.ip_address):

    config.port = port
    config.ip_address = ip_address

    try:
        response = requests.get(
            f"{config.url}/api_v1/qsummary"
        )

        for k, v in response.json().items():
            print(f'{k}: {v}')

    except (urllib3.exceptions.NewConnectionError, requests.exceptions.ConnectionError):
        print(f'Could not reach lqts server at "{config.url}')


if __name__ == "__main__":
    qsummary()
