import os
import logging
from functools import partial
from typing import List
from collections import defaultdict, Counter
from datetime import datetime

from fastapi import FastAPI
import ujson

from lqts.schema import Job, JobQueue, JobSpec, JobStatus, JobID
from lqts.mp_pool import DynamicProcessPool, Event, DEFAULT_WORKERS
from lqts.job_runner import run_command
from lqts.config import DEFAULT_CONFIG, Configuration


class Application(FastAPI):
    """
    LoQuTuS Job Scheduling Server
    """

    config: object = None

    def __init__(self):
        super().__init__()

        # self.config.log_file = None

        self.config = Configuration()

        # if os.path.exists(DEFAULT_CONFIG.queue_file):
        #     import yaml
        #     with open(DEFAULT_CONFIG.queue_file) as fid:
        #         data = yaml.full_load(fid.read())
        #     self.queue = JobQueue(**data)
        # else:

        self._setup_logging(None)
        self.queue = JobQueue(
            name="default_queue",
            queue_file=DEFAULT_CONFIG.queue_file,
            completed_limit=DEFAULT_CONFIG.completed_limit,
        )
        # self.queue.load()
        self.queue._start_manager_thread()
        self.queue.log = self.log
        # if os.path.exists(DEFAULT_CONFIG.queue_file):
        # self.queue.queue_file = DEFAULT_CONFIG.queue_file

        # self.dependencies = defaultdict(list)


        self.log.info("Starting up LoQuTuS server.")

        self.pool = None
        self.__start_workers()

        self.log.info(f"Visit {self.config.url}/qstatus to view the queue status")

    def __start_workers(self, nworkers: int = DEFAULT_WORKERS):
        """Starts the worker pool

        Parameters
        ----------
        nworkers: int
            number of workers
        """
        # if nworkers is None:
        #     nworkers = self.config.nworkers

        # self.pool = cf.ProcessPoolExecutor(max_workers=nworkers)
        self.pool = DynamicProcessPool(
            server=self, max_workers=nworkers, feed_delay=0.05
        )
        # self.pool.add_event_callback(self.receive_pool_events)
        self.log.info("Worker pool started with {} workers".format(nworkers))

    def _setup_logging(self, log_file: str):
        """
        Sets up logging.  A console and file logger are used.  The _DEGBUG flag on
        the SQServer instance controls the log level

        Parameters
        ----------
        log_file: str
        """
        from lqts.simple_logging import getLogger, Level

        self.log = getLogger('lqts', Level.INFO)
        # self.log = logging.getLogger("lqts")

        # fmt = "%(asctime)s | %(levelname)s | %(message)s"
        # formatter = logging.Formatter(
        #     fmt  # "%(asctime)s %(levelname)s " + "[%(module)s:%(lineno)d] %(message)s"
        # )
        # logging.basicConfig(format='')

        # # self.log.setLevel(logging.DEBUG)

        # for h in self.log.handlers:
        #     self.log.removeHandler(h)

        # handler = logging.StreamHandler()
        # handler.setFormatter(formatter)
        # self.log.addHandler(handler)
        # # self.log.setFormatter(fmt)
        # self.log.setLevel(logging.DEBUG)


        # if log_file:
        #     file_handler = logging.handlers.RotatingFileHandler(
        #         log_file, backupCount=2, maxBytes=5 * 1024 * 1024
        #     )  # 5 megabytes
        #     if self._debug:
        #         file_handler.setLevel(logging.DEBUG)
        #     else:
        #         file_handler.setLevel(logging.INFO)
        #     file_handler.setFormatter(formatter)
        #     self.log.addHandler(file_handler)

    def job_started_handler(self, job: Job):

        self.queue.on_job_started(job.job_id)
        self.log.info(f">>> Started     job {job.job_id} at {job.started.isoformat()}")

    def job_done_handler(self, job: Job):

        self.queue.on_job_finished(job)
        self.log.info(
            f"--- Completed   job {job.job_id} at {job.completed.isoformat()}"
        )


