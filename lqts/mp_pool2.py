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

import multiprocessing as mp
import os
import subprocess
import threading
import time

# from collections import deque
from dataclasses import dataclass
from datetime import datetime

# from pathlib import Path
from textwrap import dedent

import psutil

from lqts.core.schema import Job, JobID, JobQueue, JobStatus
from lqts.resources import CPUResourceManager
from lqts.version import VERSION

DEFAULT_WORKERS = max(mp.cpu_count() - 2, 1)


@dataclass
class WorkItem:
    """
    A WorkItem is the object that executes a Job.  To do so it has
        * job: the job (including job spec)
        * cores: list of cpu cores assigned to this job
        * process: the process (in the system or cpu sense of the word) that the job executes as
        * logfile: handle to the logfile for writing
    """

    job: Job
    cores: list = None

    mark: int = 0

    process: psutil.Process = None

    logfile = None  # file handle

    _logging_thread = None

    def start_logging(self):
        """
        Opens the log file and writes the job header
        """
        if self.job.job_spec.log_file:
            self.logfile = open(self.job.job_spec.log_file, "w")

            header = dedent(
                f"""
                Executed with LQTS (the Lightweight Queueing System)
                LQTS Version {VERSION}
                -----------------------------------------------
                Job ID:  {self.job.job_id}
                WorkDir: {self.job.job_spec.working_dir}
                Command: {self.job.job_spec.command}
                Started: {self.job.started.isoformat()}
                -----------------------------------------------

                """
            )

            self.logfile.write(header)

    def start(self):
        """
        Starts the job.  The follow steps take place:
            1. Change directory to the job's working dir
            2. Optionally start logging
            3. Start the process
            4. Set the process priority low so desktop systems stay reponsive
            5. Set the cpu affinity for the process to the assigned cores
        """

        # ================================================
        # 1. Change directory to the job's working dir
        # ================================================
        os.chdir(self.job.job_spec.working_dir)

        self.job.started = datetime.now()

        if self.job.job_spec.log_file:
            # ================================================
            # 2. Optionally start logging
            # ================================================
            self.start_logging()

        try:
            # ================================================
            # 3. Start the process
            # ================================================
            self.process = psutil.Popen(
                self.job.job_spec.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
            )

            # ================================================
            # 4. Set the process priority low so desktop systems stay reponsive
            # ================================================
            if psutil.WINDOWS:
                self.process.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
                self.process.ionice(psutil.IOPRIO_LOW)
            elif psutil.LINUX:
                self.process.nice(10)
                self.process.ionice(psutil.IOPRIO_CLASS_BE, value=5)

            # ================================================
            # 5. Set the cpu affinity for the process to the assigned cores
            # ================================================
            # Set the cpu affinity for the job so it doesn't hop all over the place
            # This is very helpful on large core systems
            self.process.cpu_affinity(self.cores)
            self.job.cores = self.cores

            self._logging_thread = threading.Thread(target=self.get_output)
            self._logging_thread.start()

        except FileNotFoundError:
            self.logfile.write(
                f"\nERROR: Command not found.  Ensure the command is an executable file.\n"
            )
            self.logfile.write(
                f"Make sure you give the full path to the file or "
                "that it is on your system path.\n\n"
            )
            # ================================================
            # Flag the job as completed with an error status
            self.job.completed = datetime.now()
            self.job.status = JobStatus.Error

    def get_status(self) -> JobStatus:
        """
        Get the status of this work item
        """
        if self.job.status not in (
            JobStatus.Error,
            JobStatus.Deleted,
            JobStatus.Completed,
        ):
            try:
                # If we can query the process status, it is a live and running
                status = self.process.status()
                self.job.status = JobStatus.Running
            except psutil.NoSuchProcess:
                # If self.process.status() fails, the process has exited
                # so the job is done
                self.job.status = JobStatus.Completed
        if (self.job.walltime is not None) and (self.job.job_spec.walltime is not None):
            if self.job.walltime.total_seconds() > self.job.job_spec.walltime:
                self.job.status = JobStatus.WalltimeExceeded
                self.kill()

        return self.job.status

    def is_running(self) -> bool:
        """
        Convienience method to tell if job status is JobStatus.Running
        """
        return self.get_status() == JobStatus.Running

    def get_output(self):
        """
        Reads some output from the process and writes it to the logfile
        """
        # print(f"Work item logging jobid= {self.job.job_id}")
        time.sleep(5)
        try:
            while True:
                line = self.process.stdout.read(64)
                # line += self.process.stderr.read(256)
                line = line.decode().replace("\r", "").replace("\n\n", "\n")
                # print(f"{line=}")
                self.logfile.write(line)
                self.logfile.flush()
        except Exception as ex:
            # import traceback
            # traceback.print_exc()
            pass

    def clean_up(self):
        """
        Mark sjob as completed and write epilogue to logfile
        """

        # self.get_output()

        self.job.completed = datetime.now()

        if not self.job.job_spec.log_file:
            return

        footer = dedent(
            f"""
            -----------------------------------------------
            Job Performance
            -----------------------------------------------
            Started: {self.job.started.isoformat()}
            Ended:   {self.job.completed.isoformat()}
            Elapsed: {self.job.walltime}
            -----------------------------------------------
            """
        )

        try:
            self.logfile.write(footer)

            self.logfile.close()
        except:
            pass

    def kill(self):
        """
        Kill this job and set its status to deleted
        """
        self.process.kill()
        self.job.status = JobStatus.Deleted


