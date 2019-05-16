# -*- coding: utf-8 -*-
import os
import argh
from glob import glob
import asyncio
import json
#import sys
from ..pluglib import plg_mgr
from pprint import pprint
import re

async def submit_job(
        loop,
        command,
        filename,
        working_dir,
        log_file,
        args,
        port=9126):

    print('-'*30 + '\nSubmitting...')
    reader, writer = await asyncio.open_connection('127.0.0.1', port,
                                                   loop=loop)

    command = command.replace('\\', '/')
    working_dir = working_dir.replace('\\','/')
    filename = filename.replace('\\', '/')

    command = "{} {} {}".format(command, filename, args)

    data = {"command": command,
            "working_dir": working_dir,
            "log_file": log_file,
            'type': 'submit',
            'args': args}

    pprint(data)

    message = json.dumps(data)

    writer.write(message.encode())
    writer.write_eof()
    await writer.drain()

    data = await reader.read()
    job_id = int(data.decode())
    writer.close()
    print('\nSubmitted Job ID: {}'.format(job_id))


@plg_mgr.register
@argh.arg('command', help='Path to executable file or script to run. This should be the full path or relative path.')
@argh.arg('files', nargs='*', help='List of input files and/or file glob patterns')
@argh.arg('--wd', help='Working directory.  Default is the current directory.')
@argh.arg('-le', '--log-extension', help='Extension for job log file')
@argh.arg('--args', help='Additional arguments to pass to command', nargs='*')
@argh.arg('--counter', nargs=2, type=int, help="Provides a way to supply an increasing integer argument to multiple"
                                               "jobs.  The two arguments are the first and last values.")
@argh.arg('--argfile', help='A file where each line is a set of arguments for the <command>.  Each line will be a separate submit.')
@argh.arg('--no-job-log', help='If specficied, then no job log file(s) is created.', action='store_true')
def submit(command, files, wd=os.getcwd(), log_extension='.sqs.log',
           port=9126, counter=None, args=None, argfile='', submit_delay=0.0, no_job_log=False):
    """Submits one or more jobs to the queue.

    Note that the relative or full path of the command should be given.  At present
     there are issues with jobs on the PATH environment variable not being found.


    Submitting Self Contained Scripts/Executables
    ..............................................

    If you have a script that requires no additional arguments, then use the following
    method:

    $ sqs submit myscript.bat
    $ sqs submit myscript.sh

    Submitting with Input Files
    ..............................................

    If you have an executable that you wish to run with one or more input files, you
    would do the following:

    $ sqs submit myprog.exe file01.inp
    $ sqs submit myprog.exe file*.inp some_other.inp

    In second case, the submit command would actually submit multiple jobs

    Supplying Additional Command Line Arguments
    ............................................

    Additional arguments may be passed to the script or executable using the --args facility.
    The --args argument here excepts any number of additional arguments.  Note that because
    of the way the command parser works, arguments that start with '-' or '--' will not work.
    They will be interpreted as arguments to the submit command.

    $ sqs submit myprog.exe file01.inp --args foo bar


    Using the Counter Argument
    ..............................................

    The *counter* argument is a way to create multiple jobs with each having an
    additional argument that is a sequentially increasing integer

    $ sqs submit myscript.bat --counter 10 20

    The above would submit 11 jobs - 'myscript.bat 10', 'myscript.bat 11', ..

    Additionally, if the counter needs to be part of a string passed into args,
    you can do the following, where {i} gets replaced by the counter value:

    $ sqs submit myscript.bat --args "foo{i}" bar --counter 1 2

    The above would submit 2 jobs - 'myscript.bat foo1 bar', 'myscript.bat foo2 bar'

    You can format the counter variable to pad zeros like this:

    $ sqs submit myscript.bat --args "foo{i:0>3}" bar --counter 1 2

    This will right justify counter i and pad it with zeros so that the result
    is 3 characters wide
    """
    import time

    pat = re.compile('\{i.*\}')

    if not os.path.exists(command):
        print('Command "{}" not found. Try specifying the full path to it.'.format(command))
        return
    else:
        if command[:2] == '.\\':
            command = command[2:]

    # Get the list of files
    if files:
        file_iter = []
        for f in files:
            found_files = glob(f)
            if not found_files:
                print('No files found for files entry {}'.format(f))
                return
            file_iter.extend(found_files)
        # if len(file_iter) == 0:
        #     print('No input files found even though one or more were specified: {}'.format(files))
        #     return
    else:
        file_iter = None

    loop = asyncio.get_event_loop()

    # If the user has specified the counter option, setup the count_iterator
    if counter is None:
        count_iterator = ['']
    else:
        count_iterator = range(counter[0], counter[1] + 1)

    # If the user specifies a counter, but no arguments, pass
    # the counter value as an argument to the user' command to run
    if args is None:
        if counter is None:
            args = []
        else:
            args = ['{i}']

    arg_string = ' '.join(args)

    for i in count_iterator:


        if pat.findall(arg_string):  # '{i}' in arg_string:
            # look for the counter in the arg_string
            # if we find it, format the string with the counter value
            arg_string_i =  arg_string.format(i=i)
        else:
            arg_string_i = arg_string

        #Finally we submit the job
        if file_iter:
            submissions = []
            for f in file_iter:
                if f[:2] == '.\\':
                    f = f[2:]

                if no_job_log:
                    log_file = ''
                else:
                    log_file = f"{f}-job{{job_id}}{log_extension}"

                submissions.append(
                    submit_job(
                        loop,
                        command=command,
                        filename=f,
                        working_dir=wd,
                        log_file=log_file,
                        args=arg_string_i,
                        port=port
                    ))
            for s in submissions:
                loop.run_until_complete(s)
                time.sleep(submit_delay)

        elif argfile:
            with open(argfile) as fid:
                args = fid.read().splitlines()
            submissions = []
            cmd = os.path.basename(command)
            for argset in args:
                if argset == "--stop--":
                    break

                if no_job_log:
                    log_file = ''
                else:
                    log_file = f"{cmd}-job{{job_id}}{log_extension}"

                submissions.append(
                        submit_job(
                                loop,
                                command=command,
                                filename='',
                                working_dir=wd,
                                log_file=log_file,
                                args=argset,
                                port=port
                                ))

            if submit_delay > 0:
                from .workers import adjust_workers
                nworkers = loop.run_until_complete(
                    adjust_workers(
                        loop,
                        worker_count=None,
                        port=port,
                        ip_address='127.0.0.1'
                    ))
            else:
                nworkers = 0


            for i, s in enumerate(submissions):
                if i > nworkers + 2:
                    submit_delay = 0.0
                time.sleep(submit_delay)
                loop.run_until_complete(s)
        else:

            cmd = os.path.basename(command)
            if no_job_log:
                log_file = ''
            else:
                log_file = f"{cmd}-job{{job_id}}{log_extension}"
            loop.run_until_complete(
                    submit_job(
                            loop,
                            command=command,
                            filename='',
                            working_dir=wd,
                            log_file=log_file,
                            args=arg_string_i,
                            port=port
                            ))

    loop.close()

