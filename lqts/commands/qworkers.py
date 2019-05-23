import os
from multiprocessing import cpu_count
from lqts.schema import DEFAULT_CONFIG
import requests
import click

from .click_ext import OptionNargs

import lqts.environment


@click.command("qworkers")
@click.argument("count", type=int, default=None, required=False)
def qworkers(count, debug=False):
    """
    Gets or sets the number of workers in the server process pool.  Without an argument
    this returns the current number of workers being used.
    """
    if count:
        count = int(count)
        response = requests.post(
            "{}/workers?count={}".format(DEFAULT_CONFIG.url, count)
        )
        print("Worker pool resized to {} workers".format(int(response.text)))
    else:
        response = requests.get("{}/workers".format(DEFAULT_CONFIG.url))
        print("Worker pool size is {}".format(int(response.text)))


if __name__ == "__main__":
    qworkers()
