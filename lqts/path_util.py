import os
import sys
from pathlib import Path

path_sep = ";" if sys.platform == "win32" else ":"


def find_file(filename, wd=None, search_path=True):

    filename = Path(filename)

    if filename.is_absolute():
        return filename

    if wd is None:
        wd = os.getcwd()

    path_list = [wd] + os.environ["PATH"].split(path_sep)

    for d in path_list:
        test_file = (Path(d) / filename).absolute()
        if test_file.exists():
            return test_file


def encode_path(p: str | Path):
    """
    Replaces backslashes in paths with forward slashes
    """
    if isinstance(p, Path):
        p = str(p)

    return p.replace("\\", "/")
