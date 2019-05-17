# -*- coding: utf-8 -*-
import os
import argh
from glob import glob
import asyncio
import json
#import sys
from ..pluglib import plg_mgr
from pprint import pprint


async def remove_job(
        loop, 
        job_id,        
        port=9126,
        ip_address='127.0.0.1'):
    

    reader, writer = await asyncio.open_connection(
        ip_address,
        port,
        loop=loop)

    data = {'type': 'remove',
            'job_id': job_id}
    
    pprint(data)
    
    message = json.dumps(data)
        
    writer.write(message.encode())
    writer.write_eof()
    
    data = await reader.read()
    job_id2 = int(data.decode())
    writer.close()
    print('\nRemoving Job ID: {}'.format(job_id2))
    
    
@plg_mgr.register
@argh.arg('first_id', type=int, help='Job ID to remove')
@argh.arg('--last_id', '-l', type=int, help='Last ID to remove.  Specifying this will cause a '
                                       'range of jobs to be removed')
def remove(first_id, last_id=None, port=9126, ip_address='127.0.0.1'):
    """Removes one or more jobs from the queue.

    Examples:
        $ sqs remove 10               # remove job 10 from the Q
        $ sqs remove 10 --last-id 20  # removes jobs 10-20 (inclusive) from the Q
        $ sqs remove 10 -l 20         # removes jobs 10-20 (inclusive) from the Q
    """
        
    loop = asyncio.get_event_loop()

    if last_id is None:
        loop.run_until_complete(
                remove_job(
                        loop,
                        first_id,
                        port=port,
                        ip_address=ip_address
                        ))

    elif last_id is not None:

        for job_id in range(first_id, last_id + 1):
            loop.run_until_complete(
                remove_job(
                    loop,
                    job_id,
                    port=port,
                    ip_address=ip_address
                ))

    loop.close()


