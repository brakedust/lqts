import os
import logging
from functools import partial
from typing import List
from collections import defaultdict, Counter
from datetime import datetime

from fastapi import FastAPI
import ujson

from .schema import Configuration, Job, JobQueue, JobSpec, JobStatus, JobID, DEFAULT_CONFIG
from .mp_pool import DynamicProcessPool, Event, DEFAULT_WORKERS
from .job_runner import run_command


class Application(FastAPI):
    """
    LoQuTuS Job Scheduling Server
    """

    def __init__(self):
        super().__init__()

        self.config = Configuration()

        # if os.path.exists(DEFAULT_CONFIG.queue_file):
        #     import yaml
        #     with open(DEFAULT_CONFIG.queue_file) as fid:
        #         data = yaml.full_load(fid.read())
        #     self.queue = JobQueue(**data)
        # else:
        self.queue = JobQueue()
        if os.path.exists(DEFAULT_CONFIG.queue_file):
            self.queue.load()

        self.queue._start_manager_thread()



        self.dependencies = defaultdict(list)

        self.config.log_file = None

        self._setup_logging(self.config.log_file)
        self.log.info("Starting up LoQuTuS server.")

        self.pool = None
        self.__start_workers()


        self.log.info(f"Visit {self.config.url} to view the queue status")

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
        self.pool = DynamicProcessPool(server=self, max_workers=nworkers, feed_delay=0)
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
        fmt = "%(asctime)s %(levelname)s | %(message)s"
        logging.basicConfig(format=fmt)
        self.log = logging.getLogger("uvicorn")
        self.log.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            fmt   # "%(asctime)s %(levelname)s " + "[%(module)s:%(lineno)d] %(message)s"
        )

        if log_file:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file, backupCount=2, maxBytes=5 * 1024 * 1024
            )  # 5 megabytes
            if self._debug:
                file_handler.setLevel(logging.DEBUG)
            else:
                file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            self.log.addHandler(file_handler)

    def get_job_by_id(self, job_id: JobID) -> Job:
        """
        Looks for a job in the queue with the given job id

        Parameters
        ----------
        job_id
            The id for the requested job

        Returns
        -------
        job
            dict containing details about the job
        """
        if job_id in self.queue.running_jobs:
            return self.queue.running_jobs[job_id]
        elif job_id in self.queue.queued_jobs:
            return self.queue.queued_jobs[job_id]
        else:
            for job in self.queue.completed_jobs:
                if job.job_id == job_id:
                    return job
        return None

    def job_started_handler(self, job: Job):
        # job = self.queue.queued_jobs.pop(job.job_id)
        # self.queue.running_jobs[job.job_id] = job
        # job.status = JobStatus.Running
        # job.started = datetime.now()
        self.queue.on_job_started(job.job_id)
        self.log.info(f"--- Started    job {job.job_id} at {job.started.isoformat()}")

    def job_done_handler(self, job: Job):
        # job = self.queue.running_jobs.pop(job.job_id)
        # job.status = JobStatus.Completed
        # job.completed = datetime.now()
        # self.queue.completed_jobs.append(job)
        self.queue.on_job_finished(job.job_id)
        self.log.info(f"--- Completed   job {job.job_id} at {job.completed.isoformat()}")
        # print("# Running jobs = ", len(self.queue.running_jobs))

        # if job.job_id in self.dependencies:

        #     for dependent in self.dependencies[job.job_id]:
        #         waiting_job: Job = self.get_job_by_id(dependent)
        #         waiting_job.job_spec.depends.remove(job.job_id)
        #         waiting_job.completed_depends.append(job.job_id)
        #         if len(waiting_job.job_spec.depends) == 0:

        #             self.log.info(
        #                 ">>> Dependencies for job {} now complete".format(
        #                     waiting_job.job_id
        #                 )
        #             )
        #     self.dependencies.pop(job.job_id)

    # def check_can_job_run(self, job_id: JobID):

    #     job = self.get_job_by_id(job_id)
    #     dependencies: List[Job] = [self.get_job_by_id(id_) for id_ in job.job_spec.depends]

    #     dependencies = [d for d in dependencies if d is not None]

    #     if not dependencies:
    #         return True

    #     DEBUG = False
    #     # print(dependencies)
    #     running_deps = [d.job_id for d in dependencies if (d.job_id in self.queue.running_jobs)]
    #     if running_deps:
    #         if DEBUG:
    #             print(f'>w<{job.job_id} waiting on running jobs: {running_deps}')
    #         return False

    #     queued_deps = [d.job_id for d in dependencies if (d.job_id in self.queue.queued_jobs)]
    #     if queued_deps:
    #         if DEBUG:
    #             print(f'>w<{job.job_id} Waiting on queued jobs: {queued_deps}')
    #         print(self.queue.queued_jobs)
    #         return False

    #     return True

    def queue_empty(self):

        return any(not job.is_done() for job in self.queue.jobs)

    def submit_jobs(self, job_specs: List[JobSpec]):

        job_ids = []
        group = self.queue.current_group
        self.queue.current_group += 1
        for i, job_spec in enumerate(job_specs):
            job_id = JobID(group=group, index=i)
            job = self.queue.submit(job_spec, job_id=job_id)
            # if job_spec.depends:

            #     for dep in job_spec.depends:
            #         dep_job_id = JobID.parse_obj(dep)
            #         dep_job = self.get_job_by_id(dep_job_id)
            #         if dep_job.status not in (JobStatus.Completed, JobStatus.Deleted):
            #             self.dependencies[dep_job_id].append(job.job_id)

            job_ids.append(str(job.job_id))
            self.log.info(
                f"+++ Assimilated job {job.job_id} at {job.submitted.isoformat()} - {job.job_spec.command}"
            )
            # self.log.info(f"Job dependencies for {job.job_id}: {[job.job_spec.depends]}")

            # self.pool.submit(partial(run_command, job), job)

        return job_ids


