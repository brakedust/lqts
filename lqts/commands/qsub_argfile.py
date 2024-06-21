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


@click.command("qsub-argfile")
@click.argument("command", nargs=1)
@click.argument("argfile", nargs=1)
@click.option("--priority", default=1, type=int)
# @click.option("--logfile", default="", type=str)
@click.option("-d", "--depends", cls=OptionNargs, default=list)
@click.option("--debug", is_flag=True, default=False)
@click.option("--submit-delay")
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
def qsub_argfile(
    command,
    argfile,
    priority=1,
    log=False,
    depends=None,
    debug=False,
    submit_delay=0.0,
    cores=1,
    port=config.port,
    ip_address=config.ip_address,
    alternate_runner=False,
):
    """Submits multiple jobs to the queue.

    Use this if you have a program you want to run with different sets of arguments
    where each set of arguments are one line in the **argfile**.
    """
    _qsub_argfile(
        command,
        argfile,
        priority,
        log,
        depends,
        debug,
        submit_delay,
        cores,
        port,
        ip_address,
        alternate_runner,
    )


def _qsub_argfile(
    command,
    argfile,
    priority=1,
    log=False,
    depends=None,
    debug=False,
    submit_delay=0.0,
    cores=1,
    port=config.port,
    ip_address=config.ip_address,
    alternate_runner=False,
    walltime=None,
):

    from glob import glob

    # files = glob(files)
    command = Path(command).absolute()

    job_specs = []
    working_dir = encode_path(os.getcwd())

    if depends:
        depends = list(chain(*[get_job_ids(d) for d in depends]))

    with open(argfile) as f:

        for iline, argline in enumerate(f):

            command_str = f"{command} {argline.strip()}"
            # print(command)

            if log:
                log_file = str(Path(argfile).with_suffix(f".lqts.{iline:0>3}.log"))
            else:
                log_file = None

            js = JobSpec(
                command=command_str,
                working_dir=working_dir,
                log_file=log_file,
                priority=priority,
                depends=depends,
                cores=cores,
                alternate_runner=alternate_runner,
                walltime=walltime,
            )
            js = JobSpec.model_validate(js)
            job_specs.append(js.model_dump())

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
    elif response.status_code == 422:
        print(json.dumps(response.json(), indent=4))
    else:
        print(response)


def app():
    qsub_argfile(windows_expand_args=False)
