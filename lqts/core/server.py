
from pathlib import Path

from fastapi import FastAPI

from lqts.core.schema import JobQueue
from lqts.mp_pool2 import DynamicProcessPool, DEFAULT_WORKERS
# from lqts.job_runner import run_command
from lqts.core.config import Configuration
from lqts.version import VERSION


class Application(FastAPI):
    """
    LoQuTuS Job Scheduling Server
    """

    config: Configuration = None

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
            config=self.config,
        )

        self.queue._start_manager_thread()
        # self.queue.log = self.log

        self.log.info(f"Starting up LoQuTuS server - {VERSION}")

        self.pool = None
        self.__start_workers(self.config.nworkers)

        self.log.info(f"Visit {self.config.url}/qstatus to view the queue status")

        if self.config.resume_on_start_up and Path(self.config.queue_file).exists():
            self.log.info("Attempting to resume queue")
            self.queue.load()

        self.debug = self.config.debug

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
            queue=self.queue, max_workers=nworkers, feed_delay=0.05, manager_delay=2.0
        )
        self.pool._start_manager_thread()
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
        if self.debug:
            self.log = getLogger("lqts", Level.DEBUG)
        else:
            self.log = getLogger("lqts", Level.INFO)


app = None


def get_app():
    global app
    if app is None:
        app = Application()
    return app
