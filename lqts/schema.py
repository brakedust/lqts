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

DEBUG = False


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

    # def dict(self, *args, **kwargs):
    #     return self.__str__()

    def __lt__(self, other: 'JobID'):

        if self.group == other.group:
            return self.index < other.index
        else:
            return self.group < other.group

    # def __eq__(self, other: 'JobID'):

    #     return (self.group == other.group) and (self.index == other.index)


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

    def __lt__(self, other: 'JobSpec'):
        return self.priority > other.priority

    def __eq__(self, other: 'JobSpec'):
        return self.priority == other.priority


class Job(BaseModel):

    job_id: JobID = JobID(group=1, index=0)
    status: JobStatus = JobStatus.Initialized

    submitted: datetime = None
    started: datetime = None
    completed: datetime = None

    # walltime: timedelta = None
    job_spec: JobSpec = None

    # completed_depends: List[JobID] = []

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
            ",".join(str(d) for d in self.job_spec.depends) if self.job_spec.depends else ""
        ]
    def _sort_params(self):

        return (self.job_spec, self.job_id)

    def __lt__(self, other):

        return self._sort_params() < other._sort_params()

    def __eq__(self, other):

        return self._sort_params() == other._sort_params()

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

    queued_jobs: Dict[JobID, Job] = {}
    running_jobs: Dict[JobID, Job] = {}
    completed_jobs: Dict[JobID, Job] = {}

    pruned_jobs: Dict[JobID, Job] = {}
    # deleted_jobs: List[Job] = []

    current_group: int = 1

    last_changed: datetime = datetime.now()

    is_dirty: bool = False
    flags: list = []

    # def __post_init__(self):

    #     self._last_save = datetime(year=1995)
    def __init__(self, *args, start_manager_thread=False, **kwargs):
        super().__init__(*args, **kwargs)
        if start_manager_thread:
            self._start_manager_thread()


    @property
    def queue_file(self):
        return DEFAULT_CONFIG.queue_file

    def on_queue_change(self):
        self.last_changed = datetime.now()
        self.is_dirty = True

    def get_job_group(self, group_id: int) -> List[Job]:
        # pass
        return [
            job for job in itertools.chain(self.running_jobs.values(), self.queued_jobs.values()) if
            job.job_id.group == group_id
        ]

    def find_job(self, job_id):
        """
        Looks for a job in the queued and running jobs
        """
        if job_id in self.queued_jobs:
            return self.queued_jobs[job_id]
        elif job_id in self.running_jobs:
            return self.running_jobs[job_id]
        # elif job_id in self.completed_jobs:
        #     return self.completed_jobs[job_id]
        return None

    def submit(self, job_spec: JobSpec, job_id=None) -> Job:
        """
        Adds a new job to the queue
        """
        if job_id is None:
            job_id = JobID(group=self.current_group)
            self.current_group += 1

        job = Job(job_id=job_id, job_spec=job_spec)
        job.status = JobStatus.Queued
        job.submitted = datetime.now()
        self.queued_jobs[job.job_id] = job
        self.on_queue_change()
        # print("Submitted: ", job,"\n")

        return job

    def next_job(self):
        """
        Gets the next runnable job
        """
        if not self.queued_jobs:
            return None

        for job in sorted(self.queued_jobs.values()):
            return job

    def on_job_started(self, job_id):
        """
        Call this when a job is about to start
        """
        job = self.queued_jobs.pop(job_id)
        job.status = JobStatus.Running
        job.started = datetime.now()
        self.running_jobs[job.job_id] = job
        self.on_queue_change()

    def on_job_finished(self, job_id):
        """
        Call this when a job is done
        """
        job = self.running_jobs.pop(job_id)
        job.status = JobStatus.Completed
        job.completed = datetime.now()
        self.completed_jobs[job.job_id] = job
        self.on_queue_change()

    def check_can_job_run(self, job_id: JobID):
        """
        Checks to see if a job is able to run.  Three conditions must be met:
        1. The job must be in self.queued_jobs
        2. No dependencies must be in self.queued_jobs
        3. No depencencies must be in self.running_jobs
        """
        if job_id not in self.queued_jobs:
            return False

        job = self.queued_jobs[job_id]

        waiting_on: List[JobID] = [
            id_ for id_ in job.job_spec.depends if
            ((id_ in self.running_jobs) or (id_ in self.queued_jobs))
        ]

        if len(waiting_on) > 0:

            if DEBUG:
                print(f'>w<{job.job_id} waiting on running jobs: {waiting_on}')

            return False
        else:
            return True


    def prune(self):
        """
        Keeps the list of completed jobs to a defined size
        """
        completed_limit = DEFAULT_CONFIG.prune_job_limt
        completed_jobs = len(self.completed_jobs)
        if completed_jobs < completed_limit:
            return

        prune_count = completed_jobs - int(completed_limit/2)

        self.pruned_jobs = {}
        for ij, job in enumerate(list(self.completed_jobs.values())):
            if ij >= prune_count:
                return
            self.completed_jobs.pop(job.job_id)
            self.pruned_jobs[job.job_id] = job

        self.on_queue_change()

    def _runloop(self):
        """
        This is the loop that manages getting job completetions, taking care of the sub-processes
         and keeping the queue moving
        """
        import time
        while True:

            self.prune()
            if self.is_dirty:
                self.save()

            for i in range(15):
                time.sleep(2)
                if 'abort' in self.flags:
                    self.flags.remove('abort')
                    return

    def _start_manager_thread(self):
        """
        Starts the thread that manages the process pool

        Returns
        -------
        t: threading.Thread
            The management thread
        """
        import threading
        t = threading.Thread(target=self._runloop)
        t.start()
        return t

    def shutdown(self):
        self.flags.append('abort')

    def save(self):

        with open(DEFAULT_CONFIG.queue_file, 'w') as fid:

            fid.write('[running_jobs]\n')
            for job_id, job in self.running_jobs.items():
                fid.write(f"{job_id}: {job.json()}\n")

            fid.write('[queued_jobs]\n')
            for job_id, job in self.queued_jobs.items():
                fid.write(f"{job_id}: {job.json()}\n")

            fid.write('[completed_jobs]\n')
            for job_id, job in self.completed_jobs.items():
                fid.write(f"{job_id}: {job.json()}\n")

        self.is_dirty = False

    def load(self):

        max_job_group = 0
        with open(DEFAULT_CONFIG.queue_file, 'r') as fid:

            reading_queue = self.running_jobs
            was_running = False
            for line in fid:
                if '[running_jobs]' in line:
                    reading_queue = self.queued_jobs
                    was_running = True
                elif '[queued_jobs]' in line:
                    reading_queue = self.queued_jobs
                    was_running = False
                elif '[completed_jobs]' in line:
                    reading_queue = self.completed_jobs
                    was_running = False
                else:
                    *_, str_job = line.partition(':')
                    job = Job.parse_raw(str_job)
                    if was_running:
                        job.status = JobStatus.Queued
                    max_job_group = max(job.job_id.group, max_job_group)

                    reading_queue[job.job_id] = job

            self.is_dirty = False
            self.current_group = max_job_group + 1


    @property
    def all_jobs(self):

        return list(itertools.chain(
            self.running_jobs.values(),
            self.queued_jobs.values(),
            self.completed_jobs.values()
        ))



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
    queue_file: str =  join(expanduser("~"), "lqts.queue.txt")
    nworkers: int = max(cpu_count() - 2, 1)
    ssl_cert: str = None

    prune_time_limit: timedelta = timedelta(days=1)
    prune_job_limt: int = 1000

    @property
    def url(self):
        if self.ssl_cert:
            return f"https://{self.ip_address}:{self.port}"
        else:
            return f"http://{self.ip_address}:{self.port}"


DEFAULT_CONFIG = Configuration()
