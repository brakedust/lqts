import json
from pathlib import Path

import requests

from lqts.core.config import config
from lqts.core.schema import JobID, JobSpec


def get_job_ids(job_id_str: str):
    """
    Gets the JobID whether job_id_str refers to a single job or a job group
    The server is queried in the case that a job group is specified.
    A job group may be specified with simply the group number ("21") or
    with an asterisk ("21.*")
    """
    is_job_group = ((".") not in job_id_str) or (job_id_str.endswith(".*"))

    if is_job_group:
        gnum = job_id_str.partition(".")[0]
        resp = requests.get(f"{config.url}/api_v1/jobgroup?group_number={int(gnum)}")
        # print(resp.url, resp.raw)
        # print(resp.json())
        # for jid in resp.json():
        #     print(f"{type(jid)} -- {jid=}")

        try:
            return [JobID(**jid) for jid in resp.json()]
        except json.decoder.JSONDecodeError:
            return []
    else:
        return JobID.parse_obj(job_id_str)


def parse_walltime(walltime):
    if ":" in walltime:
        hrs, minutes, sec = [int(x) for x in walltime.split(":")]
        walltime = sec + 60 * minutes + hrs * 3600
    else:
        walltime = float(walltime)
    return walltime
