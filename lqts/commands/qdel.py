import requests
import click
import os

import ujson

from lqts.schema import Job
from lqts.config import DEFAULT_CONFIG
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

    # job_ids = [JobID.parse_obj(jid).dict() for jid in job_ids]


    # if debug:
    #     print(response.json())
    # else:
    #     print(response.text)

    if not job_ids and sys.stdin.seekable():
        # get the job ids from standard input
        job_id_string = "".join(c for c in sys.stdin.read() if c in digits)
        job_ids = job_id_string.split()

    if not job_ids:
        print("no jobs to wait on.")
        return

    # Parse the job ids
    input_job_ids = job_ids
    job_ids = []
    for job_id in list(input_job_ids):
        if "." not in job_id:
            # A job group was specified
            response = requests.get(
                f"{DEFAULT_CONFIG.url}/jobgroup?group_number={int(job_id)}"
            )
            # print(response.json())
            if response.status_code == 200:
                job_ids.extend([JobID(**item) for item in response.json()])

        else:
            job_ids.append(JobID.parse_obj(job_id))

    job_ids = [jid.dict() for jid in set(job_ids)]

    response = requests.post(f"{DEFAULT_CONFIG.url}/qdel", json=job_ids)

    print("Jobs deleted: " + response.text)