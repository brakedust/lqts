import enum
from restable import Restable, Field
from restable.fields import DateTimeField, TimeDeltaField
from restable.collections import TypedList, TypedListFactory
from datetime import datetime, timedelta
import itertools
from os.path import join, expanduser
from multiprocessing import cpu_count


class JobID(Restable):

    Group: int = Field()
    Index: int = Field()

    def __str__(self):
        return f"{self.Group}.{self.Index}"

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

    Created = 0
    Queued = 1
    Running = 2
    Completed = 3
    Deleted = 4


class Job(Restable):

    job_id: JobID = Field(JobID, converter=JobID.parse)
    status: JobStatus = Field(default=JobStatus.Created)

    submitted: datetime = DateTimeField()
    started: datetime = DateTimeField()
    completed: datetime = DateTimeField()

    walltime: timedelta = TimeDeltaField()

    command: str = Field()
    logfile: str = Field()
    working_dir: str = Field()

    @property
    def elapsed(self):
        return self.completed - self.started

    def _should_prune(self):
        return self.status in (JobStatus.Completed, JobStatus.Deleted)


class JobQueue(Restable):

    jobs: TypedList = TypedListFactory[Job]()

    current_index: int = Field(default=1)

    def prune(self):

        self.pruned_jobs = [job for job in self.jobs if job._should_prune()]
        self.jobs = [job for job in self.jobs if not job._should_prune()]

    def submit(self, job):
        job.job_id = self.current_index
        self.jobs.append(job)
        self.current_index += 1


class Configuration(Restable):

    ip_address: str = Field("127.0.0.1")
    port: int = Field(9126)
    last_job_id: JobID = "0.0"
    log_file: str = Field(join(expanduser("~"), "sqs.log"))
    config_file: str = Field(join(expanduser("~"), "sqs.config"))
    nworkers:int  = Field(max(cpu_count() - 2, 1))