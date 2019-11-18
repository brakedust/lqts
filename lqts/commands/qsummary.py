import requests
import click
import os

import ujson

from lqts.config import DEFAULT_CONFIG
from lqts.schema import Job, JobID
import lqts.displaytable as dt

import lqts.environment

import urllib3.exceptions
import requests.exceptions

@click.command("qsummary")
def qsummary():


    try:
        response = requests.get(
            f"{DEFAULT_CONFIG.url}/qsummary"
        )

        for k, v in response.json().items():
            print(f'{k}: {v}')

    except (urllib3.exceptions.NewConnectionError, requests.exceptions.ConnectionError):
        print(f'Could not reach lqts server at "{DEFAULT_CONFIG.url}')



if __name__ == "__main__":
    qsummary()