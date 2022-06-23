from multiprocessing import cpu_count
from pathlib import Path

import click
import requests
from lqts.core.config import Configuration
import lqts.environment

if Path(".env").exists():
    config = Configuration.load_env_file(".env")
else:
    config = Configuration()


@click.command("qworkers")
@click.argument("count", type=int, default=None, required=False)
@click.option("--port", default=config.port, help="The port number of the server")
@click.option(
    "--ip_address", default=config.ip_address, help="The IP address of the server"
)
def qworkers(count, debug=False, port=config.port, ip_address=config.ip_address):
    """
    Gets or sets the number of workers in the server process pool.  Without an argument
    this returns the current number of workers being used.
    """
    config.port = port
    config.ip_address = ip_address

    if count:
        count = int(count)
        response = requests.post("{}/api_v1/workers?count={}".format(config.url, count))
        print("Worker pool resized to {} workers".format(int(response.text)))
    else:
        response = ""
        try:
            response = requests.get("{}/api_v1/workers".format(config.url))
            print("Worker pool size is {}".format(int(response.text)))
        except:  # nopep8
            print(response.text)


if __name__ == "__main__":
    qworkers()
