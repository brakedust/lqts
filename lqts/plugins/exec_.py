# -*- coding: utf-8 -*-
import os
import subprocess

from ..pluglib import plg_mgr





@plg_mgr.register
def exec(log_file):
    """Executes the command in a SQS log file.  This is useful for debugging why
    a job didn't run.  This command will read the log file, move into the job's
    working directory and run the specified command.

    Examples:
        $sqs submit some.exe
        # wait for the job to complete

        $ sqs exec some.exe-job1.sqs.log
    """

    workdir = None
    command = None

    with open(log_file) as fid:
        for line in fid:
            if line.startswith('WorkDir:'):
                workdir = line.partition(':')[-1].strip()
                print('WorkDir:' + workdir)
            elif line.startswith('Command:'):
                command = line.partition(':')[-1].strip()
                print("Command:" + command)

            if command is not None and workdir is not None:
                break

    os.chdir(workdir)
    subprocess.call(command)