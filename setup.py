from setuptools import setup, find_packages



packages = find_packages()

setup(
    name="lqts",
    packages=packages,
    version=1.0,
    entry_points={"console_scripts":[
        "qsub = lqts.qsub:qsub",
        "qstat = lqts.qstat:qstat"
    ]

    }
)





