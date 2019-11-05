import os

import requests
import click
import ujson

from lqts.schema import JobSpec, JobID, DEFAULT_CONFIG
from .click_ext import OptionNargs

import lqts.environment


def encode_path(p):
    return p.replace("\\", "/")


@click.command("qsub")
@click.argument("command", nargs=1)
@click.argument("args", nargs=-1)
@click.option("--priority", default=10, type=int)
@click.option("--logfile", default="", type=str)
@click.option("-d", "--depends", cls=OptionNargs, default=list, type=list)
@click.option("--debug", is_flag=True, default=False)
def qsub(command, args, priority=10, logfile=None, depends=None, debug=False):

    command_str = command + " " + " ".join(f'"{arg}"' for arg in args)
    # print(command)
    working_dir = encode_path(os.getcwd())

    if len(depends) == 1 and " " in depends[0]:
        depends = depends[0].split()

    print(depends)
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
    print(job_spec)
    # json_string = ujson.dumps([job_spec.dict()]).replace("\\", "")
    # print(json_string)
    response = requests.post(f"{DEFAULT_CONFIG.url}/qsub", json=[job_spec.dict()])

    if response.status_code == 200:
        if debug:
            print(response)

        print(" ".join(str(item) for item in response.json()))
    else:
        print(response)


@click.command("qsub-m")
@click.argument("command", nargs=1)
@click.argument("files", nargs=1)
@click.argument("args", nargs=-1)
@click.option("--priority", default=10, type=int)
# @click.option("--logfile", default="", type=str)
@click.option("-d", "--depends", cls=OptionNargs, default=list)
@click.option("--debug", is_flag=True, default=False)
@click.option("--no-log", is_flag=True, default=False)
def qsub_m(command, files, args, priority=10, logfile=None, depends=None, debug=False, no_log=False):
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
        if no_log:
            logfile = None
        else:
            logfile = f + '.lqts.log'

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

        print(" ".join(str(item) for item in response.json()))
    else:
        print(response)


@click.command("qsub-argfile")
@click.argument("command", nargs=1)
@click.argument("argfile", nargs=1)
@click.option("--priority", default=10, type=int)
@click.option("--logfile", default="", type=str)
@click.option("-d", "--depends", cls=OptionNargs, default=list)
@click.option("--debug", is_flag=True, default=False)
def qsub_argfile(
    command, argfile, priority=10, logfile=None, depends=None, debug=False
):

    from glob import glob

    files = glob(files)

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

        print(" ".join(str(item) for item in response.json()))
    else:
        print(response)
