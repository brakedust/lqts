import os
from pathlib import Path

import click
import requests
import ujson

import lqts.displaytable as dt
from lqts.core.config import config
from lqts.core.schema import Job, JobID


@click.command("qstat")
@click.option("--debug", is_flag=True, default=False)
@click.option("--completed", "-c", is_flag=True, default=False)
@click.option("--running", "-r", is_flag=True, default=False)
@click.option("--queued", "-q", is_flag=True, default=False)
@click.option("--port", default=config.port, help="The port number of the server")
@click.option(
    "--ip_address", default=config.ip_address, help="The IP address of the server"
)
def qstat(
    debug=False,
    completed=False,
    running=False,
    queued=False,
    port=config.port,
    ip_address=config.ip_address,
):
    """Prints a table of the queue status to the terminal."""

    options = (completed, running, queued)
    if not any(options):
        options = {
            "completed": False,
            "running": True,
            "queued": True,
        }
    else:
        options = {
            "completed": completed,
            "running": running,
            "queued": queued,
        }

    config.port = port
    config.ip_address = ip_address

    response = requests.get(f"{config.url}/api_v1/qstat", json=options)

    if debug:
        print(response.text)
    else:
        # print(response.json())
        jobs = [Job.model_validate_json(item) for item in response.json()]

        rows = [["ID", "St", "Pr", "Command", "Walltime", "WorkingDir", "Dep"]]
        for job in jobs:
            job: Job = job
            rows.append(
                [
                    job.job_id,
                    job.status.value,
                    job.job_spec.priority,
                    job.job_spec.command if job.job_spec is not None else "",
                    job.walltime,
                    job.job_spec.working_dir,
                    (
                        ",".join(str(d) for d in job.job_spec.depends)
                        if job.job_spec.depends
                        else "-"
                    ),
                ]
            )

        t = dt.make_table(rows, colsep="|", use_rowsep=False, maxwidth=90)
        print(t)
