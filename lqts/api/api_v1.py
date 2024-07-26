from datetime import datetime

from lqts.core import server
from lqts.core.schema import Job, JobID, JobSpec, JobStatus

API_VERSION = "api_v1"

app = server.get_app()


@app.get(f"/{API_VERSION}/qstat")
async def get_queue_status(options: dict):
    # print(options)

    queue_status = []
    if options.get("running", True):
        for job in list(app.queue.running_jobs.values()):
            queue_status.append(job.model_dump_json())

    if options.get("queued", True):
        for job in list(app.queue.queued_jobs.values()):
            queue_status.append(job.model_dump_json())

    if options.get("completed", False):
        queue_status.extend([job.model_dump_json() for jid, job in list(app.queue.completed_jobs.items())])

    return queue_status


@app.post(f"/{API_VERSION}/qsub")
async def qsub(job_specs: list[JobSpec]):
    print(f"Submitted job specs {job_specs}")
    return app.queue.submit(job_specs)


@app.on_event("shutdown")
async def on_shutdown():
    app.pool.shutdown(wait=False)
    app.queue.shutdown()


@app.get(f"/{API_VERSION}/qsummary")
async def get_summary():
    """
    Gets a summary of what the state of the queue is.
    * I = Initialized
    * Q = Queued
    * R = Running
    * D = Deleted
    * C = completed
    """
    # c = Counter([job.status.value for job in app.queue.jobs])
    summary = {
        "Running": len(app.queue.running_jobs),
        "Queued": len(app.queue.queued_jobs),
    }
    # for letter in "RQDC":
    #     if letter not in c:
    #         c[letter] = 0

    return summary


@app.get(f"/{API_VERSION}/workers")
async def get_workers():
    """
    Gets the number of worker processes to execute jobs.
    """
    app.log.info("Number of workers queried by user. Returned {}".format(app.pool.max_workers))
    return app.pool.max_workers


@app.post(f"/{API_VERSION}/workers")
async def set_workers(count: int) -> int:
    """
    Sets the number of worker processes to execute jobs.
    """
    app.log.info("Setting maximum number of workers to {}".format(count))
    app.pool.resize(count)
    return app.pool.max_workers


@app.get(f"/{API_VERSION}/jobgroup")
async def get_job_group(group_number: int) -> list[JobID]:
    return list(app.queue.job_groups[group_number].jobs.keys())


@app.post(f"/{API_VERSION}/qclear")
async def clear_queue(really: bool) -> str:
    """
    Kills running jobs and totally erases the queue.
    """
    if really:
        app.pool.pause()
        app.pool.kill_job(None, True)
        app.queue.clear()
        app.pool.unpause()
        return "Killed running jobs and cleared queue"
    else:
        return "You must specify really=true to actually kill the jobs"


@app.post(f"/{API_VERSION}/clear_completed")
async def clear_completed(really: bool) -> str:
    """
    Kills running jobs and totally erases the queue.
    """
    if really:
        app.queue.completed_jobs.clear()
        # app.pool.pause()
        # app.pool.kill_job(None, True)
        # app.queue.clear()
        # app.pool.unpause()
        return "Cleared completed jobs in queue"
    else:
        return "You must specify really=true to actually kill the jobs"


@app.post(f"/{API_VERSION}/qdel")
async def qdel(job_ids: list[JobID]) -> dict[str, list[JobID]]:
    """
    Delete on or more jobs
    """

    deleted_jobs = app.queue.qdel(job_ids)

    for job_id in deleted_jobs:
        if job_id in app.pool._work_items:
            app.pool.kill_job(job_id)

    return {"Deleted jobs": deleted_jobs}


@app.post(f"/{API_VERSION}/qpriority")
async def qpriority(priority: int, job_ids: list[JobID]):
    app.log.info(f"Setting priority of jobs {job_ids} to {priority}")
    for job_id in job_ids:
        job, _ = app.queue.find_job(job_id)

        job.job_spec.priority = priority


@app.get(f"/{API_VERSION}/job_request")
async def job_request() -> Job:
    job = app.queue.queued_jobs.pop()
    if job is None:
        return "{}"
    else:
        job.started = datetime.now()
        job.status = JobStatus.Running
        app.queue.running_jobs[job.job_id] = job
        app.log.info("  +Started job {} at {}".format(job.job_id, job.started))
        return job


@app.post(f"/{API_VERSION}/job_done")
async def job_done(done_job: Job):
    app.queue.on_job_finished(done_job)


@app.post(f"/{API_VERSION}/job_started")
async def job_started():
    pass


@app.post(f"/{API_VERSION}/resume")
async def qresume(job_ids: list[JobID]) -> list[JobID]:
    print("Received requst to resume some jobs")
    jobs_resumed = app.queue.resume(job_ids=job_ids)
    return jobs_resumed
