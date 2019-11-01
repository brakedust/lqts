import pytest

from datetime import datetime
from itertools import cycle

from lqts.schema import JobSpec, Job, JobID, JobQueue, JobStatus, DEFAULT_CONFIG


def get_job_spec():
    js = JobSpec(command="echo hello", working_dir="/tmp", priority=10)
    return js


def test_submit():

    q = JobQueue()

    assert len(q.queued_jobs) == 0
    js = get_job_spec()

    job = q.submit(get_job_spec())
    assert len(q.queued_jobs) == 1

    js_next = q.next_job()
    assert js_next.job_id == job.job_id


def test_priority():

    q = JobQueue()

    js1 = JobSpec(command="echo hello", working_dir="/tmp", priority=10)
    js2 = JobSpec(command="echo goodbye", working_dir="/tmp", priority=15)

    job1 = q.submit(js1)
    job2 = q.submit(js2)

    exec_job_1 = q.next_job()
    exec_job_2 = q.next_job()

    assert exec_job_1.job_id == JobID(group=2, index=0)
    assert exec_job_2.job_id == JobID(group=1, index=0)


def test_prune():

    DEFAULT_CONFIG.prune_job_limt = 10

    q = JobQueue()

    for i in range(15):
        js1 = JobSpec(command="echo hello", working_dir="/tmp", priority=10)
        job1 = q.submit(js1)

    assert len(q.queued_jobs) == 15
    assert len(q.running_jobs) == 0
    assert len(q.completed_jobs) == 0

    jobs = [q.next_job() for i in range(15)]

    assert len(q.queued_jobs) == 0
    assert len(q.running_jobs) == 15
    assert len(q.completed_jobs) == 0

    for j in jobs:
        j.completed = datetime.now()
        j.status = JobStatus.Completed
        q.on_job_finished(j.job_id)

    assert len(q.queued_jobs) == 0
    assert len(q.running_jobs) == 0
    assert len(q.completed_jobs) == 15

    q.prune()

    assert len(q.queued_jobs) == 0
    assert len(q.running_jobs) == 0
    assert len(q.completed_jobs) == 10
