"""
Logging has some weird behavior when using uvicorn.

This is a simple implementation of logging that is similar-ish in behavior
to a subset of the python's built in logging module

By default a logger has a console handler.  You can add a FileHandler
yourself or pass a filename to the getLogger function or the
init function for a Logger instance.

To get a logger:

.. code:: python
    >>> from simple_logging import getLogger, Level
    >>> logger = getLogger('mylogger', Level.INFO)
    >>> logger.info('Hello!')
    2019-11-14T16:28:23.142606 | INFO | Hello!

    >>> logger2 = sl.getLogger('mylogger2', filename='log.txt')
    >>> logger2.handlers
    {'console': <lqts.simple_logging.ConsoleHandler object at 0x0000021DBE0C76A0>,
     'file': <lqts.simple_logging.FileHandler object at 0x0000021DBE0C7828>}
    >>> logger2.error('Oh no')
    2019-11-14T16:30:46.196629 | ERROR | Oh no
    >>> # Look at the log file
    >>> import Path
    >>> Path('log.txt').read_text()
    2019-11-14T16:30:46.196629 | ERROR | Oh no

"""

from typing import Union
import logging
from datetime import datetime
from enum import IntEnum
from pathlib import Path
import traceback


class Level(IntEnum):
    SILENT = 100
    CRITICAL = 50
    ERROR = 40
    WARNING = 30
    INFO = 20
    DEBUG = 10
    NOTSET = 0


class Logger:

    _instances = {}

    def __init__(self, name='default', level=Level.INFO, filename=None):

        self.level = level
        self.name = name

        self._instances[name] = self

        self.handlers = {'console': ConsoleHandler(level=level)}

        if filename:
            self.handlers['file'] = FileHandler(level=Level.WARNING, filename=filename)

    def log(self, level: Union[Level, int], message: str):

        for handler in self.handlers.values():
            handler.log(level, message)

    def info(self, message):
        self.log(Level.INFO, message)

    def debug(self, message):
        self.log(Level.DEBUG, message)

    def error(self, message):
        self.log(Level.ERROR, message)

    def _log_exception(self, level: Union[Level, int], message: str):
        for handler in self.handlers.values():
            handler.log_exception(level, message)

    def exception(self, message):
        self._log_exception(level, message)


class ConsoleHandler:

    def __init__(self, level: Level):
        self.level = level

    def log(self, level: Union[Level, int], message: str):
        if level >= self.level:
            print(f"{datetime.now().isoformat()} | {level.name} | {message}")

    def log_exception(self, level: Union[Level, int], message: str):
        if level >= self.level:
            print(f"{datetime.now().isoformat()} | {level.name} | {message}")
            print(traceback.format_exc())

class FileHandler:

    def __init__(self, level: Level, filename: Union[str, Path]):
        self.level = level
        self.filename = filename
        self.fid = open(filename, 'a')

    def log(self, level: Union[Level, int], message: str):
        if level >= self.level:
            self.fid.write(f"{datetime.now().isoformat()} | {level.name} | {message}\n")

    def log_exception(self, level: Union[Level, int], message: str):
        if level >= self.level:
            self.fid.write(f"{datetime.now().isoformat()} | {level.name} | {message}\n")
            self.fid.write(traceback.format_exc() + '\n')



def getLogger(name, level=Level.INFO, filename=None):

    if name in Logger._instances:
        return Logger._instances[name]
    else:
        logger = Logger(name=name, level=level, filename=filename)
        return logger