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
import datetime

# import logging
import multiprocessing as mp
import queue
import threading
import time
from collections import deque

import psutil


DEFAULT_WORKERS = max(mp.cpu_count() - 2, 1)


class _WorkItem(object):
    def __init__(self, job_id, future, fn, args, kwargs):
        self.job_id = job_id
        self.future = future
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.start_time = None
        self.stop_time = None

        # class _ResultItem(object):
        #     def __init__(self, work_id, exception=None, result=None):
        #         self.work_id = work_id
        #         self.exception = exception
        #         self.result = result
        #
        #
        # class _CallItem(object):
        #     def __init__(self, work_id, fn, args, kwargs):
        #         self.work_id = work_id
        #         self.fn = fn
        #         self.args = args
        self.kwargs = kwargs


def mp_worker_func(q_in: mp.Queue, q_out: mp.Queue):

    job_id, func, args, kwargs = q_in.get()
    # future._state = cf._base.RUNNING
    # func = future.func
    # args = future.args

    result = func(*args, **kwargs)
    # future.set_result(result)
    stop_time = datetime.datetime.now().isoformat()
    # future._state = cf._base.FINISHED
    q_out.put((job_id, result, stop_time))


# def mp_worker_func2(q_in: mp.Queue, q_out: mp.Queue):
#
#     while True:
#         future = q_in.get()
#         future._state = cf._base.RUNNING
#         func = future.func
#         args = future.args
#
#         result = func(*args)
#         future.set_result(result)
#
#         future._state = cf._base.FINISHED
#         q_out.put(future)


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

    def __init__(self, max_workers=DEFAULT_WORKERS, feed_delay=0.05):

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

    def submit(self, func, args=None, kwargs=None, job_id=None):

        self.q_count += 1
        # f = MyFuture(func, args, job_id, call_back=call_back)
        future = cf.Future()
        if job_id is None:
            job_id = self.q_count

        if args is None:
            args = tuple()

        if kwargs is None:
            kwargs = {}

        work_item = _WorkItem(job_id, future, func, args, kwargs)

        with self.q_lock:
            self.log.debug("Submitting {}".format(job_id))
            self._queue.append(work_item)
            self._results[job_id] = work_item
        # self.feed_queue()

        return future

    submit.__doc__ = cf._base.Executor.submit.__doc__

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
        try:
            # see if any results are available
            job_id, result, stop_time = self.q_output.get(timeout=timeout)
            self.log.debug("Got result {} = {}".format(job_id, result, stop_time))

            work_item = self._results.pop(job_id)

            # call backs to notify external things that we are done.
            for callback in self._event_callbacks:
                event = {
                    "job_id": work_item.job_id,
                    "event_type": "completed",
                    "data": stop_time,
                }
                callback(event)

            future = work_item.future
            future.set_result(result)  # this is where callbacks get triggered

            # If the queues are empty send a signal saying we are empty
            if len(self._results) == 0 and len(self._queue) == 0:
                self.__signal_queue.put("empty")

        except queue.Empty:
            pass

        # Remove any processes that are complete
        for work_item, w in tuple(self._workers.items()):
            if not w.is_alive():
                with self.w_lock:
                    self._workers.pop(work_item)

        # make sure to feed the queue to keep work going
        self.feed_queue()

    def feed_queue(self):
        """
        Starts up jobs while there are jobs in the queue and there are workers
        available.
        """
        # log.debug('feeding q {}'.format(len(self._workers)))
        i = 1
        while (len(self._workers) < self._max_workers) and (len(self._queue) > 0):

            # while there is work to do and workers available, start up new jobs
            work_item = self._queue.popleft()

            future = work_item.future

            if not future._state == cf._base.PENDING:
                continue

            future._state = cf._base.RUNNING
            self.log.debug("Spawning {}".format(future))
            self.q_input.put(
                (work_item.job_id, work_item.fn, work_item.args, work_item.kwargs)
            )
            # self._result_queue[job_id] = future

            p = mp.Process(target=mp_worker_func, args=(self.q_input, self.q_output))
            p.start()

            with self.w_lock:
                # self.active_jobs[job_id] = p.pid()
                self._workers[work_item] = p
                # time.sleep(0.2)

            for callback in self._event_callbacks:
                event = {
                    "job_id": work_item.job_id,
                    "event_type": "started",
                    "data": datetime.datetime.now().isoformat(),
                }
                callback(event)

            this_delay = min((self.feed_delay * (1 + 0.5 * i), 5 * self.feed_delay))
            time.sleep(this_delay)
            i += 1

    def kill_job(self, job_id_to_kill):
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
            for work_item, p in self._workers.items():
                if job_id_to_kill == work_item.job_id:
                    print(f"killing running job {job_id_to_kill}")

                    # first kill the child processes
                    for child_proc in psutil.Process(p.pid).children(recursive=True):
                        child_proc.terminate()
                    # now kill the python process
                    p.terminate()

                    work_item.future._state = cf._base.CANCELLED
                    self._workers.pop(work_item)
                    self._results.pop(work_item.job_id)
                    return True

        for work_item in self._queue:
            if job_id_to_kill == work_item.job_id:
                print(f"killing queued job {job_id_to_kill}")
                work_item.future._state = cf._base.CANCELLED
                self._queue.remove(work_item)
                self._results.pop(work_item.job_id)
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
            for future, p in self._workers.items():
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