@dataclass
class Event:
    job: Job
    event_type: str
    when: datetime


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
        max_workers: int = DEFAULT_WORKERS,
        feed_delay: float = 0.0,
        manager_delay: float = 1.0,
    ):
        self.job_queue: JobQueue = queue

        self.CPUManager = CPUResourceManager(
            min(max(max_workers, 1), mp.cpu_count() - 1)
        )

        self.feed_delay = feed_delay  # delay between subsequent job start ups

        self.manager_delay = manager_delay  # delay in manager thread loop

        self._work_items: dict[JobID, WorkItem] = {}

        # self._queue = deque()

        self.__exiting = False

        self.q_lock = threading.Lock()

        self.w_lock = threading.Lock()

        self._event_callbacks = set()

        self.log = DummyLogger()
        self._logging_threads = []

        self.__paused: bool = False
        self.__manager_thread = None

    @property
    def max_workers(self) -> int:
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

        # see if any results are available
        for job_id, work_item in list(self._work_items.items()):
            if not work_item.is_running():
                # the work_item has completed
                work_item.mark += 1
                if work_item.mark > 1:
                    # clean it up
                    work_item.clean_up()
                    # free the cpu resources
                    self.CPUManager.free_processors(work_item.cores)

                    job = work_item.job

                    self.log.info("Got result {} = {}".format(job.job_id, job))
                    self.job_queue.on_job_finished(job)
                    self._work_items.pop(job_id)

    def get_log_output(self):
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

        # see if any results are available
        for work_item in list(self._work_items.values()):
            if work_item.is_running():
                print(f"-->Getting output {work_item.job.job_id}")
                work_item.get_output()

    def submit_one_job(self, job: Job, cores: list) -> tuple[bool, WorkItem]:
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
                # no jobs available
                break

            some_available, cores = self.CPUManager.get_processors(
                count=job.job_spec.cores
            )

            if not some_available:
                # not enough cores are available to run this job
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

    def kill_job(self, job_id_to_kill, kill_all=False) -> int:
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
        # i = 0
        while True:
            time.sleep(self.manager_delay)
            # print(f"Cycling {i=}")
            # check for finished jobs
            self.process_completions()

            # if (i := i + 1) == 20:
            #     # get log output every 20th time through this loop
            #     print("Getting output 0")
            #     self.get_log_output()
            #     i = 0

            if self.__exiting:
                if len(self._work_items) == 0:
                    # we are done
                    return
                else:
                    # we still have some clean up to do
                    continue

            elif self.__paused:
                # don't do anything this time through the loop
                continue

            else:
                # start up new jobs
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

    def join(self, wait: bool = True):
        """
        If wait is True, this blocks until all jobs are complete.
        If wait is False, then running jobs are killed and we wait for
        the manager thread to complete
        """
        self.shutdown(wait=wait)
        self.__manager_thread.join()

    def shutdown(self, wait: bool = True):
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
                # kill running jobs
                work_item.kill()

    def _start_manager_thread(self) -> threading.Thread:
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
