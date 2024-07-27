from contextlib import asynccontextmanager

from fastapi import FastAPI

# from lqts.job_runner import run_command
from lqts.core.config import Configuration, config
from lqts.core.schema import JobQueue
from lqts.mp_pool2 import DEFAULT_WORKERS, DynamicProcessPool
from lqts.simple_logging import Level, getLogger
from lqts.version import VERSION


class Application(FastAPI):
    """
    LoQuTuS Job Scheduling Server
    """

    def __init__(self, lifespan):
        super().__init__(lifespan=lifespan)

        self._configure()

        self._setup_logging(None)

        self._start_queue()

        self._start_worker_pool(self.config.nworkers)

        self.log.info(f"Visit {self.config.url}/qstatus to view the queue status")

    def _configure(self):
        self.config: Configuration = config
        self.debug = self.config.debug

    def _setup_logging(self, log_file: str):
        """
        Sets up logging.  A console and file logger are used.  The _DEGBUG flag on
        the SQServer instance controls the log level

        Parameters
        ----------
        log_file: str
        """
        if self.debug:
            self.log = getLogger("loqutus", Level.DEBUG)
        else:
            self.log = getLogger("loqutus", Level.INFO)

    def _start_queue(self):
        self.queue = JobQueue(
            name="default_queue",
            queue_file=self.config.queue_file,
            completed_limit=self.config.completed_limit,
            config=self.config,
        )
        self.queue.load()
        self.queue.start()
        self.log.info(f"Starting up LoQuTuS server - {VERSION}")

    def _start_worker_pool(self, nworkers: int = DEFAULT_WORKERS):
        """Starts the worker pool

        Parameters
        ----------
        nworkers: int
            number of workers
        """
        self.pool = DynamicProcessPool(
            queue=self.queue, max_workers=self.config.nworkers, feed_delay=0.05, manager_delay=2.0
        )
        self.pool.start()
        self.log.info("Worker pool started with {} workers.".format(nworkers))
        self.log.info(f"Total number of CPUs available is {self.pool.CPUManager._system_cpu_count}.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    pass
    yield
    print("Shutting down loqutus server")
    app.pool.shutdown(wait=False)
    app.queue.shutdown()


app = None


def get_app():
    global app
    if app is None:
        app = Application()
    return app
