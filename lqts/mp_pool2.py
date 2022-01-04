"""
mp_pool Module
================

The mp_pool module implements and DynamicProcessPool which is similar to the the
concurrent.futures.ProcessPoolExecutor, but it has several significant differences.
Each job that is created starts a process and that process is terminated
when the job is done.  This is intended for medium to long run time jobs where it
is desirable to have the ability to kill a running job.  The walltime or each
job can also be tracked.

"""
# import concurrent.futures as cf
import multiprocessing as mp
import os
# import queue
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from typing import Any, Callable, Dict, List

# from pydantic import BaseModel, PyObject, validator
import psutil

from lqts.job_runner import run_command
from lqts.resources import CPUResourceManager, CPUResponse
from lqts.version import VERSION

from lqts.schema import Job, JobID, JobQueue, JobStatus

# import logging




DEFAULT_WORKERS = max(mp.cpu_count() - 2, 1)


@dataclass
class WorkItem:

    job: Job
    cores: List = None

    # start_time: datetime = None
    # stop_time: datetime = None

    mark: int = 0

    process: psutil.Process = None

    logfile = None  # file handle

    def start_logging(self):
        if self.job.job_spec.log_file:
            self.logfile = open(self.job.job_spec.log_file, "w")

            header = dedent(
                """
                Executed with LQTS (the Lightweight Queueing System)
                LQTS Version {}
                -----------------------------------------------
                Job ID:  {}
                WorkDir: {}
                Command: {}
                Started: {}
                -----------------------------------------------

                """.format(
                    VERSION,
                    self.job.job_id,
                    self.job.job_spec.working_dir,
                    self.job.job_spec.command,
                    self.job.started.isoformat(),
                    # end.isoformat(),
                    # (end - start),
                )
            )

            self.logfile.write(header)

    def start(self):
        # p = subprocess.Popen(
        #     command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False
        # )
        os.chdir(self.job.job_spec.working_dir)

        self.job.started = datetime.now()

        if self.job.job_spec.log_file:
            self.start_logging()

        try:
            # print("starting")
            self.process = psutil.Popen(
                self.job.job_spec.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
            )
            # print("started")
            if psutil.WINDOWS:
                self.process.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
                self.process.ionice(psutil.IOPRIO_LOW)
            elif psutil.LINUX:
                self.process.nice(10)
                self.process.ionice(psutil.IOPRIO_CLASS_BE, value=5)
            # ================================================

            # ================================================
            # set the cpu affinity for the job so it doesn't hop all over the place
            # this is QUITE be helpful on large core systems
            # if cores is None:
            #     some_available, cores = self.CPUManager.get_processors(count=job.job_spec.cores)

            self.process.cpu_affinity(self.cores)

        except FileNotFoundError:
            self.logfile.write(
                f"\nERROR: Command not found.  Ensure the command is an executable file.\n"
            )
            self.logfile.write(
                f"Make sure you give the full path to the file or that it is on your system path.\n\n"
            )
            self.job.completed = datetime.now()
            self.job.status = JobStatus.Error

    def get_status(self):

        if self.job.status not in (JobStatus.Error, JobStatus.Deleted):
            try:
                status = self.process.status()
                self.job.status = JobStatus.Running
            except psutil.NoSuchProcess:
                self.job.status = JobStatus.Completed

        return self.job.status

    def is_running(self):
        return self.get_status() == JobStatus.Running

    def get_output(self):
        line = self.process.stdout.read()
        line += self.process.stderr.read()
        line = line.decode().replace("\r", "").replace("\n\n", "\n")

        self.logfile.write(line)

    def clean_up(self):
        self.job.completed = datetime.now()

        if not self.job.job_spec.log_file:
            return

        footer = dedent(
            """
            -----------------------------------------------
            Job Performance
            -----------------------------------------------
            Started: {}
            Ended:   {}
            Elapsed: {}
            -----------------------------------------------
            """
        )

        footer = footer.format(
            self.job.started.isoformat(),
            self.job.completed.isoformat(),
            (self.job.walltime),
        )
        self.logfile.write(footer)

        self.logfile.close()

    def kill(self):
        self.process.kill()
        self.job.status = JobStatus.Deleted

    # @validator("future")
    # def allow_anything(cls, v):
    #     return v

    # @validator("fn")
    # def allow_anything2(cls, v):
    #     return v


