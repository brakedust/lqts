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
def qstat(debug=False):

    response = requests.get(f"{DEFAULT_CONFIG.url}/qstat")  # , json=message)

    if debug:
        print(response)
    else:
        jobs = (Job(**ujson.loads(item)) for item in response.json())

        # td = dt.tablize(
        #                 data,
        #                 include=['job_id', 'command', 'status', 'started', 'walltime'])
        rows = [["ID", "St", "Command", "Walltime", "WorkingDir", "Dep / CmplDep"]]
        for job in jobs:
            job: Job = job
            rows.append(
                [
                    job.job_id,
                    job.status.value,
                    job.job_spec.command,
                    job.walltime,
                    job.job_spec.working_dir,
                    "{} / {}".format(
                        ",".join(str(d) for d in job.job_spec.depends)
                        if job.job_spec.depends
                        else "-",
                        ",".join(str(d) for d in job.completed_depends)
                        if job.completed_depends
                        else "-",
                    ),
                ]
            )

        t = dt.make_table(rows, colsep="|", use_rowsep=False, maxwidth=80)
        print(t)
