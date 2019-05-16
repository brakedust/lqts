from os.path import join, expanduser
from multiprocessing import cpu_count

import yaml


class Configuration:
    def __init__(
        self,
        ip_address="127.0.0.1",
        port=9126,
        last_job_id=0,
        log_file=join(expanduser("~"), "sqs.log"),
        config_file=join(expanduser("~"), "sqs.config"),
        nworkers: int = max(cpu_count() - 2, 1),
    ):

        self.ip_address = "127.0.0.1"
        self.port = port
        self.last_job_id = last_job_id
        self.log_file = log_file
        self.config_file = config_file
        self.nworkers = nworkers

    def load_defaults(self):

        self.ip_address = "127.0.0.1"
        self.port = 9126
        self.last_job_id = "0"
        self.log_file = join(expanduser("~"), "sqs.log")
        self.config_file = join(expanduser("~"), "sqs.config")
        self.nworkers = max(cpu_count() - 2, 1)

    def save(self):

        d = {
            "ip_address": self.ip_address,
            "port": self.port,
            "log_file": self.log_file,
            "last_job_id": self.last_job_id,
            "nworkers": self.nworkers,
        }

        with open(self.config_file, "w") as fid:
            fid.write(yaml.dump(d))

    @classmethod
    def load(cls, config_file):

        with open(config_file, "r") as fid:
            kwargs = yaml.load(fid)

        return cls(**kwargs)

