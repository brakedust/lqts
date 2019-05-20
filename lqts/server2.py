import os
import logging
from functools import partial
from typing import List
from collections import defaultdict, Counter

from fastapi import FastAPI

from .schema import Configuration, Job, JobQueue, JobSpec, JobStatus, JobID
from .mp_pool import DynamicProcessPool, Event, DEFAULT_WORKERS
from .job_runner import run_command

class Application(FastAPI):
    """
    LoQuTuS Job Scheduling Server
    """
    def __init__(self):
        super().__init__()

        self.config = Configuration()
        self.queue = JobQueue()

        self.dependencies = defaultdict(list)

        self.config.log_file = None

        self._setup_logging(self.config.log_file)
        self.log.info('Starting up LoQuTuS server.')

        self.pool = None
        self.__start_workers()

    def __start_workers(self, nworkers: int=DEFAULT_WORKERS):
        """Starts the worker pool

        Parameters
        ----------
        nworkers: int
            number of workers
        """
        # if nworkers is None:
        #     nworkers = self.config.nworkers

        # self.pool = cf.ProcessPoolExecutor(max_workers=nworkers)
        self.pool = DynamicProcessPool(max_workers=nworkers, feed_delay=0)
        self.pool.add_event_callback(self.receive_pool_events)
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
            "%(asctime)s %(levelname)s " + "[%(module)s:%(lineno)d] %(message)s"
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

        for job in self.queue.jobs:
            if job.job_id == job_id:
                return job

    def receive_pool_events(self, event: Event):
        """
        The sqs.mp_pool.DynamicProcessPool sends some events when jobs start
        and stop.  The method is registered as a callback to receive these
        events.

        Parameters
        ----------
        event: dict
            dict containing the data from the event
        """

        job = self.get_job_by_id(event.job.job_id)
        job.status = event.job.status

        # print("job is job2 = ", job is job2)
        if event.event_type == "started" and len(self.queue.jobs) > 0:
            job.started = event.job.started
            self.log.info(
                "  +Started job {} at {}".format(job.job_id, job.started)
            )

        elif event.event_type == "completed" and len(self.queue.jobs) > 0:
            job.completed = event.job.completed
            self.log.info(
                "  -Finished job {} at {}".format(job.job_id, job.completed)
            )

            if job.job_id in self.dependencies:
                for dependent in self.dependencies[job.job_id]:
                    waiting_job: Job = self.get_job_by_id(dependent)
                    waiting_job.spec.depends.remove(job.job_id)
                    if len(waiting_job.spec.depends) == 0:
                        waiting_job.can_run = True
                        self.dependencies.pop(job.job_id)
                        self.log.info(
                            ">>> Dependencies for job {} now complete".format(waiting_job.job_id) #, job.job_id, job.completed)
                        )

    def queue_empty(self):

        return any(not job.is_done() for job in self.queue.jobs)

    async def submit_jobs(self, job_specs: List[JobSpec]):

        job_ids = []
        group = self.queue.current_index
        self.queue.current_index += 1
        for i, job_spec in enumerate(job_specs):
            job_id = JobID(group=group, index=i)
            job = self.queue.submit(job_spec, job_id=job_id)
            if (job_spec.depends):

                for dep in job_spec.depends:
                    dep_job_id = JobID.parse(dep)
                    dep_job = self.get_job_by_id(dep_job_id)
                    if dep_job.status not in (JobStatus.Completed, JobStatus.Deleted):
                        self.dependencies[dep_job_id].append(job.job_id)

            job_ids.append(str(job.job_id))
            self.log.info(
                "+++Assimilated job {} at {} - {}".format(job.job_id, job.submitted, job.job_spec.command)
            )

            self.pool.submit(partial(run_command, job), job)

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


@app.get('/')
def root():
    return 'Hello, world!'


@app.get("/qstat")
def get_queue():
    return [j.json() for j in app.queue.jobs]


@app.post("/qsub")
async def qsub(job_specs: List[JobSpec]):

    return await app.submit_jobs(job_specs)


@app.on_event("shutdown")
def on_shutdown():
    app.pool.shutdown(wait=False)


@app.get('/qsummary')
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
    for letter in 'IRQDC':
        if letter not in c:
            c[letter] = 0

    return c


@app.get('/workers')
def get_workers():
    """
    Gets the number of worker processes to execute jobs.
    """
    app.log.info(
        "Number of workers queried by user. Returned {}".format(app.pool._max_workers)
    )
    return app.pool._max_workers


@app.post('/workers')
def set_workers(count: int):
    """
    Sets the number of worker processes to execute jobs.
    """
    app.log.info(
        "Setting maximum number of workers to {}".format(count)
    )
    app.pool.resize(count)
    return app.pool._max_workers


@app.post('/qclear')
def clear_queue(really: bool):
    """
    Kills running jobs and totally erases the queue.
    """
    if really:
        app.pool.kill_job(None, True)
        app.queue.jobs.clear()
        return 'Killed running jobs and cleared queue'
    else:
        return 'You must specify really=true to actually kill the jobs'

@app.post('/qdel')
def qdel(job_ids:List[JobID]):
    """
    Delete on or more jobs
    """
    deleted_jobs = []
    for jid in job_ids:
        job_id = JobID.parse(jid)
        app.pool.kill_job(job_id)
        job = app.get_job_by_id(job_id)
        job.status = JobStatus.Deleted
        deleted_jobs.append(job_id)

    return f"Deleted jobs {ujson.dumps(deleted_jobs)}"
