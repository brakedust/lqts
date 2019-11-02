import os
import sys
import platform

from starlette.testclient import TestClient
import ujson

from lqts.server import app
from lqts.commands.qsub import qsub
from lqts.schema import Job, JobSpec, JobID

from tests.data import data_path

from unittest import mock


def log_info(text):
    print(text)


app.log.info = log_info


client = TestClient(app)
pwd = os.path.dirname(os.path.abspath(__file__))


def test_is_queued():

    job_spec = JobSpec(
        command=f'{data_path}/echo_it.bat "hello"',
        working_dir=pwd,
        log_file="test.log",
        priority=5,
        depends=[],
    )

    response = client.post("qsub", json=[job_spec.dict()])

    assert response.json() == ["1.0"]
    assert app.queue.queued_jobs[0].job_spec.command == job_spec.command

    assert app.queue.queued_jobs[0].job_spec.priority == 5
    assert app.queue.queued_jobs[0].job_spec.working_dir == pwd
    assert app.queue.queued_jobs[0].job_spec.log_file == "test.log"
    assert app.queue.queued_jobs[0].job_spec.depends == []

    assert app.queue.queued_jobs[0].submitted is not None


def test_job_depends():

    if platform.platform().lower().startswith("linux"):
        job_spec = JobSpec(
            command=f"bash {data_path}/sleepy.sh",
            working_dir=pwd,
            log_file="test.log",
            priority=5,
            depends=[],
        )
    else:
        job_spec = JobSpec(
            command=f"{data_path}/sleepy.bat",
            working_dir=pwd,
            log_file="test.log",
            priority=5,
            depends=[],
        )

    response = client.post("qsub", json=[job_spec.dict()])
    dependency = response.json()
    # dependency = ujson.loads(dependency)

    job_spec = JobSpec(
        depends=[JobID.parse_obj(dep) for dep in dependency],
        command=f'{data_path}/echo_it.bat "goodbye"',
        working_dir=pwd,
    )

    response = client.post("qsub", json=[job_spec.dict()])

    # counts = client.get('/qsummary').json()
    # sys.__stdout__.write('counts=' + str(counts))
    # import time
    # time.sleep(4)
    # assert set(
    #     app.queue.jobs[-1].job_spec.depends + app.queue.jobs[-1].completed_depends
    # ) == set(job_spec.depends)

    # while not counts['R'] + counts['Q'] > 0:
    #     print('sleeping')
    #     time.sleep(0.5)
    #     counts = client.get('/qsummary').json()
    #     print(counts)
    # client.post('/shutdown')


if __name__ == "__main__":
    # test_is_queued()
    test_job_depends()
