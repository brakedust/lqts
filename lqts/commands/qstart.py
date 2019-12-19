from pathlib import Path
import subprocess

import click

import lqts.environment
from lqts.config import Configuration

if Path(".env").exists():
    config = Configuration.load_env_file(".env")
else:
    config = Configuration()


@click.command("qstart")
@click.option("--no-popout", is_flag=True, default=False, help="By default the server is started in a new cmd prompt using "
    "windows's 'start' mechanism. This flag causes the server to start in this terminal instance and block.")
@click.option("--port", default=config.port, help="The port number of the server")
@click.option("--ip_address", default=config.ip_address, help="The IP address of the server")
def qstart(no_popout=False, port=config.port, ip_address = config.ip_address):
    """Starts the LQTS queue server"""
    if no_popout:
        args = ["uvicorn", "--port", str(port), "--log-level", "warning", "lqts.server:app"]
    else:
        args = ["start", "uvicorn", "--port", str(port), "--log-level", "warning", "lqts.server:app"]
    print(" ".join(args))
    subprocess.call(" ".join(args), shell=True)


if __name__ == "__main__":
    qstart()
