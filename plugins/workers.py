# -*- coding: utf-8 -*-
import os
import argh
from glob import glob
import asyncio
import json
# import sys
from ..pluglib import plg_mgr
from pprint import pprint


async def adjust_workers(
        loop,
        worker_count=None,
        port=9126,
        ip_address='127.0.0.1'):


    reader, writer = await asyncio.open_connection(
        ip_address,
        port,
        loop=loop)

    data = {'type': 'worker-count',
            'count': worker_count}

    # pprint(data)

    message = json.dumps(data)

    writer.write(message.encode())
    writer.write_eof()

    data = await reader.read()
    nworkers = int(data.decode())
    writer.close()
    return nworkers


@plg_mgr.register
def get_workers(port=9126, ip_address='127.0.0.1'):
    """Gets the number of worker processes used by the server

    Examples:
        $ sqs get-workers
    """

    loop = asyncio.get_event_loop()


    nworkers = loop.run_until_complete(
        adjust_workers(
            loop,
            port=port,
            ip_address=ip_address
        ))

    print('\nNumber of workers: {}'.format(nworkers))
    loop.close()


@plg_mgr.register
def set_workers(n_workers, port=9126, ip_address='127.0.0.1'):
    """Sets the number of worker processes used by the server

    Example:
        $ sqs set-workers 6
    """

    loop = asyncio.get_event_loop()

    loop.run_until_complete(
        adjust_workers(
            loop,
            worker_count=n_workers,
            port=port,
            ip_address=ip_address
        ))

    loop.close()