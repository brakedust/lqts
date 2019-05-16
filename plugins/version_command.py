
from ..pluglib import plg_mgr


@plg_mgr.register
def version():
    """
    Displays the program version and exits.
    """
    from sqs.version import VERSION
    print(VERSION)
