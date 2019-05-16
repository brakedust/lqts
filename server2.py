from fastapi import FastAPI
from .work_queue import Configuration, Job, JobQueue

class Application(FastAPI):

    def __init__(self):
        super().__init__()

        self.config = Configuration()
        self.queue = JobQueue()

app = Application()
app.debug = True
# app.mount('/static', StaticFiles(directory="static"))


def fake_job():
    j = Job(command="echo hello")
    return j

app.queue.submit(fake_job())
app.queue.submit(fake_job())
app.queue.submit(fake_job())


@app.get('/')
def root():
    return 'Hello, world!'


@app.get("/q")
def get_queue():
    return [j.dump(dialect='json') for j in app.queue.jobs]

@app.put("/qsub")
def qsub(command:str, working_dir:str, log_file:str=None):
    job = Job(
        command=command,
        working_dir=working_dir,
        log_file=log_file,
    )
    app.queue.submit(job)