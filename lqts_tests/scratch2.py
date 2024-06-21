from pathlib import Path

import click


@click.command("mycommand")
@click.argument("filepattern", nargs=1, type=str)
def mycommand(filepattern):
    print(filepattern)
    print(list(Path(".").glob(filepattern)))


if __name__ == "__main__":
    mycommand(windows_expand_args=False)
