import os
import sys
import platform

from starlette.testclient import TestClient
import ujson

from lqts.server2 import app
from lqts.qsub import qsub
from lqts.schema import Job, JobSpec, JobID


from unittest import mock


def log_info(text):
    print(text)


app.log.info = log_info


client = TestClient(app)
pwd = os.path.dirname(os.path.abspath(__file__))


def test_is_queued():

    job_spec = JobSpec(
        command='echo "hello"',
        working_dir=pwd,
        log_file="test.log",
        priority=5,
        depends=[],
    )

    response = client.post("qsub", json=[job_spec.dict()])

    assert response.json() == ["1.0"]

    assert app.queue.jobs[0].job_spec.command == 'echo "hello"'
    assert app.queue.jobs[0].job_spec.priority == 5
    assert app.queue.jobs[0].job_spec.working_dir == pwd
    assert app.queue.jobs[0].job_spec.log_file == "test.log"
    assert app.queue.jobs[0].job_spec.depends == []

    assert app.queue.jobs[0].submitted is not None


def test_job_depends():

    if platform.platform == "linux":
        job_spec = JobSpec(
            command=f"bash {pwd}/sleepy.sh",
            working_dir=pwd,
            log_file="test.log",
            priority=5,
            depends=[],
        )
    else:
        job_spec = JobSpec(
            command=f"{pwd}\\sleepy.bat",
            working_dir=pwd,
            log_file="test.log",
            priority=5,
            depends=[],
        )

    response = client.post("qsub", json=[job_spec.dict()])
    dependency = response.json()
    # dependency = ujson.loads(dependency)

    job_spec.depends = [JobID.parse(dep) for dep in dependency]
    job_spec.command = 'echo "goodbye"'
    response = client.post("qsub", json=[job_spec.dict()])

    # counts = client.get('/qsummary').json()
    # sys.__stdout__.write('counts=' + str(counts))
    # import time
    # time.sleep(4)
    assert set(
        app.queue.jobs[-1].job_spec.depends + app.queue.jobs[-1].completed_depends
    ) == set(job_spec.depends)

    # while not counts['R'] + counts['Q'] > 0:
    #     print('sleeping')
    #     time.sleep(0.5)
    #     counts = client.get('/qsummary').json()
    #     print(counts)
    # client.post('/shutdown')

