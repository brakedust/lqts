import os

import requests
import click
import ujson

from lqts.schema import JobSpec, JobID, JobStatus, DEFAULT_CONFIG
from .click_ext import OptionNargs

import lqts.environment


@click.command("qwait")
@click.argument("args", nargs=-1)
@click.option("--priority", default=10, type=int)
@click.option("--logfile", default="", type=str)
@click.option("-d", "--depends", cls=OptionNargs, default=list)
@click.option("--debug", is_flag=True, default=False)
def wait(jobs=None, interval=15, port=9126, verbose=0):

    jid = [JobID.parse(j) for j in jobs]

    response = requests.post(f"{DEFAULT_CONFIG.url}/qsummary")

    if response.status_code == 200:
        data = response.json()
        for status, count in data.items():
            print(f"{JobStatus(status):>15} {count}")
    else:
        print(response)
