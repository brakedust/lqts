# -*- coding: utf-8 -*-
import sys
import argh
from .pluglib import plg_mgr


def main():
    parser = argh.ArghParser(fromfile_prefix_chars="%")
    plugins = plg_mgr.scan_plugins()

    if len(plugins) == 0:
        print("No commands defined")
        sys.exit(0)
    elif len(plugins) == 1:
        parser.set_default_command(plugins[0])
    else:
        parser.add_commands(plugins)

    parser.dispatch()
