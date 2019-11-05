import requests
import click
import os

import ujson

from lqts.schema import Job, DEFAULT_CONFIG
import lqts.displaytable as dt

import lqts.environment


@click.command("qstat")
# @click.argument("command", nargs=1)
# @click.argument("args", nargs=-1)
# @click.option("--priority", default=10, type=int)
# @click.option("--logfile", default='', type=str)
@click.option("--debug", is_flag=True, default=False)
@click.option("--completed", "-c", is_flag=True, default=False)
def qstat(debug=False, completed=False):

    options = {"completed": completed}
    response = requests.get(
        f"{DEFAULT_CONFIG.url}/qstat", json=options
    )  # , json=message)

    if debug:
        print(response)
    else:
        jobs = [Job(**ujson.loads(item)) for item in response.json()]
        # print(jobs)
        # td = dt.tablize(
        #                 data,
        #                 include=['job_id', 'command', 'status', 'started', 'walltime'])
        rows = [["ID", "St", "Command", "Walltime", "WorkingDir", "Dependencies"]]
        for job in jobs:
            job: Job = job
            rows.append(
                [
                    job.job_id,
                    job.status.value,
                    job.job_spec.command if job.job_spec is not None else "",
                    job.walltime,
                    job.job_spec.working_dir,
                    ",".join(str(d) for d in job.job_spec.depends),
                ]
            )

        t = dt.make_table(rows, colsep="|", use_rowsep=False, maxwidth=80)
        print(t)
