import requests
import click
import os

import ujson

from .work_queue import Job


@click.command("qsub")
# @click.argument("command", nargs=1)
# @click.argument("args", nargs=-1)
# @click.option("--priority", default=10, type=int)
# @click.option("--logfile", default='', type=str)
def qstat():
    

    # command = command + " " + " ".join(f'"{arg}"' for arg in  args)
    # print(command)
    # working_dir = os.getcwd()

    # message = {
    #     "command": command,
    #     "working_dir": working_dir,
    #     "logfile": logfile,
    #     "priority": priority
    # }
    
    response = requests.get("http://127.0.0.1:8000/qstat")  #, json=message)
    print(response.json())
    jobs = (Job(**ujson.loads(item)) for item in response.json())

    for job in jobs:
        job:Job = job
        print(job.job_id, job.status, job.spec.command, job.walltime)