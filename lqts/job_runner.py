import sys
import os
import subprocess
import time
from datetime import datetime, timedelta

from .schema import Job, JobID, JobStatus


def run_command(job: Job):
    """
    Runs an instance of aegir for the given filename

    Parameters
    ----------
    file_name

    Returns
    -------

    """

    if job.status == JobStatus.Deleted:
        return

    time.sleep(0.025)
    os.chdir(job.job_spec.working_dir)
    start = datetime.now()
    #        log.info(f'+Starting: {command} at {start.isoformat()}')

    job.status = JobStatus.Running
    job.started = start
    command = job.job_spec.command

    #    log.info('+Started: job {} completed at {}'.format(
    #            job['jobid'], job['started']))

    header = """
Executed with LQTS (the Lightweight Queueing System)
LQTS Version {}
-----------------------------------------------
Job ID:  {}
WorkDir: {}
Command: {}
Started: {}
-----------------------------------------------

""".format(
        "0.1.0",
        job.job_id,
        job.job_spec.working_dir,
        command,
        start.isoformat(),
        # end.isoformat(),
        # (end - start),
    )

    if job.job_spec.log_file:
        fid = open(job.job_spec.log_file, "w")
        fid.write(header)
    else:
        import io

        fid = io.StringIO(header)

    # output = ":)\n"
    p = None

    fid.write(
        "\n-----------------------------------------------\nSTDOUT\n-----------------------------------------------\n"
    )

    def get_output(p, stderr=False):

        if not stderr:
            line = p.stdout.read(1024 * 2)
        else:
            line = p.stderr.read()

        return line.decode().replace("\r", "").replace("\n\n", "\n")

    if sys.platform == "linux":
        import shlex

        # eol = "\n"
        command = shlex.split(job.job_spec.command.strip())

    else:
        # eol = "\r\n"
        command = command.strip()

    # print(command)
    try:
        p = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False
        )
        line = get_output(p)
        fid.write(line)
        while line:
            line = get_output(p)
            fid.write(line)
        serr = get_output(p, stderr=True)
        sys.stderr.write(serr)
        fid.write(
            "\n-----------------------------------------------\nSTDERR\n-----------------------------------------------\n"
        )
        fid.write(serr)
        job.status = JobStatus.Completed
    except FileNotFoundError:
        fid.write(
            f"\nERROR: Command not found.  Ensure the command is an executable file.\n"
        )
        fid.write(
            f"Make sure you give the full path to the file or that it is on your system path.\n\n"
        )
        job.status = JobStatus.Error

    end = datetime.now()
    time.sleep(0.001)

    job.completed = end
    # job.walltime = str(end - start)

    footer = """
-----------------------------------------------
Job Performance
-----------------------------------------------
Started: {}
Ended:   {}
Elapsed: {}
-----------------------------------------------
"""

    footer = footer.format(start.isoformat(), end.isoformat(), (end - start))
    fid.write(footer)

    fid.close()

    return job