import sys
import os
import subprocess
import time
from datetime import datetime, timedelta

from .work_queue import Job, JobID, JobStatus

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
    os.chdir(job.spec.working_dir)
    start = datetime.now()
    #        log.info(f'+Starting: {command} at {start.isoformat()}')

    job.status = JobStatus.Running
    job.started = start
    command = job.spec.command

    #    log.info('+Started: job {} completed at {}'.format(
    #            job['jobid'], job['started']))

    header = """
Executed with SQS (the Simple Queueing System)
SQS Version {}
-----------------------------------------------
Job ID:  {}
WorkDir: {}
Command: {}
Started: {}
-----------------------------------------------

""".format(
        "LQTS VERSION",
        job.job_id,
        job.spec.working_dir,
        command,
        start.isoformat(),
        # end.isoformat(),
        # (end - start),
    )

    if job.spec.log_file:
        fid = open(job.spec.log_file, "w")
        fid.write(header)
    else:
        import io

        fid = io.StringIO(header)

    output = ":)\n"
    p = None

    fid.write(
        "\n-----------------------------------------------\nSTDOUT\n-----------------------------------------------\n"
    )

    def get_output(p, stderr=False):

        if not stderr:
            line = p.stdout.read(1024 * 2)
        else:
            line = p.stderr.read()

        return line.decode().replace('\r', '').replace('\n\n', '\n')

    if sys.platform == "linux":
        import shlex
        eol = "\n"
        command = shlex.split(job.spec.command.strip())

    else:
        eol = "\r\n"
        command = command.strip()

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

    end = datetime.now()
    time.sleep(0.025)
    job.status = JobStatus.Completed
    job.completed = end
    job.walltime = str(end - start)

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


def job_done(server, future):
    """
    Called when a job finishes.  This callback is added to each Future object
    in submit_job_handler.
    """
    job_done = future.result()

    for job, fut in server.jobs:
        if job["job_id"] == job_done["job_id"]:
            job.update(job_done)
            break