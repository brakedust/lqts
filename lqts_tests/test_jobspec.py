import pytest

from lqts.core.schema import JobID, JobSpec


def test_job_spec():

    js = JobSpec(command="test", working_dir="/tmp", priority=10)

    assert js.command == "test"
    assert js.working_dir == "/tmp"

    assert js.priority == 10

    assert js.log_file is None
