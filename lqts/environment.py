import os
import click
from functools import partial

os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""

click.option = partial(click.option, show_default=True)