app = Application()
app.debug = True
# app.mount('/static', StaticFiles(directory="static"))


# def fake_job():
#     j = JobSpec(command="echo hello", working_dir=os.getcwd())
#     return j

# app.queue.submit(fake_job())
# app.queue.submit(fake_job())
# app.queue.submit(fake_job())


@app.get("/")
def root():
    return "Hello, world!"


@app.get("/qstat")
def get_queue(options: dict):
    # print(options)
    queue_status = []

    # print("qstat 1")
    for jid, job in app.queue.running_jobs.items():
        # print(jid)
        # print(job)
        # print()
        queue_status.append(job.json())

    # print("qstat 2")
    for jid, job in app.queue.queued_jobs.items():
        queue_status.append(job.json())

    if options.get('completed', False):
        queue_status.extend([job.json() for jid, job in app.queue.completed_jobs.items()])
    # print("qstat 3")

    return queue_status  #[j.json() for j in app.queue.running_jobs.values()] + [j.json() for j in app.queue.queued_jobs.value()]


@app.post("/qsub")
def qsub(job_specs: List[JobSpec]):
    # print(f"Submitted job specs {job_specs}")
    return app.submit_jobs(job_specs)


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
    c = Counter([job.status.value for job in app.queue.jobs])
    for letter in "IRQDC":
        if letter not in c:
            c[letter] = 0

    return c


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
    for jid in list(job_ids):
        if jid.index is None:
            job_ids.remove(jid)
            job_ids.extend(j.job_id for j in app.queue.get_job_group(jid.group))
        # else:
        #     job_ids.append(jid)

    deleted_jobs = []
    for job_id in job_ids:
        # job_id = JobID.parse_obj(jid)
        # job = app.queue.find_job(job_id)

        should_delete = False
        if job_id in app.queue.running_jobs:
            app.pool.kill_job(job_id)
            should_delete = True

        elif job in app.queue.queued_jobs:
            should_delete = True

        if should_delete:
            job.status = JobStatus.Deleted
            job.completed = datetime.now()
            app.queue.completed_jobs.append(job)
            deleted_jobs.append(job_id)

    dead_jobs = [str(jid) for jid in deleted_jobs]
    return {"Deleted jobs": dead_jobs}


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

    job: Job = app.queue.running_jobs.pop(done_job.job_id)
    job.status = JobStatus.Completed
    job.completed = done_job.completed

    app.queue.completed_jobs.append(job)


@app.post("/job_started")
def job_started():
    pass
