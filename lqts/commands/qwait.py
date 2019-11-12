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

from lqts.schema import JobSpec, JobID, JobStatus, DEFAULT_CONFIG, Job

# from lqts.click_ext import OptionNargs

import lqts.environment


@click.command("qwait")
@click.argument("job_ids", nargs=-1)
@click.option("--interval", "-i", type=int, default=5)
@click.option("--port", type=int, default=DEFAULT_CONFIG.port)
def qwait(job_ids=None, interval=5, port=DEFAULT_CONFIG.port, verbose=0):

    if not job_ids:
        # get the job ids from standard input
        job_id_string = "".join(c for c in sys.stdin.read() if c in digits)
        job_ids = job_id_string.split()

    # Parse the job ids
    job_ids = set(JobID.parse_obj(jid) for jid in job_ids)

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

        if len(waiting_on) > 0:
            done_waiting = False
            time.sleep(interval)
            if t is None:
                if len(waiting_on) <= 20:
                    msg = str(waiting_on)
                else:
                    msg = f"{len(waiting_on)} jobs"
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
