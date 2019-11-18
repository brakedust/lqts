from setuptools import setup, find_packages
import os
from os.path import join
import sys

python = None
python_possibilites = [
    join(sys.prefix, 'python'),
    join(sys.prefix, 'python.exe'),
    join(sys.prefix, 'bin', 'python'),
    join(sys.prefix, 'Scripts', 'python.exe')
]

for pypos in python_possibilites:
    if os.path.exists(pypos):
        python = pypos
        break

if python is None:
    print(f'Could not locate python in {sys.prefix}')
    sys.exit(1)


os.system(f'{python} version_maker.py')

from version import VERSION

packages = find_packages()

setup(
    name="lqts",
    packages=packages,
    version=VERSION,
    entry_points={
        "console_scripts": [
            "qsub = lqts.commands.qsub:qsub",
            "qsub-multi = lqts.commands.qsub:qsub_multi",
            "qsub-cmulti = lqts.commands.qsub:qsub_cmulti",
            "qsub-argfile = lqts.commands.qsub:qsub_argfile",
            "qstart = lqts.commands.qstart:qstart",
            "qstat = lqts.commands.qstat:qstat",
            "qclear = lqts.commands.qclear:qclear",
            "qdel = lqts.commands.qdel:qdel",
            "qworkers = lqts.commands.qworkers:qworkers",
            "qwait = lqts.commands.qwait:qwait",
            "qsummary = lqts.commands.qsummary:qsummary"
        ]
    },
    setup_requires=[
        "click",
        "requests",
        "pydantic<0.32.2",
        "fastapi",
        "ujson",
        "uvicorn",
        "psutil",
        "jinja2",
        "tqdm",
    ],
)