@dataclass
class Event:

    job: Job
    event_type: str
    when: datetime


# def mp_worker_func(q_in: mp.Queue, q_out: mp.Queue):

#     # job, func, args, kwargs = q_in.get()
#     work_item = q_in.get()
#     # print(work_item)

#     job = run_command(work_item[0])
#     # job.started = datetime.now()
#     # future.set_result(result)
#     # stop_time = datetime.now()
#     # job.completed = datetime.now()
#     # job.walltime = job.completed - job.started
#     # print(job)
#     # future._state = cf._base.FINISHED
#     q_out.put(job)


class DummyLogger:
    def debug(self, *args):
        pass

    def info(self, *args):
        pass

    def error(self, *args):
        pass


class DynamicProcessPool:
    """
    A process pool that can be resized.  Individual processes may be terminated.
    It can send notifications of job starts and completions.
    """

    def __init__(
        self,
        queue: JobQueue,
        max_workers=DEFAULT_WORKERS,
        feed_delay=0.0,
        manager_delay=1.0,
    ):

        # self.server = server
        self.job_queue: JobQueue = queue

        # max_works = max(max_workers, 1)
        self.CPUManager = CPUResourceManager(
            min(max(max_workers, 1), mp.cpu_count() - 1)
        )
        # if max_workers is not None:
        #     if max_workers <= 0:
        #         raise ValueError("max_workers must be greater than 0")
        #     self._max_workers = max_workers

        self.feed_delay = feed_delay
        self.manager_delay = manager_delay

        self._work_items: Dict[JobID, WorkItem] = {}

        self._queue = deque()  # deque(maxlen=1000)
        # self._results = {}

        # self.q_input = mp.Queue()
        # self.q_output = mp.Queue()
        self.__exiting = False
        # self.results = deque(maxlen=500)

        self.q_lock = threading.Lock()
        # self.job_lock = threading.Lock()
        self.w_lock = threading.Lock()

        # self.status_queue = mp.Queue()  # used to send signals and data to external code

        # self.q_count = 0

        # self.__signal_queue = mp.Queue()  # used to send internal signals and data

        # self._start_manager_thread()

        self._event_callbacks = set()

        self.log = DummyLogger()

        self.__paused: bool = False
        self.__manager_thread = None

    @property
    def max_workers(self):
        return self.CPUManager.cpu_count

    @max_workers.setter
    def max_workers(self, value):
        self.resize(value)

    def set_logger(self, logger):

        self.log = logger

    def resize(self, max_workers):
        """
        Adjusts the number of worker processes that may be used.

        Parameters
        ----------
        max_workers: int
            Maximum number of workers
        """
        more_capacity = max_workers > self.max_workers
        if max_workers is not None:

            self.CPUManager.resize(max_workers)

            if more_capacity:
                self.feed_queue()

    def process_completions(self, timeout=2.0):
        """
        Handles getting the results when a job is done and cleaning up
        worker processes that have finished.  It then calls feed_queue
        to ensure that work continues to be done.

        Parameters
        ----------
        timeout: int
            A timeout for waiting on a result

        """
        work_item: WorkItem
        # try:
        # see if any results are available
        for job_id, work_item in list(self._work_items.items()):
            if not work_item.is_running():
                work_item.mark += 1
                if work_item.mark > 1:
                    print(f"finished job {job_id}")
                    work_item.clean_up()
                    self.CPUManager.free_processors(work_item.cores)

                    job = work_item.job
                    # print(job)
                    self.log.info("Got result {} = {}".format(job.job_id, job))
                    self.job_queue.on_job_finished(job)
                    self._work_items.pop(job_id)

        # make sure to feed the queue to keep work going
        # if not self.__paused:
        #     self.feed_queue()

    def submit_one_job(self, job: Job, cores: list):
        """Start one job running in the pool"""

        work_item = WorkItem(job=job, cores=cores)

        work_item.start()

        self.job_queue.on_job_started(job)

        return True, work_item

    def feed_queue(self):
        """
        Starts up jobs while there are jobs in the queue and there are workers
        available.
        """

        while len(self.job_queue.queued_jobs) > 0:

            job = self.job_queue.next_job()

            if job is None:
                break

            some_available, cores = self.CPUManager.get_processors(
                count=job.job_spec.cores
            )

            if not some_available:
                break
            # while there is work to do and workers available, start up new jobs
            job_was_submitted, work_item = self.submit_one_job(job, cores)
            self._work_items[job.job_id] = work_item

            if job_was_submitted:
                time.sleep(self.feed_delay)
            else:
                break

    def pause(self):
        self.__paused = True

    def unpause(self):
        self.__paused = False

    def kill_job(self, job_id_to_kill, kill_all=False):
        """
        Kills the job with ID *job_id_to_kill*

        Parameters
        ----------
        job_id_to_kill : int

        Returns
        -------
        success: bool
            True if the job was found and killed, False is the job was not found.
        """

        if kill_all:
            job_ids_to_kill = list(self._work_items.keys())
        else:
            job_ids_to_kill = [job_id_to_kill]

        killed_jobs = []
        for jid in job_ids_to_kill:
            try:
                work_item = self._work_items.pop(jid)
                work_item.kill()
                print(f"killing running job {jid}")
                self.CPUManager.free_processors(work_item.cores)
                killed_jobs.append(jid)
            except psutil.NoSuchProcess:
                pass

        return len(killed_jobs) > 0

    def _runloop(self):
        """
        This is the loop that manages getting job completetions, taking care of the sub-processes
         and keeping the queue moving
        """
        while True:
            time.sleep(self.manager_delay)
            self.process_completions()

            if self.__exiting:
                if len(self._work_items) == 0:
                    return
                else:
                    continue

            elif self.__paused:
                continue

            else:
                self.feed_queue()

    # def join(self, timeout=None):
    #     """
    #     Blocks until all jobs are complete
    #     Parameters
    #     ----------
    #     timeout: int
    #         optional time value
    #     """
    #     self.log.debug("waiting to join")
    #     value = ""
    #     while len(self._work_items) > 0:
    #         value = self.__signal_queue.get(timeout=timeout)
    #         self.log.debug("join received signal: {}".format(value))

    def join(self, wait=True):
        self.shutdown(wait=wait)
        # print("waiting for things to finish up")
        self.__manager_thread.join()

    def shutdown(self, wait=True):
        """
        Shuts down the pool.

        Parameters
        ----------
        wait: bool
            If True, wait until all jobs are complete, then shutdown.
            If False then kill the processes and shutdown immediately
        """
        self.__exiting = True

        if not wait:
            for work_item in self._work_items.values():
                work_item.kill()

    def _start_manager_thread(self):
        """
        Starts the thread that manages the process pool

        Returns
        -------
        t: threading.Thread
            The management thread
        """
        t = threading.Thread(target=self._runloop)
        t.start()
        self.__manager_thread = t
        return t

    def _start_sync(self):
        """
        Starts the management function synchronously.  Use only for debugging
        """
        self._runloop()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown(wait=True)
        return False

    def add_event_callback(self, func):
        """
        Registers a callback function that is called when jobs start or stop

        Parameters
        ----------
        func : callable


        """
        self._event_callbacks.add(func)
