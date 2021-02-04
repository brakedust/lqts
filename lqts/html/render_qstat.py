from typing import List
from collections import Counter
from lqts.schema import Job, JobID, JobSpec, JobStatus
from lqts.server import app

# import jinja2
# import lqts.displaytable as dt
# from lqts.themes import make_html

from jinja2 import Environment, PackageLoader, select_autoescape


env = Environment(
    loader=PackageLoader("lqts", "html"), autoescape=select_autoescape(["html", "xml"])
)

STATUS_SORT_ORDER = {"R": 1, "Q": 2, "C": 3, "D": 4, "E": 5, "I": 6}


def render_qstat_table(jobs: List[Job], include_complete: bool = False):

    header = ["ID", "St", "Command", "Walltime", "WorkingDir", "Dependencies"]
    rows = (
        job.as_table_row()
        for job in sorted(
            jobs, key=lambda job: STATUS_SORT_ORDER[job.status.value], reverse=True
        )
        if include_complete or job.status is not JobStatus.Completed
    )

    table_template = env.get_template("table_template.jinja")
    table_text = table_template.render(header=header, rows=rows)

    return table_text


def render_qstat_page(include_complete: bool = False):

    jobs = app.queue.all_jobs

    page_template = env.get_template("page_template.jinja")
    buttonbar = env.get_template("button_bar.jinja").render(
        workercount=app.pool.max_workers
    )
    script_block = env.get_template("js_script_template.jinja").render()

    c = Counter([job.status.value for job in jobs])
    for letter in "QDRC":
        if letter not in c:
            c[letter] = 0

    summary_text = "  ".join(f"{s}:{c}" for s, c in c.items())

    page_text = page_template.render(
        page_title="Queue Status",
        navbar="",
        buttonbar=buttonbar,
        summary=summary_text,
        table=render_qstat_table(jobs, include_complete),
        script_block=script_block,
    )

    return page_text


if __name__ == "__main__":

    job = Job(
        job_id=JobID(group=1, index=2),
        job_spec=JobSpec(command="cmd /c echo hello", working_dir="/tmp"),
    )

    print(render_qstat_page(jobs=[job]))
