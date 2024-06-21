import pytest

from lqts.core.schema import JobID


def test_job_id():

    jid = JobID()

    assert jid.group == 1
    assert jid.index == 0


def test_job_id_2():

    jid1 = JobID.parse_obj("2.4")
    assert jid1.group == 2
    assert jid1.index == 4


if __name__ == "__main__":
    test_job_id()
    test_job_id_2()
