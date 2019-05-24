import enum
from datetime import datetime, timedelta
import itertools
from os.path import join, expanduser
from multiprocessing import cpu_count
from pydantic import BaseModel
from typing import List, Deque, Union


class JobID(BaseModel):

    group: int = 1
    index: int = None

    # @validator('index', pre=True, always=True)
    # def set_ts_now(cls, v):
    #     return v or datetime.now()

    def __hash__(self):
        return hash(str(self))

    def __str__(self):
        return f"{self.group}.{self.index}"

    @staticmethod
    def parse(value):
        job_id = JobID()
        if isinstance(value, JobID):
            return value
        elif isinstance(value, str):
            if "." not in value:
                job_id.group = int(value)
            else:
                g, i = value.split(".")
                job_id.group = int(g)
                if i in (None, "*"):
                    job_id.index = None
                else:
                    job_id.index = int(i)

        elif isinstance(value, int):
            job_id.group = value
            job_id.index = 0
        else:
            raise ValueError(
                f"JobID.parse excepts types int, JobID, or str. You provided {value} of type {type(value)}."
            )
        return job_id


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
    depends: List[JobID] = []


class Job(BaseModel):

    job_id: JobID = JobID(group=1, index=0)
    status: JobStatus = JobStatus.Initialized

    submitted: datetime = None
    started: datetime = None
    completed: datetime = None

    # walltime: timedelta = None
    job_spec: JobSpec = None

    completed_depends: List[JobID] = []

    @property
    def can_run(self):
        return len(self.job_spec.depends) == 0

    @property
    def walltime(self):

        if self.completed is not None:
            return self.completed - self.started
        elif self.started is not None:
            return datetime.now() - self.started
        else:
            return timedelta(0)

    def _should_prune(self):
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

    def is_done(self):
        return self.status in (JobStatus.Completed, JobStatus.Deleted)

    def as_table_row(self):

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


class JobQueue(BaseModel):

    jobs: List[Job] = []
    pruned_jobs: List[Job] = []

    current_index: int = 1

    def prune(self):
        self.pruned_jobs = [
            job
            for job in self.pruned_jobs
            if (datetime.now() - job.completed) < timedelta(seconds=4 * 3600)
        ]
        self.pruned_jobs += [job for job in self.jobs if job._should_prune()]
        self.jobs = [job for job in self.jobs if not job._should_prune()]

    def submit(self, job_spec: JobSpec, job_id=None) -> Job:

        if job_id is None:
            job_id = JobID(group=self.current_index)
            self.current_index += 1

        job = Job(job_id=job_id, job_spec=job_spec)
        job.status = JobStatus.Queued
        job.submitted = datetime.now()
        self.jobs.append(job)

        return job

    def get_job_group(self, group_id: int) -> List[Job]:

        return [job for job in self.jobs if job.job_id.group == group_id]


class Configuration(BaseModel):

    ip_address: str = "127.0.0.1"
    port: int = 9200
    last_job_id: JobID = JobID(group=0, index=1)
    log_file: str = join(expanduser("~"), "lqts.log")
    config_file: str = join(expanduser("~"), "lqts.config")
    nworkers: int = max(cpu_count() - 2, 1)
    ssl_cert: str = None

    @property
    def url(self):
        if self.ssl_cert:
            return f"https://{self.ip_address}:{self.port}"
        else:
            return f"http://{self.ip_address}:{self.port}"


DEFAULT_CONFIG = Configuration()

