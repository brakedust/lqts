# -*- coding: utf-8 -*-
import asyncio
import json
import time
import datetime
import argh

from ..pluglib import plg_mgr


async def get_progress(loop, port=9126):

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

    return data


@plg_mgr.register
@argh.arg("-j", "--jobs", nargs="*", help="Job IDs to wait on")
@argh.arg(
    "-i",
    "--interval",
    type=int,
    help="Number of seconds to wait before checking the queue again",
)
@argh.arg(
    "--verbose",
    "-v",
    action="count",
    help="Give more feedback. -v for a little. -vv for more",
)
@argh.arg("--port", help="what port the server is running on")
def wait(jobs=None, interval=15, port=9126, verbose=0):
    """
    Blocks until the specified jobs have completed.  If no jobs are specified
    then 'wait' blocks until all jobs have completed.
    """
    still_running = True

    loop = asyncio.get_event_loop()
    while still_running:

        f = get_progress(loop, port)
        data = loop.run_until_complete(f)

        # data = get_status(port=port)
        data = {entry["job_id"]: entry for entry in data}

        if jobs:
            running = [data[j]["status"] in ("R", "Q") for j in jobs]
        else:
            running = [data[j]["status"] in ("R", "Q") for j in data]

        still_running = any(running)

        if still_running and verbose >= 2:
            print("Waiting on {} jobs".format(running.count(True)))

        if still_running:
            time.sleep(interval)

    loop.close()
    if verbose >= 1:
        print("Done waiting: {}".format(datetime.datetime.now().isoformat()))
