"""
=============
shema Module
=============

This modules contains the main objects used to define and manage jobs and
job queues.

    * JobID
    * JobSpec
    * JobStats
    * Job
    * JobQueue
"""

import concurrent.futures as cf
import enum
import itertools
import textwrap
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple, Union

from pydantic import BaseModel

from lqts.core.config import Configuration
from lqts.simple_logging import Level, Logger, getLogger

DEBUG = False

LOGGER = getLogger("lqts", Level.INFO)


class JobID(BaseModel):
    """
    Represents the unique ID for the job that can be used to find the job.

    A JobID consists of a group number and an index.  Client commands such as
    qsub-multi and qsub-cmulti submit job groups, where each job as the same
    group number but a different index.
    """

    group: int = 1
    index: int = 0

    # @validator('index', pre=True, always=True)
    # def set_ts_now(cls, v):
    #     return v or datetime.now()

    def __hash__(self):
        return hash(str(self))

    def __str__(self):
        return f"{self.group}.{self.index:0>3}"

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
                job_id.index = None
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
            job_id = JobID()
            job_id.group = int(value["group"])
            job_id.index = int(value["index"])
            return job_id

            # return super().parse_obj(value)

    # def dict(self, *args, **kwargs):
    #     return self.__str__()

    def __lt__(self, other: "JobID"):
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
    Error = "E"
    Paused = "P"
    WalltimeExceeded = "X"


class JobSpec(BaseModel):
    command: str
    working_dir: str
    log_file: str = None
    priority: int = 10
    cores: int = 1  # number of cores required by the job
    alternate_runner: bool = False
    depends: List[JobID] = None
    walltime: float = None

    def __lt__(self, other: "JobSpec"):
        return self.priority > other.priority

    def __eq__(self, other: "JobSpec"):
        return self.priority == other.priority

    def parse_walltime(self):
        if isinstance(self.walltime, timedelta):
            self.walltime = self.walltime.total_seconds()
        elif isinstance(walltime, str):
            if ":" in walltime:
                hrs, minutes, sec = [int(x) for x in walltime.split(":")]
                seconds = sec + 60 * minutes + hrs * 3600
            else:
                walltime = float(walltime)


class Job(BaseModel):
    job_id: JobID = JobID(group=1, index=0)
    status: JobStatus = JobStatus.Queued

    submitted: datetime = None
    started: datetime = None
    completed: datetime = None

    job_spec: JobSpec = None

    cores: list[int] = None

    # def __init__(self, *args, **kwargs):
    #     print("kwargs = ", kwargs)
    #     super().__init__(*args, **kwargs)

    # def initialize(self)
    #     self.submitted = datetime.now()
    #     self.status = JobStatus.Queued

    # def __gt__(self, other: "Job"):
    #     return self.job_spec.priority > other.job_spec.priority

    # def __eq__(self, other: "Job"):
    #     return self.job_spec.priority == other.job_spec.priority

    # @property
    # def can_run(self) -> bool:
    #     # self.job_spec.depends
    #     return len(self.job_spec.depends) == 0

    @property
    def walltime(self) -> timedelta:
        try:
            if self.completed is not None:
                return self.completed - self.started
            elif self.started is not None:
                return datetime.now() - self.started
            else:
                return timedelta(0)
        except TypeError:
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
        """Returns true if this job has completed or has been deleted"""
        return self.status in (JobStatus.Completed, JobStatus.Deleted)

    def as_table_row(self) -> list:
        """Gets a list of Job attributes to show up in the qstatus tables"""
        if self.job_spec.depends:
            dependencies_str = " ".join(str(d) for d in self.job_spec.depends)
            # dependencies_str = textwrap.wrap(dependencies_str, width=40, initial_indent="<p>")
        else:
            dependencies_str = ""

        return [
            self.job_id,
            self.status.value,
            self.job_spec.priority,
            self.job_spec.command,
            self.walltime,
            self.job_spec.working_dir,
            dependencies_str,
            self.completed.isoformat() if self.status == JobStatus.Completed else "",
        ]

    def _sort_params(self):
        return (self.job_spec, self.job_id)

    def __lt__(self, other):
        return self._sort_params() < other._sort_params()

    def __eq__(self, other):
        return self._sort_params() == other._sort_params()


class JobGroup(BaseModel):
    """
    Represents a group of jobs with a common group number and
    distinct indexes
    """

    group_number: int = 0
    jobs: Dict[JobID, Job] = {}

    def next_job_index(self):
        "Return the job index for the next job to add to the job group"
        return len(self.job_ids)

    def next_job_id(self):
        return JobID(group=self.group_number, index=len(self.jobs))


