import json
import os
from itertools import chain
from pathlib import Path

import click
import requests

from lqts.core.schema import JobID, JobSpec
from lqts.path_util import encode_path, find_file
from lqts.qsub_util import config, get_job_ids, parse_walltime

from .click_ext import OptionNargs


@click.command("qsub-multi")
@click.argument("commands", nargs=1, type=str)
@click.argument("args", nargs=-1, type=str)
@click.option("--priority", default=1, type=int)
@click.option(
    "-d",
    "--depends",
    cls=OptionNargs,
    default=list,
    help="Specify one or more jobs that these batch of jobs depend on."
    " They will be held until those jobs complete",
)
@click.option("--debug", is_flag=True, default=False)
@click.option(
    "--log",
    is_flag=True,
    default=False,
    help="Create a log file for each command submitted",
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
@click.option(
    "--walltime",
    type=str,
    default=None,
    help=(
        "A amount of time a job is allowed to run like HH:MM:SS or in seconds.  "
        + "It will be killed after this amount"
    ),
)
def qsub_multi(
    commands,
    args,
    priority=1,
    logfile=None,
    depends=None,
    debug=False,
    log=False,
    cores=1,
    port=config.port,
    ip_address=config.ip_address,
    alternate_runner=False,
    walltime=None,
):
    """
    Submits mutilple jobs to the queue.

    Use this if have have multiple commands that you wish to run and
    you can specify them with a glob pattern

    $ qsub mycommand*.bat -- --option1 --option2 value2
    """

    from glob import iglob

    # commands = iglob(commands)

    job_specs = []
    working_dir = encode_path(os.getcwd())

    if depends:
        depends = list(chain(*[get_job_ids(d) for d in depends]))

    if walltime:
        walltime = parse_walltime(walltime)

    for command in iglob(commands):
        # print(f, print(args))
        # command = Path(command).absolute()
        resolved_command = find_file(command)
        if resolved_command is None:
            print(f"Command '{command}' not found.")
        print(resolved_command)
        command_str = f'"{resolved_command}"'
        if args:
            command_str += " " + " ".join(f'"{arg}"' for arg in args)
        # print(command)
        if log:
            logfile = str(Path(resolved_command).with_suffix(".lqts.log"))
        else:
            logfile = None

        js = JobSpec(
            command=command_str,
            working_dir=working_dir,
            log_file=logfile,
            priority=priority,
            depends=depends,
            cores=cores,
            alternate_runner=alternate_runner,
            walltime=walltime,
        )
        job_specs.append(js.dict())

    if debug:
        for js in job_specs:
            print(js)

    config.port = port
    config.ip_address = ip_address

    response = requests.post(f"{config.url}/api_v1/qsub", json=job_specs)

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
    qsub_multi(windows_expand_args=False)
