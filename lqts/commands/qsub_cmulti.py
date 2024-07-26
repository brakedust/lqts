import os
from itertools import chain
from pathlib import Path

import click
import requests

from lqts.core.schema import JobID, JobSpec
from lqts.path_util import encode_path, find_file
from lqts.qsub_util import config, get_job_ids, parse_walltime

from .click_ext import OptionNargs


@click.command("qsub-cmulti")
@click.argument("command", nargs=1)
@click.argument("file_pattern", nargs=1, type=str)
@click.argument("args", nargs=-1)
@click.option("--priority", default=1, type=int)
# @click.option("--logfile", default="", type=str)
@click.option(
    "-d",
    "--depends",
    cls=OptionNargs,
    default=None,
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
    "--walltime",
    type=str,
    default=None,
    help=(
        "A amount of time a job is allowed to run.  "
        + "It will be killed after this amount [NOT IMPLEMENTED YET]"
    ),
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
    "--changewd",
    is_flag=True,
    help="Causes the working directory to be the parent directory of each input file."
    "  This is useful if your file_pattern traverses directories and there "
    "are additional files in those directories required for command to be successful",
)
def qsub_cmulti(
    command,
    file_pattern,
    args,
    priority=1,
    logfile=None,
    depends=None,
    debug=False,
    log=False,
    cores=1,
    port=config.port,
    ip_address=config.ip_address,
    walltime=None,
    alternate_runner=False,
    changewd=False,
):
    """
    Submits mutlitiple jobs to the queue.

    Runs **command** for each file in **files**.  Pass in args.

    $ qsub mycommand.exe MyInputFile*.inp -- --do --it

           [-----------] [--------------]    [--------]

             command        filepattern         args
    """

    from glob import iglob

    # files = []
    # for fp in file_pattern:
    #     files.append(list(iglob(fp)))
    files = list(iglob(file_pattern))

    print(files)

    # command = Path(command).absolute()
    resolved_command = find_file(command)
    if resolved_command is None:
        print(f"Command '{command}' not found in local directory or on PATH.")

    # print("file_patter:", file_pattern)
    # print(files)
    job_specs = []
    working_dir = encode_path(os.getcwd())

    if depends:
        depends = list(chain(*[get_job_ids(d) for d in depends]))
    else:
        depends = []

    if walltime:
        walltime = parse_walltime(walltime)

    for f in files:
        if changewd:
            working_dir = str(Path(f).absolute().parent)
            f = Path(f).name

        # print(f, print(args))
        command_str = f'"{resolved_command}" {f} ' + " ".join(
            f'"{arg}"' for arg in args
        )
        # print(command)
        if log:
            logfile = str(Path(f).with_suffix(".lqts.log"))
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
    qsub_cmulti(windows_expand_args=False)
