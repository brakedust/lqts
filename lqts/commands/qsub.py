import os

import requests
import click
import ujson

from lqts.schema import JobSpec, JobID
from .click_ext import OptionNargs

import lqts.environment
from lqts.config import DEFAULT_CONFIG


def encode_path(p):
    return p.replace("\\", "/")


@click.command("qsub")
@click.argument("command", nargs=1)
@click.argument("args", nargs=-1)
@click.option("--priority", default=1, type=int)
@click.option("--logfile", default="", type=str)
@click.option("-d", "--depends", cls=OptionNargs, default=list, type=list)
@click.option("--debug", is_flag=True, default=False)
def qsub(command, args, priority=1, logfile=None, depends=None, debug=False):

    command_str = command + " " + " ".join(f'"{arg}"' for arg in args)
    # print(command)
    working_dir = encode_path(os.getcwd())

    if len(depends) == 1 and " " in depends[0]:
        depends = depends[0].split()

    # print(depends)
    if depends:
        depends = [JobID.parse_obj(d) for d in depends]
    else:
        depends = []

    job_spec = JobSpec(
        command=command_str,
        working_dir=working_dir,
        log_file=logfile,
        priority=priority,
        depends=depends,
    )
    # print(job_spec)
    # json_string = ujson.dumps([job_spec.dict()]).replace("\\", "")
    # print(json_string)
    response = requests.post(f"{DEFAULT_CONFIG.url}/qsub", json=[job_spec.dict()])

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
@click.argument("files", nargs=1)
@click.argument("args", nargs=-1)
@click.option("--priority", default=1, type=int)
# @click.option("--logfile", default="", type=str)
@click.option("-d", "--depends", cls=OptionNargs, default=list)
@click.option("--debug", is_flag=True, default=False)
@click.option("--log", is_flag=True, default=False)
def qsub_cmulti(
    command,
    files,
    args,
    priority=1,
    logfile=None,
    depends=None,
    debug=False,
    log=False,
):
    """
    Run **command** for each file in **files**.  Pass in args.

    $ qsub mycommand.exe *.inp -- --do --it
    """

    from glob import iglob

    files = iglob(files)

    job_specs = []
    working_dir = encode_path(os.getcwd())

    depends = [JobID.parse(d) for d in depends]

    for f in files:
        # print(f, print(args))
        command_str = f"{command} {f} " + " ".join(f'"{arg}"' for arg in args)
        # print(command)
        if log:
            logfile = f"{f}.lqts.log"
        else:
            logfile = None


        js = JobSpec(
            command=command_str,
            working_dir=working_dir,
            log_file=logfile,
            priority=priority,
            depends=depends,
        )
        job_specs.append(js.dict())

    if debug:
        for js in job_specs:
            print(js)

    response = requests.post(f"{DEFAULT_CONFIG.url}/qsub", json=job_specs)

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
# @click.option("--logfile", default="", type=str)
@click.option("-d", "--depends", cls=OptionNargs, default=list)
@click.option("--debug", is_flag=True, default=False)
@click.option("--log", is_flag=True, default=False)
def qsub_multi(
    commands,
    args,
    priority=1,
    logfile=None,
    depends=None,
    debug=False,
    log=False,
):
    """
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
            logfile = command + ".lqts.log"
        else:
            logfile = None

        js = JobSpec(
            command=command_str,
            working_dir=working_dir,
            log_file=logfile,
            priority=priority,
            depends=depends,
        )
        job_specs.append(js.dict())

    if debug:
        for js in job_specs:
            print(js)

    response = requests.post(f"{DEFAULT_CONFIG.url}/qsub", json=job_specs)

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
@click.option("--logfile", default="", type=str)
@click.option("-d", "--depends", cls=OptionNargs, default=list)
@click.option("--debug", is_flag=True, default=False)
@click.option("--submit-delay")
def qsub_argfile(
    command,
    argfile,
    priority=1,
    logfile=None,
    depends=None,
    debug=False,
    submit_delay=0.0,
):

    from glob import glob

    # files = glob(files)

    job_specs = []
    working_dir = encode_path(os.getcwd())

    depends = [JobID.parse(d) for d in depends]

    with open(argfile) as f:

        for argline in f:

            command_str = f"{command} {argline}"
            # print(command)

            js = JobSpec(
                command=command_str,
                working_dir=working_dir,
                log_file=logfile,
                priority=priority,
                depends=depends,
            )
            job_specs.append(js.dict())

    if debug:
        for js in job_specs:
            print(js)

    response = requests.post(f"{DEFAULT_CONFIG.url}/qsub", json=job_specs)

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
