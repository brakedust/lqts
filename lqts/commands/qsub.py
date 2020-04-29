import os
from pathlib import Path
import requests
import click
import ujson

from lqts.schema import JobSpec, JobID
from .click_ext import OptionNargs

import lqts.environment
from lqts.config import Configuration


if Path(".env").exists():
    config = Configuration.load_env_file(".env")
else:
    config = Configuration()


def encode_path(p):
    return p.replace("\\", "/")


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
    help="A amount of time a job is allowed to run.  It will be killed after this amount [NOT IMPLEMENTED YET]",
)
@click.option(
    "--cores", type=int, default=1, help="Number of cores/threads required by the job"
)
@click.option("--port", default=config.port, help="The port number of the server")
@click.option(
    "--ip_address", default=config.ip_address, help="The IP address of the server"
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
):
    """Submits one job to the queue"""

    command_str = command + " " + " ".join(f'"{arg}"' for arg in args)

    working_dir = encode_path(os.getcwd())

    if len(depends) == 1 and " " in depends[0]:
        depends = depends[0].split()

    # print(depends)
    if depends:
        depends = [JobID.parse_obj(d) for d in depends]
    else:
        depends = []

    if walltime:
        if ":" in walltime:
            hrs, minutes, sec = [int(x) for x in walltime.split(":")]
            seconds = sec + 60 * minutes + hrs * 3600
        else:
            walltime = float(walltime)

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
    )

    config.port = port
    config.ip_address = ip_address

    response = requests.post(f"{config.url}/qsub", json=[job_spec.dict()])

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


@click.command("qsub-cmulti")
@click.argument("command", nargs=1)
@click.argument("file_pattern", nargs=1)
@click.argument("args", nargs=-1)
@click.option("--priority", default=1, type=int)
# @click.option("--logfile", default="", type=str)
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
):
    """
    Submits mutlitiple jobs to the queue.

    Runs **command** for each file in **files**.  Pass in args.

    $ qsub mycommand.exe MyInputFile*.inp -- --do --it

           [-----------] [--------------]    [--------]

             command        filepattern         args
    """

    from glob import iglob

    files = iglob(file_pattern)

    job_specs = []
    working_dir = encode_path(os.getcwd())

    depends = [JobID.parse(d) for d in depends]

    for f in files:
        # print(f, print(args))
        command_str = f"{command} {f} " + " ".join(f'"{arg}"' for arg in args)
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
        )
        job_specs.append(js.dict())

    if debug:
        for js in job_specs:
            print(js)

    config.port = port
    config.ip_address = ip_address

    response = requests.post(f"{config.url}/qsub", json=job_specs)

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
):
    """
    Submits mutilple jobs to the queue.

    Use this if have have multiple commands that you wish to run and
    you can specify them with a glob pattern

    $ qsub mycommand*.bat -- --option1 --option2 value2
    """

    from glob import iglob

    commands = iglob(commands)

    job_specs = []
    working_dir = encode_path(os.getcwd())

    depends = [JobID.parse(d) for d in depends]

    for command in commands:
        # print(f, print(args))
        command_str = f"{command} " + " ".join(f'"{arg}"' for arg in args)
        # print(command)
        if log:
            logfile = str(Path(command).with_suffix(".lqts.log"))
        else:
            logfile = None

        js = JobSpec(
            command=command_str,
            working_dir=working_dir,
            log_file=logfile,
            priority=priority,
            depends=depends,
            cores=cores,
        )
        job_specs.append(js.dict())

    if debug:
        for js in job_specs:
            print(js)

    config.port = port
    config.ip_address = ip_address

    response = requests.post(f"{config.url}/qsub", json=job_specs)

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
):

    from glob import glob

    # files = glob(files)

    job_specs = []
    working_dir = encode_path(os.getcwd())

    depends = [JobID.parse(d) for d in depends]

    with open(argfile) as f:

        for iline, argline in enumerate(f):

            command_str = f"{command} {argline}"
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
            )
            job_specs.append(js.dict())

    if debug:
        for js in job_specs:
            print(js)

    config.port = port
    config.ip_address = ip_address

    response = requests.post(f"{config.url}/qsub", json=job_specs)

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
    help="A amount of time a job is allowed to run.  It will be killed after this amount [NOT IMPLEMENTED YET]",
)
@click.option(
    "--cores", type=int, default=1, help="Number of cores/threads required by the job"
)
@click.option("--port", default=config.port, help="The port number of the server")
@click.option(
    "--ip_address", default=config.ip_address, help="The IP address of the server"
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
):
    """Easily submit some test jobs to the queue for testing and experimenting. This command
    writes a batch file 'sleepy.bat' and 'argfile.txt'.  It then uses qsub-argfile to submit
    the commands.

    The duration argument is how long each job should last.  They just call sleep.
    """

    Path("sleepy.bat").write_text(
        f"echo Falling asleep...\nsleep {duration}\necho %1\necho %2\necho Waking up"
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
        cores=cores
        # walltime=walltime
    )
