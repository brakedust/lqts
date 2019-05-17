import enum
from datetime import datetime, timedelta
import itertools
from os.path import join, expanduser
from multiprocessing import cpu_count
from pydantic import BaseModel
from typing import List, Deque
 

class JobID(BaseModel):

    group: int = 1
    index: int = 0

    def __str__(self):
        return f"{self.group}.{self.index}"

    @staticmethod
    def parse(value):
        job_id = JobID()
        if isinstance(value, JobID):
            return value
        elif isinstance(value, str):
            if "." not in value:
                job_id.Group = int(value)
            else:
                job_id.Group, job_id.value = map(int, value.split("."))
        elif isinstance(value, int):
            job_id.Group = value
        else:
            raise ValueError(f"JobID.parse excepts types int, JobID, or str. You provided {value} of type {type(value)}.")
        return job_id


class JobStatus(enum.Enum):

    Initialized = 'I'
    Queued = 'Q'
    Running = 'R'
    Completed = 'C'
    Deleted = 'D'


class JobSpec(BaseModel):

    command: str 
    working_dir: str
    log_file: str = None


class Job(BaseModel):

    job_id: JobID = JobID(group=1, index=0)
    status: JobStatus = JobStatus.Initialized

    submitted: datetime = None
    started: datetime = None
    completed: datetime = None

    walltime: timedelta = None
    spec: JobSpec = None

    @property
    def elapsed(self):
        return self.completed - self.started

    def _should_prune(self):
        now = datetime.now()
        if JobStatus.Completed and now - self.completed > timedelta(seconds=4*3600):
            return True
        elif self.status == JobStatus.Deleted:
            return True
        else:
            return False

class JobQueue(BaseModel):

    jobs: List[Job] = []

    current_index: int = 1

    def prune(self):

        self.pruned_jobs = [job for job in self.jobs if job._should_prune()]
        self.jobs = [job for job in self.jobs if not job._should_prune()]

    def submit(self, job_spec: JobSpec):
        
        job = Job(job_id=JobID(group=self.current_index), spec = job_spec)
        job.status = JobStatus.Queued
        job.submitted = datetime.now()
        self.jobs.append(job)
        self.current_index += 1
        return job.job_id

class Configuration(BaseModel):

    ip_address: str = "127.0.0.1"
    port: int = 9126
    last_job_id: JobID = JobID(group=0, index=0)
    log_file: str = join(expanduser("~"), "lqts.log")
    config_file: str = join(expanduser("~"), "lqts.config")
    nworkers:int  = max(cpu_count() - 2, 1)