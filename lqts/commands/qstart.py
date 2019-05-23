import subprocess

import click

from lqts.schema import DEFAULT_CONFIG


@click.command("qstart")
@click.option("--port", type=int, default=DEFAULT_CONFIG.port)
def qstart(port):

    args = ["uvicorn", "lqts.server:app"]
    if port is not None:
        args.extend(["--port", str(port)])

    subprocess.call(args, shell=True)


if __name__ == "__main__":
    qstart()
