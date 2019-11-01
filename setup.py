from setuptools import setup, find_packages


packages = find_packages()

setup(
    name="lqts",
    packages=packages,
    version=1.0,
    entry_points={
        "console_scripts": [
            "qsub = lqts.commands.qsub:qsub",
            "qsub-m = lqts.commands.qsub:qsub_m",
            "qsub-argfile = lqts.commands.qsub:qsub_argfile",
            "qstat = lqts.commands.qstat:qstat",
            "qclear = lqts.commands.qclear:qclear",
            "qdel = lqts.commands.qdel:qdel",
            "qworkers = lqts.commands.qworkers:qworkers",
            "qstart = lqts.commands.qstart:qstart",
        ]
    },
)

