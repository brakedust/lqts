import subprocess

import click

from lqts.config import DEFAULT_CONFIG


@click.command("qstart")
@click.option("--port", type=int, default=DEFAULT_CONFIG.port)
def qstart(port=DEFAULT_CONFIG.port):

    args = ["start", "uvicorn", "--port", str(port), "--log-level", "warning", "lqts.server:app"]
    print(" ".join(args))
    subprocess.call(" ".join(args), shell=True)


if __name__ == "__main__":
    qstart()
