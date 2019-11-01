import subprocess

import click

from lqts.schema import DEFAULT_CONFIG


@click.command("qstart")
@click.option("--port", type=int, default=DEFAULT_CONFIG.port)
def qstart(port=DEFAULT_CONFIG.port):

    args = ["uvicorn"]
    # if port is not None:
    args.extend(["--port", str(port)])
    args.append("lqts.server:app")
    print(args)
    subprocess.call(" ".join(args), shell=True)


if __name__ == "__main__":
    qstart()
