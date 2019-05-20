import os
import logging
from functools import partial

from fastapi import FastAPI

from .schema import Configuration, Job, JobQueue, JobSpec, JobStatus, JobID
from .mp_pool import DynamicProcessPool, Event, DEFAULT_WORKERS
from .job_runner import run_command

class Application(FastAPI):

    def __init__(self):
        super().__init__()

        self.config = Configuration()
        self.queue = JobQueue()

        self.dependencies = {}

        self.config.log_file = None

        self._setup_logging(self.config.log_file)

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
        
        logging.basicConfig(format="%(asctime)s %(levelname)s " + "[%(module)s:%(lineno)d] %(message)s")
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
        # job = event.job
        job = self.get_job_by_id(event.job.job_id)
        job.completed = event.job.completed
        # print(job.completed)
        job.walltime = event.job.walltime
        job.status = event.job.status

        

        # print("job is job2 = ", job is job2)
        if event.event_type == "started" and len(self.queue.jobs) > 0:
            self.log.info(
                "+Started job {} at {}".format(job.job_id, job.started)
            )

        elif event.event_type == "completed" and len(self.queue.jobs) > 0:
            self.log.info(
                "-Finished job {} at {}".format(job.job_id, job.completed)
            )

            if job.job_id in self.dependencies:
                waiting_job = self.get_job_by_id(self.dependencies[job.job_id])
                waiting_job.can_run = True
                self.dependencies.pop(job.job_id)
                self.log.info(
                    ">>> Dependency for job {} now complete".format(waiting_job.job_id) #, job.job_id, job.completed)
                )

    def queue_empty(self):

        return any(not job.is_done() for job in self.queue.jobs)


            # self.queue.prune()

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
def qsub(job_spec: JobSpec):

    job = app.queue.submit(job_spec)
    if (job_spec.depend_on):
        job.can_run = False
        app.dependencies[JobID.parse(job_spec.depend_on)] = job.job_id

    app.pool.submit(partial(run_command, job), job)
    return str(job.job_id)


@app.on_event("shutdown")
def on_shutdown():
    app.pool.shutdown(wait=False)

@app.post('/shutdown')
def shutdown():
    app.pool.shutdown(wait=False)
    raise KeyboardInterrupt()

@app.get('/qsummary')
def get_summary():
    from collections import Counter
    c = Counter([job.status.value for job in app.queue.jobs])
    for letter in 'IRQDC':
        if letter not in c:
            c[letter] = 0

    return c

@app.get('/workers')
def get_workers():
    app.log.info(
        "Number of workers queried by user. Returned {}".format(app.pool._max_workers)
    )
    return app.pool._max_workers

@app.post('/workers')
def set_workers(count: int):
    
    app.log.info(
        "Setting maximum number of workers to {}".format(count)
    )
    app.pool.resize(count)
    return app.pool._max_workers


