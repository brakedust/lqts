"""
mp_pool Module
================

The mp_pool module implements and DynamicProcessPool which is similar to the the
concurrent.futures.ProcessPoolExecutor, but it has several significant differences.
Each job that is created starts a new Python process and that process is terminated
when the job is done.  This is intended for medium to long run time jobs where it
is desirable to have the ability to kill a running job.  The walltime or each
job can also be tracked.

"""
import concurrent.futures as cf
from datetime import datetime

# import logging
import multiprocessing as mp
import queue
import threading
import time
from collections import deque
from typing import Callable, List, Dict, Any

from pydantic import BaseModel, PyObject, validator
import psutil

from .schema import JobID, Job, JobStatus, JobQueue
from lqts.job_runner import run_command

DEFAULT_WORKERS = max(mp.cpu_count() - 2, 1)


class _WorkItem(BaseModel):

    job: Job
    future: Any
    fn: Any
    # args: List[str] = []
    # kwargs: Dict = {}
    start_time: datetime = None
    stop_time: datetime = None

    # @validator("future")
    # def allow_anything(cls, v):
    #     return v

    # @validator("fn")
    # def allow_anything2(cls, v):
    #     return v


class Event(BaseModel):

    job: Job
    event_type: str
    when: datetime


def mp_worker_func(q_in: mp.Queue, q_out: mp.Queue):

    # job, func, args, kwargs = q_in.get()
    work_item = q_in.get()
    # print(work_item)

    job = run_command(work_item[0])
    # job.started = datetime.now()
    # future.set_result(result)
    # stop_time = datetime.now()
    # job.completed = datetime.now()
    # job.walltime = job.completed - job.started
    # print(job)
    # future._state = cf._base.FINISHED
    q_out.put(job)


class DummyLogger:
    def debug(self, *args):
        pass

    def info(self, *args):
        pass

    def error(self, *args):
        pass


