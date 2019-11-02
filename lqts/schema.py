import enum
from datetime import datetime, timedelta
import itertools
from os.path import join, expanduser
from multiprocessing import cpu_count
import concurrent.futures as cf
from pydantic import BaseModel, BaseSettings
from typing import List, Deque, Union, Dict, Any
from queue import PriorityQueue
from uuid import uuid4


class JobID(BaseModel):

    group: int = 1
    index: int = 0

    # @validator('index', pre=True, always=True)
    # def set_ts_now(cls, v):
    #     return v or datetime.now()

    def __hash__(self):
        return hash(str(self))

    def __str__(self):
        return f"{self.group}.{self.index}"

    # def __eq__(self, other):
    # return (self.group == other.group) and (self.index == other.index)

    @staticmethod
    def parse_obj(value):

        if isinstance(value, JobID):
            return value
        elif isinstance(value, str):
            job_id = JobID()
            if "." not in value:
                job_id.group = int(value)
            else:
                g, i = value.split(".")
                job_id.group = int(g)
                if i in (None, "*"):
                    job_id.index = None
                else:
                    job_id.index = int(i)
            return job_id
        elif isinstance(value, int):
            job_id = JobID()
            job_id.group = value
            job_id.index = 0
            return job_id
        else:
            return super().parse_obj(value)


class JobStatus(enum.Enum):

    Initialized = "I"
    Queued = "Q"
    Running = "R"
    Completed = "C"
    Deleted = "D"


class JobSpec(BaseModel):

    command: str
    working_dir: str
    log_file: str = None
    priority: int = 10
    ncores: int = 1
    depends: List[JobID] = None


class Job(BaseModel):

    job_id: JobID = JobID(group=1, index=0)
    status: JobStatus = JobStatus.Initialized

    submitted: datetime = None
    started: datetime = None
    completed: datetime = None

    # walltime: timedelta = None
    job_spec: JobSpec = None

    completed_depends: List[JobID] = []

    def __gt__(self, other: "Job"):
        return self.job_spec.priority > other.job_spec.priority

    def __eq__(self, other: "Job"):
        return self.job_spec.priority == other.job_spec.priority

    @property
    def can_run(self) -> bool:
        # self.job_spec.depends
        return len(self.job_spec.depends) == 0

    @property
    def walltime(self) -> timedelta:

        if self.completed is not None:
            return self.completed - self.started
        elif self.started is not None:
            return datetime.now() - self.started
        else:
            return timedelta(0)

    def _should_prune(self) -> bool:
        now = datetime.now()
        if JobStatus.Completed:
            if now - self.completed > timedelta(seconds=2 * 3600):
                return True
            else:
                return False
        elif self.status == JobStatus.Deleted:
            return True
        else:
            return False

    def is_done(self) -> bool:
        return self.status in (JobStatus.Completed, JobStatus.Deleted)

    def as_table_row(self) -> list:

        return [
            self.job_id,
            self.status.value,
            self.job_spec.command,
            self.walltime,
            self.job_spec.working_dir,
            "{} / {}".format(
                ",".join(str(d) for d in self.job_spec.depends)
                if self.job_spec.depends
                else "-",
                ",".join(str(d) for d in self.completed_depends)
                if self.completed_depends
                else "-",
            ),
        ]


# class PriorityQueueThing(PriorityQueue):
#     @classmethod
#     def __get_validators__(cls):
#         yield cls.validate

#     @classmethod
#     def validate(cls, v):
#         if not isinstance(v, PriorityQueue):
#             raise ValueError(
#                 f"PriorityQueuething: PriorityQueue expected not {type(v)}"
#             )
#         return v


class JobQueue(BaseModel):

    queued_jobs: list = []

    running_jobs: Dict[JobID, Job] = {}

    completed_jobs: List[Job] = []
    pruned_jobs: List[Job] = []

    current_group: int = 1

    def get_job_group(self, group_id: int) -> List[Job]:

        return [job for job in self.jobs if job.job_id.group == group_id]

    def submit(self, job_spec: JobSpec, job_id=None) -> Job:

        if job_id is None:
            job_id = JobID(group=self.current_group)
            self.current_group += 1

        job = Job(job_id=job_id, job_spec=job_spec)
        job.status = JobStatus.Queued
        job.submitted = datetime.now()
        self.queued_jobs.append(job)

        return job

    def next_job(self):

        for job in sorted(
            self.queued_jobs, key=lambda j: j.job_spec.priority, reverse=True
        ):
            self.queued_jobs.remove(job)
            self.running_jobs[job.job_id] = job
            return job

    def on_job_finished(self, job_id):
        job = self.running_jobs.pop(job_id)
        self.completed_jobs.append(job)

    def prune(self):

        num_jobs = DEFAULT_CONFIG.prune_job_limt
        pruned_jobs = []
        if len(self.completed_jobs) > num_jobs:
            pruned_jobs = self.completed_jobs[num_jobs:]
            self.completed_jobs = self.completed_jobs[:num_jobs]

        now = datetime.now()
        for job in self.completed_jobs[:]:
            if now - job.completed > DEFAULT_CONFIG.prune_time_limit:
                pruned_jobs.append(job)
                self.completed_jobs.remove(job)


class WorkItem(BaseModel):

    job: Job
    future: Any
    fn: Any


class Configuration(BaseSettings):

    ip_address: str = "127.0.0.1"
    port: int = 9200
    last_job_id: JobID = JobID(group=0, index=1)
    log_file: str = join(expanduser("~"), "lqts.log")
    config_file: str = join(expanduser("~"), "lqts.config")
    nworkers: int = max(cpu_count() - 2, 1)
    ssl_cert: str = None

    prune_time_limit: timedelta = timedelta(days=1)
    prune_job_limt: int = 200

    @property
    def url(self):
        if self.ssl_cert:
            return f"https://{self.ip_address}:{self.port}"
        else:
            return f"http://{self.ip_address}:{self.port}"


DEFAULT_CONFIG = Configuration()

