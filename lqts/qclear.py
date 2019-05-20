import requests
import click
import os

import ujson

from .schema import Job


@click.command("qclear")
# @click.argument("command", nargs=1)
# @click.argument("args", nargs=-1)
# @click.option("--priority", default=10, type=int)
# @click.option("--logfile", default='', type=str)
@click.option("--yes", is_flag=True, default=False)
@click.option("--debug", is_flag=True, default=False)
def qclear(yes=False, debug=False):

    if yes:
        answer = "yes"
    else:
        answer = input("Clear out the queue?!?!?")

    if answer.lower() in ("y", "yes"):
        response = requests.post("http://127.0.0.1:8000/qclear?really=true")
        print(response.text)
