import concurrent.futures as cf
import enum
import itertools
from datetime import datetime, timedelta
from multiprocessing import cpu_count
from os.path import expanduser, join
import os
from queue import PriorityQueue
from typing import Any, Deque, Dict, List, Union
from uuid import uuid4

from pydantic import BaseModel, BaseSettings

from lqts.util import parse_bool

class Configuration(BaseModel):

    ip_address: str = os.environ.get("LQTS_IP_ADDRESS", "127.0.0.1")
    port: int = int(os.environ.get("LQTS_PORT", "9200"))
    log_file: str = os.environ.get("LQTS_LOG_FILE", join(expanduser("~"), "lqts.log"))
    config_file: str = os.environ.get("LQTS_CONFIG_FILE", "")  # join(expanduser("~"), "lqts.config")
    queue_file: str = os.environ.get("LQTS_QUEUE_FILE", join(expanduser("~"), "lqts.queue.txt"))
    nworkers: int = int(os.environ.get("LQTS_NWORKERS", max(cpu_count() - 2, 1)))
    ssl_cert: str = os.environ.get("LQTS_SSL_CERT", None)

    prune_time_limit: timedelta = timedelta(days=1)
    completed_limit: int = int(os.environ.get("LQTS_COMPLETED_LIMIT", 1000))

    resume_on_start_up: bool = parse_bool(os.environ.get("LQTS_RESUME_ON_START_UP", True))

    @property
    def url(self):
        if self.ssl_cert:
            return f"https://{self.ip_address}:{self.port}"
        else:
            return f"http://{self.ip_address}:{self.port}"

    # class Config:
    #     env_prefix = "lqts_"  # defaults to no prefix, i.e. ""
    #     case_sensitive = True


DEFAULT_CONFIG = Configuration()