app = Application()
app.debug = True


@app.get("/")
def root():
    return "Hello, world!"


@app.get("/qstat")
def get_queue_status(options: dict):
    # print(options)
    queue_status = []

    if options.get('running', True):
        for job in list(app.queue.running_jobs.values()):
            queue_status.append(job.json())

    if options.get('queued', True):
        for job in list(app.queue.queued_jobs.values()):
            queue_status.append(job.json())

    if options.get("completed", False):
        queue_status.extend(
            [job.json() for jid, job in list(app.queue.completed_jobs.items())]
        )

    return (
        queue_status
    )


@app.post("/qsub")
def qsub(job_specs: List[JobSpec]):
    # print(f"Submitted job specs {job_specs}")
    return app.queue.submit(job_specs)


@app.on_event("shutdown")
def on_shutdown():
    app.pool.shutdown(wait=False)
    app.queue.shutdown()


@app.get("/qsummary")
def get_summary():
    """
    Gets a summary of what the state of the queue is.
    * I = Initialized
    * Q = Queued
    * R = Running
    * D = Deleted
    * C = completed
    """
    # c = Counter([job.status.value for job in app.queue.jobs])
    summary = {
        "Running": len(app.queue.running_jobs),
        "Queued": len(app.queue.queued_jobs)
    }
    # for letter in "RQDC":
    #     if letter not in c:
    #         c[letter] = 0

    return summary


@app.get("/workers")
def get_workers():
    """
    Gets the number of worker processes to execute jobs.
    """
    app.log.info(
        "Number of workers queried by user. Returned {}".format(app.pool._max_workers)
    )
    return app.pool._max_workers


@app.post("/workers")
def set_workers(count: int):
    """
    Sets the number of worker processes to execute jobs.
    """
    app.log.info("Setting maximum number of workers to {}".format(count))
    app.pool.resize(count)
    return app.pool._max_workers


@app.get("/jobgroup")
def get_job_group(group_number: int):

    return list(app.queue.job_groups[group_number].jobs.keys())


@app.post("/qclear")
def clear_queue(really: bool):
    """
    Kills running jobs and totally erases the queue.
    """
    if really:
        app.pool.kill_job(None, True)
        app.queue.jobs.clear()
        return "Killed running jobs and cleared queue"
    else:
        return "You must specify really=true to actually kill the jobs"


@app.post("/qdel")
def qdel(job_ids: List[JobID]):
    """
    Delete on or more jobs
    """

    deleted_jobs = app.queue.qdel(job_ids)

    for job_id in deleted_jobs:
        if job_id in app.pool._workers:
            app.pool.kill_job(job_id)

    return {"Deleted jobs": deleted_jobs}

@app.post("/qpriority")
def qpriority(job_ids: List[JobID], priority: int):

    for job_id in job_ids:
        job, _ = app.queue.find_job(job_id)
        job.job_spec.priority = priority


@app.get("/qstatus")
def qstat_html(complete="no"):
    from lqts.html.render_qstat import render_qstat_page
    from starlette.responses import HTMLResponse

    complete = complete == "yes"
    return HTMLResponse(render_qstat_page(complete))


@app.get("/job_request")
def job_request():

    job = app.queue.queued_jobs.pop()
    if job is None:
        return "{}"
    else:
        job.started = datetime.now()
        job.status = JobStatus.Running
        app.queue.running_jobs[job.job_id] = job
        app.log.info("  +Started job {} at {}".format(job.job_id, job.started))
        return job


@app.post("/job_done")
def job_done(done_job: Job):
    app.queue.on_job_finished(done_job)
    # job: Job = app.queue.running_jobs.pop(done_job.job_id)
    # job.status = JobStatus.Completed
    # job.completed = done_job.completed

    # app.queue.completed_jobs.append(job)


@app.post("/job_started")
def job_started():
    pass
