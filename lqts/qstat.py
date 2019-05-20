import requests
import click
import os

import ujson

from .schema import Job
import lqts.displaytable as dt


@click.command("qstat")
# @click.argument("command", nargs=1)
# @click.argument("args", nargs=-1)
# @click.option("--priority", default=10, type=int)
# @click.option("--logfile", default='', type=str)
@click.option("--debug", is_flag=True, default=False)
def qstat(debug=False):

    response = requests.get("http://127.0.0.1:8000/qstat")  # , json=message)

    if debug:
        print(response.json())
    else:
        jobs = (Job(**ujson.loads(item)) for item in response.json())

        # td = dt.tablize(
        #                 data,
        #                 include=['job_id', 'command', 'status', 'started', 'walltime'])
        rows = [["ID", "St", "Command", "Walltime", "WorkingDir", "DependsOn"]]
        for job in jobs:
            job: Job = job
            rows.append(
                [
                    job.job_id,
                    job.status.value,
                    job.job_spec.command,
                    job.walltime,
                    job.job_spec.working_dir,
                    str(job.job_spec.depends),
                ]
            )

        t = dt.make_table(rows, colsep="|", use_rowsep=False, maxwidth=80)
        print(t)
