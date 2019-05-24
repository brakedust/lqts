# -*- coding: utf-8 -*-

import asyncio
import json

import argh

from ..pluglib import plg_mgr

import lqts.environment


async def get_progress(
    loop, raw=False, long=False, status_filter=None, port=9126, summary=False
):

    from sqs import displaytable as dt

    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", port, loop=loop)
    except ConnectionRefusedError:
        print("Not able to communicate with the sqs server.  Is it running?")
        return

    data = {"type": "status"}

    message = json.dumps(data)

    writer.write(message.encode())
    writer.write_eof()

    data = await reader.read()

    writer.close()
    data = json.loads(data.decode())

    # filter jobs by status
    if status_filter:
        data = [d for d in data if d["status"] in status_filter]

    if raw:
        from pprint import pprint

        pprint(data)

    else:

        if not summary:
            if not long:
                td = dt.tablize(
                    data, include=["job_id", "command", "status", "started", "walltime"]
                )
            else:
                td = dt.tablize(data)

            t = dt.make_table(td, colsep="|", use_rowsep=False, maxwidth=60)
            print(t)

            print("")

        running = len([d for d in data if d["status"] == "R"])
        print("# of jobs running: {}".format(running))
        queued = len([d for d in data if d["status"] == "Q"])
        print("# of jobs queued:  {}".format(queued))


@plg_mgr.register
@argh.arg(
    "--raw",
    action="store_true",
    help="Display the raw json message returned by the server.",
)
@argh.arg(
    "--long", action="store_true", help="Display all columns returned from the server."
)
@argh.arg("-C", "-c", action="store_true", help="Show completed jobs only")
@argh.arg("-Q", "-q", action="store_true", help="Show queued jobs only")
@argh.arg("-R", "-r", action="store_true", help="Show running jobs only")
@argh.arg("-s", "--summarize", action="store_true", help="Show summary only")
def status(
    raw=False, long=False, C=False, Q=False, R=False, port=9126, summarize=False
):
    """Gets the status of submitted jobs. By default all jobs submitted since the
    server started are displayed.  The -c, -r, and -q options may be
    combined.

    Examples:
        $ sqs status        # display all jobs
        $ sqs status -c     # display only completed jobs
        $ sqs status -r -q  # display only jobs that are running or waiting in the queue
    """

    if any((C, Q, R)):
        status_filter = []
        if C:
            status_filter.append("C")
        if Q:
            status_filter.append("Q")
        if R:
            status_filter.append("R")
    else:
        status_filter = None

    loop = asyncio.get_event_loop()
    f = get_progress(loop, raw, long, status_filter, port, summarize)
    loop.run_until_complete(f)
    loop.close()