class JobQueue(BaseModel):
    """
    The JobQueue keeps track of all jobs and their states.
    The DynamicProcessPool queries the JobQueue for the next job
    and keeps it informed of when a job has finished.
    """

    name: str = "default"
    queue_file: str = ""
    completed_limit: int = 500

    queued_jobs: Dict[JobID, Job] = {}
    running_jobs: Dict[JobID, Job] = {}
    completed_jobs: Dict[JobID, Job] = {}

    pruned_jobs: Dict[JobID, Job] = {}

    job_groups: Dict[int, JobGroup] = {}
    # deleted_jobs: List[Job] = []

    next_group_number: int = 1

    last_changed: datetime = datetime.now()

    is_dirty: bool = False
    flags: list = []

    config: Configuration = Configuration()

    def start_up(self):
        """Start up the queue"""
        self._start_manager_thread()

    def on_queue_change(self, *args, **kwargs):
        """
        Calls this when the queue has changed
        """
        self.last_changed = datetime.now()
        self.is_dirty = True

    def get_job_group(self, group_id: int) -> List[Job]:
        """
        Given a job group_id, gets a list of jobs in the group.
        The jobs returned are either running or queued.  Completed
        jobs are not returned
        """
        return [
            job
            for job in itertools.chain(
                self.running_jobs.values(), self.queued_jobs.values()
            )
            if job.job_id.group == group_id
        ]

    def find_job(self, job_id: JobID) -> Tuple[Job, "JobQueue"]:
        """
        Looks for a job in the queued and running jobs
        """
        if job_id in self.queued_jobs:
            return self.queued_jobs[job_id], self.queued_jobs
        elif job_id in self.running_jobs:
            return self.running_jobs[job_id], self.running_jobs
        # elif job_id in self.completed_jobs:
        #     return self.completed_jobs[job_id]
        return None, None

    def submit(self, job_specs: List[JobSpec]) -> List[JobID]:
        """
        Submits a list of job specs to the queue.  The result
        is a list of jobs.  So a JobSpec gets submitted and turns into a Job
        """
        group = JobGroup(group_number=self.next_group_number)
        self.job_groups[group.group_number] = group
        self.next_group_number += 1
        for job_spec in job_specs:
            job_id = group.next_job_id()  # JobID(group=group, index=i)
            # print(job_id, job_spec)
            job = Job(job_id=job_id, job_spec=job_spec)
            group.jobs[job_id] = job
            job.submitted = datetime.now()
            self.queued_jobs[job_id] = job

        if len(job_specs) == 1:
            LOGGER.info(
                f"+++ Assimilated job {job.job_id} at "
                + f"{job.submitted.isoformat()} - {job.job_spec.command}"
            )
        elif len(job_specs) > 1:
            first_job_id, *_, last_job_id = list(group.jobs.keys())
            LOGGER.info(
                f"+++ Assimilated jobs {first_job_id} - {last_job_id} at "
                + f"{group.jobs[first_job_id].submitted.isoformat()}"
            )

        self.on_queue_change()
        return list(group.jobs.keys())

    def running_count(self) -> int:
        """
        Gets the current nuber of running jobs sum (ncores_each_job * njobs).

        This is the number that is used to determine whether or not to start up another job
        """

        n = 0
        for job in self.running_jobs.values():
            n += job.job_spec.cores

        return n

    def next_job(self) -> Job:
        """
        Gets the next runnable job
        """
        if not self.queued_jobs:
            return None

        for job in sorted(self.queued_jobs.values()):
            if self.check_can_job_run(job.job_id):
                return job

    def on_job_started(self, started_job: Job):
        """
        Call this when a job is about to start
        """
        job = self.queued_jobs.pop(started_job.job_id)
        job.status = JobStatus.Running
        job.started = datetime.now()
        self.running_jobs[job.job_id] = job
        self.on_queue_change()

        if LOGGER is not None:
            LOGGER.info(
                f">>> Started     job {job.job_id} at {job.started.isoformat()}.  cores={job.cores}"
            )

    def on_job_finished(self, completed_job: Job):
        """
        Call this when a job is done
        """
        try:
            job = self.running_jobs.pop(completed_job.job_id)
            job.status = completed_job.status
            job.completed = completed_job.completed
            self.completed_jobs[job.job_id] = job
            duration = job.completed - job.started
            if LOGGER is not None:
                LOGGER.info(
                    f"--- Completed   job {job.job_id} at {job.completed.isoformat()}. "
                    + f"Duration = {duration}"
                )
        except KeyError:
            pass

        self.on_queue_change()

    def check_can_job_run(self, job_id: JobID) -> bool:
        """
        Checks to see if a job is able to run.  Three conditions must be met:
        1. The job must be in self.queued_jobs
        2. No dependencies must be in self.queued_jobs
        3. No depencencies must be in self.running_jobs
        """
        if job_id not in self.queued_jobs:
            return False

        job = self.queued_jobs[job_id]

        if job.job_spec.depends:
            waiting_on: List[JobID] = [
                id_
                for id_ in job.job_spec.depends
                if ((id_ in self.running_jobs) or (id_ in self.queued_jobs))
            ]
        else:
            waiting_on: List[JobID] = []

        if len(waiting_on) > 0:
            if DEBUG:
                print(f">w<{job.job_id} waiting on running jobs: {waiting_on}")

            return False
        else:
            return True

    def prune(self):
        """
        Keeps the list of completed jobs to a defined size
        """
        # completed_limit = DEFAULT_CONFIG.prune_job_limt

        completed_jobs = len(self.completed_jobs)
        if completed_jobs <= self.completed_limit:
            LOGGER.debug("Pruning - nothing pruned")
            return

        prune_count = (
            completed_jobs - self.completed_limit
        )  # int(self.completed_limit / 2)
        LOGGER.debug(f"Pruning - will prune {prune_count} completed jobs")
        self.pruned_jobs = {}
        for ij, job in enumerate(list(self.completed_jobs.values())):
            if ij >= prune_count:
                return
            if job.job_id not in self.running_jobs:
                self.completed_jobs.pop(job.job_id)
                # self.pruned_jobs[job.job_id] = job

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

            for __ in range(15):
                time.sleep(2)
                if "abort" in self.flags:
                    LOGGER.debug("Aborting and shutting down")
                    self.flags.remove("abort")
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
        self.flags.append("abort")

    def save(self):
        return
        # with open(self.queue_file, "w") as fid:

        #     fid.write("[running_jobs]\n")
        #     for job_id, job in self.running_jobs.items():
        #         fid.write(f"{job_id}: {job.json()}\n")

        #     fid.write("[queued_jobs]\n")
        #     for job_id, job in self.queued_jobs.items():
        #         fid.write(f"{job_id}: {job.json()}\n")

        #     fid.write("[completed_jobs]\n")
        #     for job_id, job in self.completed_jobs.items():
        #         fid.write(f"{job_id}: {job.json()}\n")

        # self.is_dirty = False

    def load(self):
        return
        max_job_group = 0
        with open(self.queue_file, "r") as fid:
            reading_queue = self.running_jobs
            was_running = False
            for line in fid:
                if "[running_jobs]" in line:
                    reading_queue = self.queued_jobs
                    was_running = True
                elif "[queued_jobs]" in line:
                    reading_queue = self.queued_jobs
                    was_running = False
                elif "[completed_jobs]" in line:
                    reading_queue = self.completed_jobs
                    was_running = False
                else:
                    *_, str_job = line.partition(":")
                    job = Job.parse_raw(str_job)
                    if was_running:
                        job.status = JobStatus.Queued
                    max_job_group = max(job.job_id.group, max_job_group)

                    reading_queue[job.job_id] = job

            self.is_dirty = False
            self.next_group_number = max_job_group + 1

    @property
    def all_jobs(self):
        return list(
            itertools.chain(
                self.running_jobs.values(),
                self.queued_jobs.values(),
                self.completed_jobs.values(),
            )
        )

    def pop_job(self, job: Job, queue: Dict[JobID, Job]) -> Job:
        if job is None:
            return None
        else:
            queue.pop(job.job_id)
            job.status = JobStatus.Deleted
            job.completed = datetime.now()
            self.completed_jobs[job.job_id] = job
            return job

    def qdel(self, job_ids: List[JobID]) -> List[JobID]:
        """
        Delete on or more jobs
        """

        deleted_job_ids = []

        for job_id in list(job_ids):
            if job_id.index is None:
                for job_id2 in self.job_groups[job_id.group]:
                    job, queue = self.find_job(job_id2)
                    if job is not None:
                        job = self.pop_job(job, queue)
                        deleted_job_ids.append(job.job_id)
            else:
                job, queue = self.find_job(job_id)
                if job is not None:
                    job = self.pop_job(job, queue)
                    deleted_job_ids.append(job.job_id)

        self.on_queue_change()

        return deleted_job_ids

    def clear(self):
        for job_id in list(self.running_jobs.keys()):
            job = self.running_jobs.pop(job_id)
            job.status = JobStatus.Deleted
            self.completed_jobs[job_id] = job


class WorkItem(BaseModel):
    job: Job
    future: Any
    fn: Any
