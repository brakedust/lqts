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
from .qsub_argfile import _qsub_argfile


@click.command("qsub-test")
@click.argument("duration", type=int)
@click.option("--count", default=1, type=int, help="Number of jobs to submit")
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
def qsub_test(
    duration,
    count,
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
    """Easily submit some test jobs to the queue for testing and experimenting. This command
    writes a batch file 'sleepy.bat' and 'argfile.txt'.  It then uses qsub-argfile to submit
    the commands.

    The duration argument is how long each job should last.  They just call sleep.
    """

    Path("sleepy.bat").write_text(
        f"echo Falling asleep...\nsleep {duration}\necho %1\necho %2\necho Waking up\nexit"
    )

    with open("argfile.txt", "w") as fid:
        for i in range(count):
            fid.write(f"argument {i}\n")

    _qsub_argfile(
        command="sleepy.bat",
        argfile="argfile.txt",
        log=log,
        priority=priority,
        depends=depends,
        debug=debug,
        cores=cores,
        port=port,
        ip_address=ip_address,
        alternate_runner=alternate_runner,
        walltime=walltime,
    )


def app():
    qsub_test(windows_expand_args=False)
