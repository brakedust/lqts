import os
import subprocess
from pathlib import Path

import click

from lqts.core.config import config


@click.command("qstart")
@click.option(
    "--no-popout",
    is_flag=True,
    default=False,
    help=(
        "By default the server is started in a new cmd prompt using "
        "windows's 'start' mechanism. This flag causes the server to "
        "start in this terminal instance and block."
    ),
)
@click.option("--port", default=config.port, help="The port number of the server")
# @click.option("--ip_address", default=config.ip_address, help="The IP address of the server")
def qstart(no_popout=False, port=config.port):  # , ip_address=config.ip_address):
    """Starts the LQTS queue server"""
    import uvicorn

    os.environ["LQTS_PORT"] = str(port)

    uvicorn.run(app="lqts.main:app", port=str(port), log_level="warning")


if __name__ == "__main__":
    qstart()
