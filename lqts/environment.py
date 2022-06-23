"""
This module ensures the proxy definitions are cleared out.
Other wise the requests library tries to use the proxy to
reach local host and we get permission denied type errors
"""
import os
import click
from functools import partial, wraps

os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""

click.option = wraps(click.option)(partial(click.option, show_default=True))
