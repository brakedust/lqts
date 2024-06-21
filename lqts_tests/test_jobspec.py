from pathlib import Path

import pytest

from lqts.core.schema import JobID, JobSpec


def test_job_spec1():

    js = JobSpec(command="test", working_dir="/tmp", priority=10)

    assert js.command == "test"
    assert js.working_dir == "/tmp"

    assert js.priority == 10

    assert js.log_file is None


def test_job_spec2():
    js = JobSpec(
        command="test",
        log_file=None,
        working_dir="/tmp",
        priority=15,
        cores=2,
        depends=[JobID(group=1, index=2)],
        walltime=0,
    )

    js2 = JobSpec.model_validate(js)

    print(js2.model_dump_json(indent=4))


def test_job_spec3():
    js = JobSpec(
        command="test",
        log_file=None,
        working_dir="/tmp",
        priority=15,
        cores=2,
        depends=[JobID(group=1, index=2)],
        walltime="10:00:00",
    )
    JobSpec.model_validate(js)

    txt = js.model_dump_json(indent=4)
    print(txt)
    JobSpec.model_validate_json(txt)


if __name__ == "__main__":
    test_job_spec1()
    test_job_spec2()
    test_job_spec3()
