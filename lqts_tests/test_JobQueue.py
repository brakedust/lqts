import os
from datetime import datetime
from itertools import cycle

import pytest

from lqts.core.schema import Job, JobID, JobQueue, JobSpec, JobStatus
from tests.data import data_path

hello = os.path.join(data_path, "echo_it.bat") + " hello"
goodbye = os.path.join(data_path, "echo_it.bat") + " goodbye"


def get_job_spec():
    js = JobSpec(command=hello, working_dir=".", priority=10)
    return js


def test_submit():

    q = JobQueue()

    assert len(q.queued_jobs) == 0
    js = get_job_spec()

    job_ids = q.submit([js])
    assert len(q.queued_jobs) == 1

    js_next = q.next_job()
    assert js_next.job_id == job_ids[0]


def test_priority():

    q = JobQueue()

    js1 = JobSpec(command=hello, working_dir=".", priority=10)
    js2 = JobSpec(command=goodbye, working_dir=".", priority=15)

    job1 = q.submit([js1, js2])

    exec_job_1 = q.next_job()
    q.on_job_started(exec_job_1.job_id)
    exec_job_2 = q.next_job()
    q.on_job_started(exec_job_2.job_id)

    assert exec_job_1.job_id == JobID(group=2, index=0)
    assert exec_job_2.job_id == JobID(group=1, index=0)


def test_prune():

    # DEFAULT_CONFIG.prune_job_limt = 10

    q = JobQueue()
    q.completed_limit = 10

    for i in range(15):
        js1 = JobSpec(command=hello, working_dir=".", priority=10)
        job1 = q.submit([js1])

    assert len(q.queued_jobs) == 15
    assert len(q.running_jobs) == 0
    assert len(q.completed_jobs) == 0

    for i in range(15):
        q.on_job_started(q.next_job().job_id)

    assert len(q.queued_jobs) == 0
    assert len(q.running_jobs) == 15
    assert len(q.completed_jobs) == 0

    for job_id, job in list(q.running_jobs.items()):
        q.on_job_finished(job_id)

    assert len(q.queued_jobs) == 0
    assert len(q.running_jobs) == 0
    assert len(q.completed_jobs) == 15

    q.prune()

    assert len(q.queued_jobs) == 0
    assert len(q.running_jobs) == 0
    assert len(q.completed_jobs) == 5


def test_job_sorting():

    jobs = [
        Job(
            job_spec=JobSpec(command="", working_dir="", priority=5),
            job_id=JobID(group=1, index=0),
        ),
        Job(
            job_spec=JobSpec(command="", working_dir="", priority=5),
            job_id=JobID(group=2, index=0),
        ),
        Job(
            job_spec=JobSpec(command="", working_dir="", priority=4),
            job_id=JobID(group=3, index=0),
        ),
        Job(
            job_spec=JobSpec(command="", working_dir="", priority=6),
            job_id=JobID(group=4, index=0),
        ),
        Job(
            job_spec=JobSpec(command="", working_dir="", priority=5),
            job_id=JobID(group=5, index=1),
        ),
        Job(
            job_spec=JobSpec(command="", working_dir="", priority=5),
            job_id=JobID(group=5, index=0),
        ),
    ]

    jobs2 = list(sorted(jobs))

    for j in jobs2:
        print(j)

    assert jobs2[0].job_id.group == 4
    assert jobs2[-1].job_id.group == 3


# if __name__ == "__main__":
# test_priority()
# test_prune()


def test_save_and_read_queue():

    # DEFAULT_CONFIG.prune_job_limt = 10

    q = JobQueue(start_manager_thread=False)
    q.completed_limit = 10
    for i in range(15):
        js1 = JobSpec(command=hello, working_dir=".", priority=10)
        job1 = q.submit([js1])

    assert len(q.queued_jobs) == 15
    assert len(q.running_jobs) == 0
    assert len(q.completed_jobs) == 0

    for i in range(10):
        q.on_job_started(q.next_job().job_id)

    assert len(q.queued_jobs) == 5
    assert len(q.running_jobs) == 10
    assert len(q.completed_jobs) == 0

    i = 0
    for job_id, job in list(q.running_jobs.items()):
        q.on_job_finished(job_id)
        i += 1
        if i == 5:
            break

    assert len(q.queued_jobs) == 5
    assert len(q.running_jobs) == 5
    assert len(q.completed_jobs) == 5

    q.save()

    q2 = JobQueue()
    q2.load()

    a, b = len(q.queued_jobs) + len(q.running_jobs), len(q2.queued_jobs)
    assert a == b
    # assert len(q.running_jobs) == len(q2.running_jobs)
    assert len(q.completed_jobs) == len(q2.completed_jobs)


if __name__ == "__main__":
    pytest.main()
