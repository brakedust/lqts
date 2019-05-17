"""
start_server Module
===================

Provides the command start-server, which starts the SQS server.
"""
from os.path import join, expanduser
from multiprocessing import cpu_count

import argh

from ..pluglib import plg_mgr
from ..server import SQServer


@plg_mgr.register
@argh.arg('-n', '--nworkers', type=int, help='Number of worker threads to use.'
          ' Default is number of cpus minus 2')
@argh.arg('-p', '--port', type=int, help='Network port to use')
#@argh.arg('-ip', help='IP address of server.  Defaults to localhost.')
def start_server(nworkers=cpu_count()-2,
                 port=9126,  # ip='127.0.0.1',
                 log_file=join(expanduser('~'), 'sqs.log'),
                 config_file=join(expanduser('~'), 'sqs.config'),
                 feed_delay=0.0,
                 debug=False):
    """Starts the sqs server so that it can accept and execute jobs.
    The server runs on local host.

    The number of workers can later be dynamically adjusted using the **sqs set-workers**
    command.
    """

    ip_address = '127.0.0.1'

    sqs_server = SQServer(
        port=port,
        ip_address=ip_address,
        nworkers=nworkers,
        log_file=log_file,
        config_file=config_file,
        feed_delay=feed_delay,
        debug=debug)

    sqs_server.run()
