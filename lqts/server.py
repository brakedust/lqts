# -*- coding: utf-8 -*-
"""
server Module
================

Provides the SQServer class.
"""
import asyncio
import json
import logging
import logging.handlers
from os.path import join, expanduser
from collections import deque
from multiprocessing import cpu_count

from .exceptions import SQSShutdownException
from .messages import MessageDispatcher
from .version import VERSION
from .mp_pool import DynamicProcessPool
from .config import Configuration

# VERSION = GitVersionInfo.get().setuptools_version


class SQServer:
    """
    Simple Queueing System server class

    This class handles receiving requests from clients and managing the queueing and
    execution of work.
    """

    dispatcher = MessageDispatcher()

    def __init__(
        self,
        port: int = 9126,
        ip_address: str = "127.0.0.1",
        config_file: str = join(expanduser("~"), "sqs.config"),
        log_file: str = join(expanduser("~"), "sqs.log"),
        nworkers: int = cpu_count() - 2,
        feed_delay=0.0,
        debug: bool = False,
    ):

        self.config_file = config_file

        self.config = Configuration(
            ip_address=ip_address,
            port=port,
            config_file=config_file,
            log_file=log_file,
            nworkers=nworkers,
        )

        # self.port = port
        # self.ip_address = ip_address
        # self.config_file = config_file
        # self.log_file = log_file
        # self.nworkers = nworkers
        self.pool = None
        self._shutting_down = False
        self.jobs = deque()
        self.job_id = 0
        self._debug = debug
        self.feed_delay = feed_delay
        self.event_loop = None
        self.__server = None

        self.log = None
        self.setup_logging(self.config.log_file)

        self.log.info("Starting SQS version %s", VERSION)

    def __start_workers(self, nworkers: int = None):
        """Starts the worker pool

        Parameters
        ----------
        nworkers: int
            number of workers
        """
        if nworkers is None:
            nworkers = self.config.nworkers

        # self.pool = cf.ProcessPoolExecutor(max_workers=nworkers)
        self.pool = DynamicProcessPool(max_workers=nworkers, feed_delay=self.feed_delay)
        self.pool.add_event_callback(self.receive_pool_events)
        self.log.info("Worker pool started with {} workers".format(nworkers))

    def run(self):
        """
        Starts the worker process pool and the event loop
        """
        import ssl

        self.__start_workers()

        # sc = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        # sc.check_hostname = False
        # sc.load_cert_chain(
        #     r'A:\data\.cert\shrike-data-public.cert',
        #     r'A:\data\.cert\shrike-data-private.key'
        # )

        self.event_loop = asyncio.get_event_loop()

        coro = asyncio.start_server(
            self.handle_job_submission,
            self.config.ip_address,
            self.config.port,
            loop=self.event_loop,
        )
        # self.config.ip_address, self.config.port, loop=self.event_loop, ssl=sc)

        self.__server = self.event_loop.run_until_complete(coro)

        # Serve requests until Ctrl+C is pressed
        self.log.info("Serving on {}".format(self.__server.sockets[0].getsockname()))
        try:
            self.event_loop.run_forever()
        except (KeyboardInterrupt, SQSShutdownException):
            self.log.info("Shutting down server")
        finally:
            # Close the server
            self.config.save()
            self.pool.shutdown(wait=False)

            self.__server.close()
            # pending = asyncio.Task.all_tasks()

            # Run loop until tasks done:
            # self.event_loop.run_until_complete(asyncio.gather(*pending))
            self.event_loop.run_until_complete(self.__server.wait_closed())

            # self.event_loop.run_until_complete(self.handle_job_submission.finish_connections(5))
        self.event_loop.close()
        # self.event_loop.run_until_complete(app.cleanup())

    def receive_pool_events(self, event: dict):
        """
        The sqs.mp_pool.DynamicProcessPool sends some events when jobs start
        and stop.  The method is registered as a callback to receive these
        events.

        Parameters
        ----------
        event: dict
            dict containing the data from the event
        """

        if event["event_type"] == "started" and len(self.jobs) > 0:
            job = self.get_job_by_id(event["job_id"])
            if job:
                job["status"] = "R"
                job["started"] = event["data"]
                self.log.info(
                    "+Started job {} at {}".format(job["job_id"], job["started"])
                )

        elif event["event_type"] == "completed" and len(self.jobs) > 0:
            job = self.get_job_by_id(event["job_id"])
            if job:
                job["status"] = "C"
                if not job["completed"]:
                    job["completed"] = event["data"]
                self.log.info(
                    "-Finished job {} at {}".format(job["job_id"], job["completed"])
                )

    def get_job_by_id(self, job_id: int) -> dict:
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

        for job, __ in self.jobs:
            if job["job_id"] == job_id:
                return job

        # @property
        # def config(self) -> dict:
        """
        Gets the configuration dict for this server instance
        """
        # return self.config{
        #     "job_id": self.job_id,
        #     "port": self.port,
        #     "ip_address": self.ip_address}

    def read_config(self):
        """
        Reads the sqs configuration file.
        """
        self.config = Configuration.load(self.config_file)
        # if os.path.exists(self.config_file):
        #     with open(self.config_file) as fid:
        #         config = json.load(fid)
        #
        #     self.log.debug(config)
        #
        #     self.job_id = config.get('job_id', self.job_id)
        #     self.log.info('Initial JobID = {}'.format(self.job_id))
        #
        #     self.port = config.get('port', self.port)
        #     self.ip_address = config.get('ip_address', self.ip_address)

    def write_config(self):
        """Writes the SQS configuration file"""
        self.config.last_job_id = self.job_id
        self.config.save()
        # with open(self.config_file, 'w') as fid:
        #     json.dump(self.config, fid)

        self.log.debug("config file written")

    def setup_logging(self, log_file: str):
        """
        Sets up logging.  A console and file logger are used.  The _DEGBUG flag on
        the SQServer instance controls the log level

        Parameters
        ----------
        log_file: str
        """
        self.log = logging.getLogger("SQS")
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s " + "[%(module)s:%(lineno)d] %(message)s"
        )
        # setup console logging

        console_handler = logging.StreamHandler()
        if self._debug:
            self.log.setLevel(logging.DEBUG)
            console_handler.setLevel(logging.DEBUG)
        else:
            self.log.setLevel(logging.INFO)
            console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        self.log.addHandler(console_handler)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, backupCount=2, maxBytes=5 * 1024 * 1024
        )  # 5 megabytes
        if self._debug:
            file_handler.setLevel(logging.DEBUG)
        else:
            file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        self.log.addHandler(file_handler)

    async def handle_job_submission(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        """
        Called when the server receives a message from the client.

        """

        # self.log.debug('message received')
        data = await reader.read()

        message = data.decode()

        self.log.debug("message received: {}".format(message))

        addr = writer.get_extra_info("peername")
        #        print("Received %r from %r" % (message, addr))

        message = json.loads(message)

        message["host"] = addr[0]

        func = self.dispatcher.get_handler(message)

        await func(self, message, reader, writer)
