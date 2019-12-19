import requests
import click
import os
from pathlib import Path

import ujson

from lqts.schema import Job
from lqts.config import Configuration

import lqts.environment

if Path(".env").exists():
    config = Configuration.load_env_file(".env")
else:
    config = Configuration()


@click.command("qclear")
@click.option("--yes", is_flag=True, default=False)
@click.option("--debug", is_flag=True, default=False)
@click.option("--port", default=config.port, help="The port number of the server")
@click.option(
    "--ip_address", default=config.ip_address, help="The IP address of the server"
)
def qclear(yes=False, debug=False, port=config.port, ip_address=config.ip_address):

    if yes:
        answer = "yes"
    else:
        answer = input("Clear out the queue?!?!?")

    config.port = port
    config.ip_address = ip_address

    if answer.lower() in ("y", "yes"):
        response = requests.post(f"{config.url}/qclear?really=true")
        print(response.text)
