# -*- coding: utf-8 -*-
"""
pluglib
=========

Handles plugin functionality

"""
import os
from glob import glob
from importlib import import_module


PACKAGE = __name__.split(".")[0]


class PluginManager:
    def __init__(self, name="plugins", plugin_path=None):

        self.name = name
        self.plugins = []
        if plugin_path:
            self.plugin_path = plugin_path
        else:
            self.plugin_path = os.path.abspath(os.path.dirname(__file__))
            self.plugin_path = os.path.join(self.plugin_path, "plugins")

    def register(self, func):
        """
        Registers a function as a command for the application
        This is typically used as a decorator.
        """

        self.plugins.append(func)

        return func

    def scan_plugins(self, plugin_path=None, clear_plugins=False):
        """
        Scans *plugin_path* for python files and imports them.
        If a python module uses the *register* function, then
        that function gets added to the list of available subcommands.
        """
        if clear_plugins:
            self.plugins.clear()

        if plugin_path is None:
            plugin_path = self.plugin_path

        for filename in glob(os.path.join(plugin_path, "*.py")):
            filename = os.path.split(filename)[-1]
            if filename == "__init__.py":
                continue
            modname = os.path.splitext(filename)[0]
            modname = "{0}.plugins.{1}".format(PACKAGE, modname)
            #            print(modname)
            import_module(modname)

        return self.plugins


plg_mgr = PluginManager()
