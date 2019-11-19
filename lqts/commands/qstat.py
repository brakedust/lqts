import requests
import click
import os

import ujson

from lqts.config import DEFAULT_CONFIG
from lqts.schema import Job, JobID
import lqts.displaytable as dt

import lqts.environment


@click.command("qstat")
# @click.argument("command", nargs=1)
# @click.argument("args", nargs=-1)
# @click.option("--priority", default=10, type=int)
# @click.option("--logfile", default='', type=str)
@click.option("--debug", is_flag=True, default=False)
@click.option("--completed", "-c", is_flag=True, default=False)
@click.option("--running", "-r", is_flag=True, default=False)
@click.option("--queued", "-q", is_flag=True, default=False)
def qstat(debug=False, completed=False, running=False, queued=False):

    options = (completed, running, queued)
    if not any(options):
        options = {"completed": False, "running":True, "queued": True}
    else:
        options = {"completed": completed, "running":running, "queued": queued}

    response = requests.get(
        f"{DEFAULT_CONFIG.url}/qstat", json=options
    )

    if debug:
        print(response.text)
    else:
        jobs = [Job(**ujson.loads(item)) for item in response.json()]

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
                    ",".join(str(d) for d in job.job_spec.depends)
                    if job.job_spec.depends
                    else "-",
                ]
            )

        t = dt.make_table(rows, colsep="|", use_rowsep=False, maxwidth=90)
        print(t)