class DynamicProcessPool(cf.Executor):
    """
    A process pool that can be resized.  Individual processes may be terminated.
    It can send notifications of job starts and completions.
    """

    def __init__(self, server , max_workers=DEFAULT_WORKERS, feed_delay=0.05):

        self.server = server
        # self.server_queue: JobQueue = server.queue

        if max_workers is not None:
            if max_workers <= 0:
                raise ValueError("max_workers must be greater than 0")
            self._max_workers = max_workers

        self.feed_delay = feed_delay

        self._workers = {}

        self._queue = deque()  # deque(maxlen=1000)
        self._results = {}

        self.q_input = mp.Queue()
        self.q_output = mp.Queue()
        self.__abort = False
        # self.results = deque(maxlen=500)

        self.q_lock = threading.Lock()
        # self.job_lock = threading.Lock()
        self.w_lock = threading.Lock()

        # self.status_queue = mp.Queue()  # used to send signals and data to external code

        self.q_count = 0

        self.__signal_queue = mp.Queue()  # used to send internal signals and data

        self._start_manager_thread()

        self._event_callbacks = set()

        self.log = DummyLogger()

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

        if max_workers is not None:
            if max_workers <= 0:
                raise ValueError("max_workers must be greater than 0")
            self._max_workers = max_workers

            self.feed_queue()

    def submit(self, func: Callable, job: Job):

        self.q_count += 1
        # f = MyFuture(func, args, job_id, call_back=call_back)
        future = cf.Future()
        # if job_id is None:
        #     job_id = self.q_count

        # if args is None:
        #     args = tuple()

        # if kwargs is None:
        #     kwargs = {}

        work_item = _WorkItem(
            job=job,
            future=future,
            fn=func,
            # args=args,
            # kwargs=kwargs
        )

        with self.q_lock:
            self.log.debug("Submitting {}".format(job.job_id))
            self._queue.append(work_item)
            self._results[job.job_id] = work_item
        # self.feed_queue()

        return future

    submit.__doc__ = cf._base.Executor.submit.__doc__

    def process_completions(self, timeout=1.0):
        """
        Handles getting the results when a job is done and cleaning up
        worker processes that have finished.  It then calls feed_queue
        to ensure that work continues to be done.

        Parameters
        ----------
        timeout: int
            A timeout for waiting on a result

        """
        try:
            # see if any results are available

            job = self.q_output.get(timeout=timeout)
            print(job)
            self.log.info("Got result {} = {}".format(job.job_id, job))
            self.server.job_done_handler(job)

        except queue.Empty:
            pass

        # Remove any processes that are complete
        for job_id, (work_item, p) in tuple(self._workers.items()):
            if not p.is_alive():
                with self.w_lock:
                    self._workers.pop(job_id)

        # make sure to feed the queue to keep work going
        self.feed_queue()

    def submit_one_job(self):

        future = cf.Future()

        # job = None
        job = self.server.queue.next_job()
        # for jid in self.server.queue.queued_jobs:
        #     # j: Job = j
        #     if self.server.check_can_job_run(jid):
        #         job = self.server.queue.queued_jobs[jid]
        #         # self.server.queue.running_jobs[jid] = job
        #         # self.server.queue.queued_jobs = [jb for jb in self.server.queue.queued_jobs if jb.job_id != j.job_id]
        #         # self.server.queue.running_jobs[job.job_id] = job
        #         # job.status = JobStatus.Running
        #         break
        #     else:
        #         pass
        #         # print(f"Job cannot run: {j}")
        #         # print(self.server.queue.running_jobs)
        #         # print(self.server.queue.queued_jobs)
        # else:
        if job is None:
            return False, None

        future = cf.Future()

        work_item = _WorkItem(job=job, future=future, fn=run_command)

        with self.q_lock:
            # self.server.log.info(f"<-> Started     job {job.job_id} at {datetime.now().isoformat()}")
            self.server.job_started_handler(job)
            # self._queue.append(work_item)
            self._results[job.job_id] = work_item

            future._state = cf._base.RUNNING
            # self.log.debug("Spawning {}".format(future))
            self.q_input.put((job, work_item.fn))
            # self._result_queue[job_id] = future

            p = mp.Process(target=mp_worker_func, args=(self.q_input, self.q_output))
            p.start()

        with self.w_lock:
            self._workers[job.job_id] = (work_item, p)

        return True, work_item

    def feed_queue(self):
        """
        Starts up jobs while there are jobs in the queue and there are workers
        available.
        """
        # log.debug('feeding q {}'.format(len(self._workers)))
        i = 1
        while (len(self._workers) < self._max_workers) and (
            len(self.server.queue.queued_jobs) > 0
        ):

            # while there is work to do and workers available, start up new jobs
            job_was_submitted, job = self.submit_one_job()

            if job_was_submitted:
                time.sleep(self.feed_delay)
            else:
                break

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
        with self.w_lock:
            for job_id, (work_item, p) in self._workers.items():
                if (job_id_to_kill == job_id) or kill_all:
                    print(f"killing running job {job_id}")

                    # first kill the child processes
                    for child_proc in psutil.Process(p.pid).children(recursive=True):
                        child_proc.terminate()
                    # now kill the python process
                    p.terminate()

                    work_item.future._state = cf._base.CANCELLED
                    self._workers.pop(job_id)
                    self._results.pop(job_id)
                    return True

        for work_item in self._queue:
            if job_id_to_kill == work_item.job.job_id or kill_all:
                print(f"killing queued job {work_item.job.job_id}")
                work_item.future._state = cf._base.CANCELLED
                self._queue.remove(work_item)
                self._results.pop(work_item.job.job_id)
                return True

        # print(f'job not found {job_id_to_kill}')
        return False

    def _runloop(self):
        """
        This is the loop that manages getting job completetions, taking care of the sub-processes
         and keeping the queue moving
        """
        while True:

            self.process_completions()

            if self.__abort:
                return

    def join(self, timeout=None):
        """
        Blocks until all jobs are complete
        Parameters
        ----------
        timeout: int
            optional time value
        """
        self.log.debug("waiting to join")
        value = ""
        while value != "empty":
            value = self.__signal_queue.get(timeout=timeout)
            self.log.debug("join received signal: {}".format(value))

    def shutdown(self, wait=True):
        """
        Shuts down the pool.

        Parameters
        ----------
        wait: bool
            If True, wait until all jobs are complete, then shutdown.
            If False then kill the processes and shutdown immediately
        """
        if wait:
            self.join()
            self.__abort = True
        else:
            self.__abort = True
            for job_id, (work_item, p) in self._workers.items():
                p.terminate()

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
