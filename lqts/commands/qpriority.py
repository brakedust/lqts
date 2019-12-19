import os
import time
import sys
from pathlib import Path
from string import digits

digits += ". "

import requests
import click
import ujson
import tqdm

from lqts.schema import JobSpec, JobID, JobStatus, Job
from lqts.config import Configuration

# from lqts.click_ext import OptionNargs

import lqts.environment

if Path(".env").exists():
    config = Configuration.load_env_file(".env")
else:
    config = Configuration()


@click.command("qpriority")
@click.argument("priority", nargs=1)
@click.argument("job_ids", nargs=-1)
@click.option("--port", default=config.port, help="The port number of the server")
@click.option(
    "--ip_address", default=config.ip_address, help="The IP address of the server"
)
def qpriority(
    priority=10, job_ids=None, port=config.port, ip_address=config.ip_address
):
    """Change the priority of one or more jobs"""

    if not job_ids and sys.stdin.seekable():
        # get the job ids from standard input
        job_id_string = "".join(c for c in sys.stdin.read() if c in digits)
        job_ids = job_id_string.split()

    if not job_ids:
        print("no jobs to wait on.")
        return

    config.port = port
    config.ip_address = ip_address

    # Parse the job ids
    input_job_ids = job_ids
    job_ids = []
    for job_id in list(input_job_ids):
        if "." not in job_id:
            # A job group was specified
            response = requests.get(f"{config.url}/jobgroup?group_number={int(job_id)}")
            # print(response.json())
            if response.status_code == 200:
                job_ids.extend([JobID(**item) for item in response.json()])

        else:
            job_ids.append(JobID.parse_obj(job_id))

    # job_ids = set(job_ids)
    job_ids = [jid.dict() for jid in set(job_ids)]
    # data = {"priority": priority, "job_ids": job_ids}
    # print(data)
    response = requests.post(f"{config.url}/qpriority", params={"priority":priority}, json=job_ids)

    print(response.text)

if __name__ == "__main__":
    qpriority()
