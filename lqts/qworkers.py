import os
from multiprocessing import cpu_count

import requests
import click

# import ujson

# from lqts.schema import JobSpec, JobID
from lqts.click_ext import OptionNargs


@click.command("qworkers")
@click.argument("count", type=int, default=None, required=False)
def qworkers(count, debug=False):
    """
    Gets or sets the number of workers in the server process pool.  Without an argument
    this returns the current number of workers being used.
    """
    if count:
        count = int(count)
        response = requests.post("http://127.0.0.1:8000/workers?count={}".format(count))
        print("Worker pool resized to {} workers".format(int(response.text)))
    else:
        response = requests.get("http://127.0.0.1:8000/workers")
        print("Worker pool size is {}".format(int(response.text)))


if __name__ == "__main__":
    qworkers()
