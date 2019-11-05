import requests
import click
import os

import ujson

from lqts.schema import Job, DEFAULT_CONFIG
import lqts.displaytable as dt
from lqts.schema import JobID

import lqts.environment


@click.command("qdel")
# @click.argument("command", nargs=1)
# @click.argument("args", nargs=-1)
# @click.option("--priority", default=10, type=int)
# @click.option("--logfile", default='', type=str)
@click.argument("job_ids", nargs=-1)
@click.option("--debug", is_flag=True, default=False)
def qdel(job_ids, debug=False):

    job_ids = [JobID.parse_obj(jid).dict() for jid in job_ids]

    response = requests.post(f"{DEFAULT_CONFIG.url}/qdel", json=job_ids)

    if debug:
        print(response.json())
    else:
        print(response.text)
