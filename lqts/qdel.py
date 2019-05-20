import requests
import click
import os

import ujson

from .schema import Job
import lqts.displaytable as dt
from lqts.schema import JobID


@click.command("qdel")
# @click.argument("command", nargs=1)
# @click.argument("args", nargs=-1)
# @click.option("--priority", default=10, type=int)
# @click.option("--logfile", default='', type=str)
@click.argument("job_ids", nargs=-1)
@click.option("--debug", is_flag=True, default=False)
def qdel(job_ids, debug=False):

    job_ids = [JobID.parse(jid).dict() for jid in job_ids]

    response = requests.post("http://127.0.0.1:8000/qdel", json=job_ids)

    if debug:
        print(response.json())
    else:
        print(response.text)
