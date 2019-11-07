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
    q.on_job_started(exec_job_1.job_id)
    exec_job_2 = q.next_job()
    q.on_job_started(exec_job_2.job_id)

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
        Job(job_spec=JobSpec(command='', working_dir='', priority=5), job_id=JobID(group=1,index=0)),
        Job(job_spec=JobSpec(command='', working_dir='', priority=5), job_id=JobID(group=2,index=0)),
        Job(job_spec=JobSpec(command='', working_dir='', priority=4), job_id=JobID(group=3,index=0)),
        Job(job_spec=JobSpec(command='', working_dir='', priority=6), job_id=JobID(group=4,index=0)),
        Job(job_spec=JobSpec(command='', working_dir='', priority=5), job_id=JobID(group=5,index=1)),
        Job(job_spec=JobSpec(command='', working_dir='', priority=5), job_id=JobID(group=5,index=0)),
    ]

    jobs2 = list(sorted(jobs))

    for j in jobs2:
        print(j)

    assert jobs2[0].job_id.group == 4
    assert jobs2[-1].job_id.group == 3

# if __name__ == "__main__":
    # test_priority()
    # test_prune()