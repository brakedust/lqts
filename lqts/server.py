import os
import logging
from functools import partial
from typing import List
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from starlette.responses import RedirectResponse
import ujson

from lqts.schema import Job, JobQueue, JobSpec, JobStatus, JobID
from lqts.mp_pool import DynamicProcessPool, Event, DEFAULT_WORKERS
from lqts.job_runner import run_command
from lqts.config import Configuration
from lqts.version import VERSION


class Application(FastAPI):
    """
    LoQuTuS Job Scheduling Server
    """

    config: object = None

    def __init__(self):
        super().__init__()

        if Path(".env").exists():
            self.config = Configuration.load_env_file(".env")
        else:
            self.config = Configuration()

        self._setup_logging(None)
        self.queue = JobQueue(
            name="default_queue",
            queue_file=self.config.queue_file,
            completed_limit=self.config.completed_limit,
            config=self.config
        )

        self.queue._start_manager_thread()
        self.queue.log = self.log

        self.log.info(f"Starting up LoQuTuS server - {VERSION}")

        self.pool = None
        self.__start_workers(self.config.nworkers)

        self.log.info(f"Visit {self.config.url}/qstatus to view the queue status")

        if self.config.resume_on_start_up and Path(self.config.queue_file).exists():
            self.log.info("Attempting to resume queue")
            self.queue.load()

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
            queue=self.queue, max_workers=nworkers, feed_delay=0.05
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

        self.log = getLogger("lqts", Level.INFO)

    # def job_started_handler(self, job: Job):

    #     self.queue.on_job_started(job.job_id)
    #     self.log.info(f">>> Started     job {job.job_id} at {job.started.isoformat()}")

    # def job_done_handler(self, job: Job):

    #     self.queue.on_job_finished(job)
    #     self.log.info(
    #         f"--- Completed   job {job.job_id} at {job.completed.isoformat()}"
    #     )

app = Application()
app.debug = True


@app.get("/")
async def root():
    from lqts.html.render_qstat import render_qstat_page
    from starlette.responses import HTMLResponse

    # complete = complete == "yes"
    return HTMLResponse(render_qstat_page(False))


@app.get("/qstat")
async def get_queue_status(options: dict):
    # print(options)
    queue_status = []

    if options.get("running", True):
        for job in list(app.queue.running_jobs.values()):
            queue_status.append(job.json())

    if options.get("queued", True):
        for job in list(app.queue.queued_jobs.values()):
            queue_status.append(job.json())

    if options.get("completed", False):
        queue_status.extend(
            [job.json() for jid, job in list(app.queue.completed_jobs.items())]
        )

    return queue_status


@app.post("/qsub")
async def qsub(job_specs: List[JobSpec]):
    # print(f"Submitted job specs {job_specs}")
    return app.queue.submit(job_specs)


@app.on_event("shutdown")
async def on_shutdown():
    app.pool.shutdown(wait=False)
    app.queue.shutdown()


@app.get("/qsummary")
async def get_summary():
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
        "Queued": len(app.queue.queued_jobs),
    }
    # for letter in "RQDC":
    #     if letter not in c:
    #         c[letter] = 0

    return summary


@app.get("/workers")
async def get_workers():
    """
    Gets the number of worker processes to execute jobs.
    """
    app.log.info(
        "Number of workers queried by user. Returned {}".format(app.pool._max_workers)
    )
    return app.pool._max_workers


@app.post("/workers")
async def set_workers(count: int=4):
    """
    Sets the number of worker processes to execute jobs.
    """
    app.log.info("Setting maximum number of workers to {}".format(count))
    app.pool.resize(count)
    return app.pool._max_workers


@app.get("/jobgroup")
async def get_job_group(group_number: int):

    return list(app.queue.job_groups[group_number].jobs.keys())


@app.post("/qclear")
async def clear_queue(really: bool):
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
async def qdel(job_ids: List[JobID]):
    """
    Delete on or more jobs
    """

    deleted_jobs = app.queue.qdel(job_ids)

    for job_id in deleted_jobs:
        if job_id in app.pool._workers:
            app.pool.kill_job(job_id)

    return {"Deleted jobs": deleted_jobs}


@app.post("/qpriority")
async def qpriority(priority: int, job_ids: List[JobID]):
    app.log.info(f"Setting priority of jobs {job_ids} to {priority}")
    for job_id in job_ids:
        job, _ = app.queue.find_job(job_id)
        try:
            job.job_spec.priority = priority
        except:
            import traceback
            traceback.print_exc()


@app.get("/qstatus")
async def qstat_html(complete="no"):
    from lqts.html.render_qstat import render_qstat_page
    from starlette.responses import HTMLResponse

    complete = complete == "yes"
    return HTMLResponse(render_qstat_page(complete))


@app.get("/job_request")
async def job_request():

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
async def job_done(done_job: Job):
    app.queue.on_job_finished(done_job)
    # job: Job = app.queue.running_jobs.pop(done_job.job_id)
    # job.status = JobStatus.Completed
    # job.completed = done_job.completed

    # app.queue.completed_jobs.append(job)


@app.post("/job_started")
async def job_started():
    pass
