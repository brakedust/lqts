import sys
from string import digits

import click
import requests

from lqts.core.config import config
from lqts.core.schema import JobID

digits += ". "


@click.command("qresume")
@click.argument("job_ids", nargs=-1)
@click.option("--debug", is_flag=True, default=False)
@click.option("--port", default=config.port, help="The port number of the server")
@click.option("--ip_address", default=config.ip_address, help="The IP address of the server")
def qresume(job_ids, debug=False, port=config.port, ip_address=config.ip_address):
    """Resume paused jobs from the queue"""

    if not job_ids and sys.stdin.seekable():
        # get the job ids from standard input
        job_id_string = "".join(c for c in sys.stdin.read() if c in digits)
        job_ids = job_id_string.split()

    if job_ids:
        config.port = port
        config.ip_address = ip_address

        # Parse the job ids
        input_job_ids = job_ids
        job_ids = []
        for job_id in list(input_job_ids):
            if "." not in job_id:
                # A job group was specified
                response = requests.get(f"{config.url}/api_v1/jobgroup?group_number={int(job_id)}")
                # print(response.json())
                if response.status_code == 200:
                    job_ids.extend([JobID(**item) for item in response.json()])

            else:
                job_ids.append(JobID.parse_obj(job_id))

        job_ids = [jid.dict() for jid in set(job_ids)]
    else:
        job_ids = []

    print(f"Requesting resumption of jobs: {[str(JobID(**rj)) for rj in job_ids]}")
    # job_ids = [jid.dict() for jid in set(job_ids)]
    response = requests.post(f"{config.url}/api_v1/resume", json=job_ids)

    resjobs = [JobID(**item) for item in response.json()]
    print(f"Jobs resumed: {[str(rj) for rj in resjobs]}")
