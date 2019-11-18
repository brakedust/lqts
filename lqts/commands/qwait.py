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


@click.command("qwait")
@click.argument("job_ids", nargs=-1)
@click.option("--interval", "-i", type=float, default=5)
@click.option("--port", type=int, default=DEFAULT_CONFIG.port)
def qwait(job_ids=None, interval=5, port=DEFAULT_CONFIG.port, verbose=0):

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

    t = None
    done_waiting = False
    num_jobs_left = None

    while not done_waiting:
        options = {"completed": False}

        response = requests.get(
            f"{DEFAULT_CONFIG.url}/qstat", json=options
        )  # , json=message)

        queued_or_running_job_ids = set(
            Job(**ujson.loads(item)).job_id for item in response.json()
        )

        waiting_on = job_ids.intersection(queued_or_running_job_ids)
        # print(waiting_on)
        if len(waiting_on) > 0:
            done_waiting = False
            time.sleep(interval)
            if t is None:
                if len(waiting_on) <= 20:
                    msg = str(waiting_on)
                else:
                    lsw = list(sorted(waiting_on))
                    msg = f"{len(waiting_on)} jobs: {lsw[0]} - {lsw[-1]}"
                    del lsw
                print(f"Waiting on {msg}")
                t = tqdm.tqdm(total=len(waiting_on))

                num_jobs_left = len(waiting_on)
            else:
                num_finshed = num_jobs_left - len(waiting_on)
                t.update(num_finshed)
                num_jobs_left = len(waiting_on)
        else:
            done_waiting = True


if __name__ == "__main__":
    qwait()
