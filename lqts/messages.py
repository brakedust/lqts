# -*- coding: utf-8 -*-
"""
messages Module
================

The messages module contains the handlers for dealing with the messages that have been
received by the server.  Each message handler is registered with the MessageDispatcher
and the MessageDispatcher is responsible for calling the correct handler.

"""
import sys
import datetime
import json
import os
import subprocess
import time
from functools import partial

from dateutil.parser import parse

from sqs.version import VERSION


# VERSION = GitVersionInfo.get().setuptools_version


class MessageDispatcher:
    """Handles registering functions that handle different types
    of messages received by the server.

    Registration is done using a decorator.  For example, to register
    a function that handles status requests:

    .. code:: python
        @MessageDispatcher.register_message_handler('status')
        async def status_request_handler(server, message, reader, writer):
            pass

    The *get_handler* method will determine the correct handler to call
    by looking at the 'type' field of the message dict and looking for the
    handler that has been registered to for that type.

    """

    handlers = {}

    def __init__(self):

        pass

    @classmethod
    def register_message_handler(cls, message_type):
        """
        Registers a function to that will handle functions of a certain type.


        Parameters
        ----------
        message_type
            type string from the message

        Returns
        -------
        function
            the unmodified function
        """

        def inner_register(func):

            cls.handlers[message_type] = func

            return func

        return inner_register

    @classmethod
    def get_handler(cls, message):
        """Examines the *type* field of the message and determines
        the proper handler to call

        Parameters
        -----------
        message: dict
            decoded json message received from a client
        """
        try:
            return cls.handlers[message["type"]]
        except KeyError:
            return _unknown_request_handler


async def _unknown_request_handler(server, message, reader, writer):
    server.log.error("Unkown message type passed to server\n{}".format(message))
    writer.write("Unkown message type passed to server\n{}".format(message).encode())
    writer.write_eof()
    await writer.drain()
    writer.close()


@MessageDispatcher.register_message_handler("status")
async def status_request_handler(server, message, reader, writer):
    """
    Handles responding to request for the job queue status

    Parameters
    ----------
    server: sqs.server.Server
    message: dict
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    """
    server.log.debug("status request received")

    status = [job for job, fut in server.jobs]

    for job in status:
        if job["status"] == "R":  # '!= '' and job['completed'] == '':
            job["walltime"] = str(datetime.datetime.now() - parse(job["started"]))

    status_str = json.dumps(status)

    writer.write(status_str.encode())
    writer.write_eof()
    await writer.drain()
    writer.close()


@MessageDispatcher.register_message_handler("submit")
async def submit_job_handler(server, job_spec, reader, writer):
    """
    Handles submission to the job queue. Jobs are called using a process
    pool.  Each job was a callback attached that will be called when
    it is complete.  This callback is the *job_done* function.

    Parameters
    ----------
    server: sqs.server.Server
    message: dict
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    """
    # server.log.info('job received')
    server.job_id += 1
    job_spec["job_id"] = server.job_id
    server.log.info("job received: ID = {}".format(job_spec["job_id"]))
    job_spec["submitted"] = datetime.datetime.now().isoformat()
    job_spec["status"] = "Q"
    job_spec["completed"] = ""
    job_spec["walltime"] = ""
    job_spec["started"] = ""

    if "job_id" in job_spec["log_file"]:
        job_spec["log_file"] = job_spec["log_file"].format(job_id=job_spec["job_id"])

    func = partial(run_command, job_spec)
    future = server.pool.submit(func, job_id=job_spec["job_id"])
    server.jobs.append((job_spec, future))

    job_done_callback = partial(job_done, server)
    future.add_done_callback(job_done_callback)

    server.log.debug("done with job submission")

    writer.write(str(job_spec["job_id"]).encode())
    await writer.drain()
    writer.close()


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


@MessageDispatcher.register_message_handler("shutdown")
async def shutdown(server, message, reader, writer):
    """
    Shuts down the server
    """
    writer.write("Shutting down server".encode())
    writer.write_eof()
    await writer.drain()
    writer.close()

    # raise SQSShutdownException()
    raise KeyboardInterrupt()
    #

    # # time.sleep(2)
    # # sys.exit()
    # # Find all running tasks:
    # pending = asyncio.Task.all_tasks()
    #
    # # Run loop until tasks done:
    # server.event_loop.run_until_complete(asyncio.gather(*pending))


@MessageDispatcher.register_message_handler("remove")
async def remove_job(server, job_spec, reader, writer):
    """
    Removes the specified job from the queue.  If the job
    is currently running it is killed.

    Parameters
    ----------
    server
    job_spec
    reader
    writer

    Returns
    -------

    """
    for job, fut in server.jobs:
        if job["job_id"] == job_spec["job_id"]:
            server.pool.kill_job(job_spec["job_id"])
            server.log.info("killed job {}".format(job_spec["job_id"]))
            writer.write(str(job_spec["job_id"]).encode())
            job["status"] = "D"
            job["walltime"] = "-"
            break

    writer.write_eof()
    await writer.drain()
    writer.close()


def run_command(job: dict):
    """
    Runs an instance of aegir for the given filename

    Parameters
    ----------
    file_name

    Returns
    -------

    """

    if job["status"] == "D":
        return

    time.sleep(0.025)
    os.chdir(job["working_dir"])
    start = datetime.datetime.now()
    #        log.info(f'+Starting: {command} at {start.isoformat()}')

    job["status"] = "R"
    job["started"] = start.isoformat()
    command = job["command"]

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
        VERSION,
        job["job_id"],
        job["working_dir"],
        command,
        start.isoformat(),
        # end.isoformat(),
        # (end - start),
    )

    if job["log_file"]:
        fid = open(job["log_file"], "w")
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
        command = shlex.split(job["command"].strip())

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

    end = datetime.datetime.now()
    time.sleep(0.025)
    job["status"] = "C"
    job["completed"] = end.isoformat()
    job["walltime"] = str(end - start)

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


@MessageDispatcher.register_message_handler("worker-count")
async def adjust_worker_count(server, message, reader, writer):

    if "count" in message and message["count"] is not None:
        server.log.info(
            "Setting maximum number of workers to {}".format(message["count"])
        )
        server.pool.resize(int(message["count"]))

    writer.write("{}".format(server.pool._max_workers).encode())
    writer.write_eof()
    await writer.drain()
    writer.close()

