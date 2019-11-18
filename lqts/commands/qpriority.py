import os
import time
import sys
import chardet
from string import digits

digits += ". "

import requests
import click
import ujson
import tqdm

from lqts.schema import JobSpec, JobID, JobStatus, Job
from lqts.config import DEFAULT_CONFIG, Configuration

# from lqts.click_ext import OptionNargs

import lqts.environment


@click.command("qpriority")
@click.argument("priority", nargs=1)
@click.argument("job_ids", nargs=-1)
@click.option("--port", type=int, default=DEFAULT_CONFIG.port)
def qpriority(priority=10, job_ids=None, port=DEFAULT_CONFIG.port):

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

    job_ids = set(job_ids)

    respoonse = requests.post(
        f"{DEFAULT_CONFIG.url}/qpriority",
        data={}



if __name__ == "__main__":
    qpriority()
