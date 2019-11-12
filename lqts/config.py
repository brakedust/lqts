import concurrent.futures as cf
import enum
import itertools
from datetime import datetime, timedelta
from multiprocessing import cpu_count
from os.path import expanduser, join
from queue import PriorityQueue
from typing import Any, Deque, Dict, List, Union
from uuid import uuid4

from pydantic import BaseModel, BaseSettings


class Configuration(BaseSettings):

    ip_address: str = "127.0.0.1"
    port: int = 9200
    log_file: str = join(expanduser("~"), "lqts.log")
    config_file: str = join(expanduser("~"), "lqts.config")
    queue_file: str = join(expanduser("~"), "lqts.queue.txt")
    nworkers: int = max(cpu_count() - 2, 1)
    ssl_cert: str = None

    prune_time_limit: timedelta = timedelta(days=1)
    completed_limit: int = 1000

    @property
    def url(self):
        if self.ssl_cert:
            return f"https://{self.ip_address}:{self.port}"
        else:
            return f"http://{self.ip_address}:{self.port}"

    class Config:
        env_prefix = "lqts_"  # defaults to no prefix, i.e. ""
        case_sensitive = True


DEFAULT_CONFIG = Configuration()
