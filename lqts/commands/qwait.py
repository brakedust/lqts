import os

import requests
import click
import ujson

from lqts.schema import JobSpec, JobID, JobStatus, DEFAULT_CONFIG

# from lqts.click_ext import OptionNargs

import lqts.environment


@click.command("qwait")
@click.argument("jobs", nargs=-1)
@click.option("--interval", "-i", type=int, default=15)
@click.option("--port", type=int, default=DEFAULT_CONFIG.port)
def wait(jobs=None, interval=15, port=DEFAULT_CONFIG.port, verbose=0):

    jid = [JobID.parse(j) for j in jobs]

    response = requests.post(f"{DEFAULT_CONFIG.url}/qsummary")

    if response.status_code == 200:
        data = response.json()
        for status, count in data.items():
            print(f"{JobStatus(status):>15} {count}")
    else:
        print(response)
