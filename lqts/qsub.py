import requests
import click
import os
from .schema import JobSpec, JobID


@click.command("qsub")
@click.argument("command", nargs=1)
@click.argument("args", nargs=-1)
@click.option("--priority", default=10, type=int)
@click.option("--logfile", default='', type=str)
@click.option("-d", "--depend-on", default=None, type=str)
def qsub(command, args, priority=10, logfile=None, depend_on=None):
    
    command = command + " " + " ".join(f'"{arg}"' for arg in  args)
    print(command)
    working_dir = os.getcwd()

    job_spec = JobSpec(
        command=command,
        working_dir=working_dir,
        logfile=logfile,
        priority=priority,
        depend_on=JobID.parse(depend_on) if depend_on else None
    )    
    # message = {
    #     "command": command,
    #     "working_dir": working_dir,
    #     "logfile": logfile,
    #     "priority": priority
    # }
    print(job_spec.dict())
    response = requests.post("http://127.0.0.1:8000/qsub", json=job_spec.dict())
    print(response.text.strip('"'))