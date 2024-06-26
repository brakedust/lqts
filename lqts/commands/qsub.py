import json
import os
from itertools import chain
from pathlib import Path

import click
import requests

from lqts.core.config import config
from lqts.core.schema import JobID, JobSpec
from lqts.path_util import encode_path, find_file
from lqts.qsub_util import get_job_ids, parse_walltime

from .click_ext import OptionNargs


@click.command("qsub")
@click.argument("command", nargs=1)
@click.argument("args", nargs=-1)
@click.option("--priority", default=1, type=int)
@click.option("--logfile", default="", type=str, help="Name of log file")
@click.option(
    "--log",
    is_flag=True,
    default=False,
    help="Create a log file based on the command name",
)
@click.option(
    "-d",
    "--depends",
    cls=OptionNargs,
    default=list,
    type=list,
    help="Specify one or more jobs that these batch of jobs depend on."
    " They will be held until those jobs complete",
)
@click.option("--debug", is_flag=True, default=False, help="Produce debug output")
@click.option(
    "--walltime",
    type=str,
    default=None,
    help=(
        "A amount of time a job is allowed to run.  "
        + "It will be killed after this amount [NOT IMPLEMENTED YET]"
    ),
)
@click.option(
    "--cores", type=int, default=1, help="Number of cores/threads required by the job"
)
@click.option("--port", default=config.port, help="The port number of the server")
@click.option(
    "--ip_address", default=config.ip_address, help="The IP address of the server"
)
@click.option(
    "--alternate-runner",
    "-a",
    is_flag=True,
    default=False,
    help=(
        "Runs the submitted command in a slightly different manner.  "
        "In rare cases an executable can start, then hang.  "
        "However, the log file isn't updated until the process terminates."
    ),
)
def qsub(
    command,
    args,
    priority=1,
    logfile=None,
    log=False,
    depends=None,
    debug=False,
    walltime=None,
    cores=1,
    port=config.port,
    ip_address=config.ip_address,
    alternate_runner=False,
):
    """Submits one job to the queue"""

    command = find_file(command)
    if command is None:
        print("command not found")
        return

    command_str = f'"{command}"'

    if args:
        command_str += " " + " ".join(f'"{arg}"' for arg in args)

    working_dir = encode_path(os.getcwd())

    if depends:
        depends = list(chain(*[get_job_ids(d) for d in depends]))

    if walltime:
        walltime = parse_walltime(walltime)

    if log and not logfile:
        logfile = str(Path(command).with_suffix(".lqts.log"))

    job_spec = JobSpec(
        command=command_str,
        working_dir=working_dir,
        log_file=logfile,
        priority=priority,
        depends=depends,
        walltime=walltime,
        cores=cores,
        alternate_runner=alternate_runner,
    )

    if debug:
        print([job_spec.dict()])

    config.port = port
    config.ip_address = ip_address

    response = requests.post(f"{config.url}/api_v1/qsub", json=[job_spec.dict()])

    if response.status_code == 200:
        if debug:
            print(response)

        json_data = response.json()
        if len(json_data) <= 20:
            print(" ".join(str(JobID(**item)) for item in response.json()))
        else:
            print(JobID(**json_data[0]).group)
    else:
        print(response)


def app():
    qsub(windows_expand_args=False)
