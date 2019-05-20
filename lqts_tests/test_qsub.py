import os
import sys

from starlette.testclient import TestClient

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
        log_file='test.log',
        priority=5,
        depend_on=None
    )

    response = client.post('qsub', json=job_spec.dict())    
    
    assert response.text == '"1.0"'
    
    assert app.queue.jobs[0].spec.command == 'echo "hello"'
    assert app.queue.jobs[0].spec.priority == 5
    assert app.queue.jobs[0].spec.working_dir == pwd
    assert app.queue.jobs[0].spec.log_file == 'test.log'
    assert app.queue.jobs[0].spec.depend_on == None

    assert app.queue.jobs[0].submitted is not None


def test_is_depend_on():

    job_spec = JobSpec(
        command=f'bash {pwd}/sleepy.sh',
        working_dir=pwd,
        log_file='test.log',
        priority=5,
        depend_on=None
    )

    response = client.post('qsub', json=job_spec.dict())    
    dependency = response.text.strip('"')

    job_spec.depend_on = JobID.parse(dependency)
    job_spec.command = 'echo "goodbye"'
    response = client.post('qsub', json=job_spec.dict())

    # counts = client.get('/qsummary').json()
    # sys.__stdout__.write('counts=' + str(counts))
    # import time
    # time.sleep(4)
    assert app.queue.jobs[-1].spec.depend_on == job_spec.depend_on
    
    # while not counts['R'] + counts['Q'] > 0:
    #     print('sleeping')
    #     time.sleep(0.5)    
    #     counts = client.get('/qsummary').json()
    #     print(counts)
    # client.post('/shutdown')

