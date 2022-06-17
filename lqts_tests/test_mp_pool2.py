import pytest
import time

# from lqts.lqts.schema import JobSpec, WorkItem
from lqts.mp_pool2 import WorkItem, DynamicProcessPool
from lqts.schema import JobSpec, Job, JobQueue, JobID


def test_work_item():

    q = JobQueue()

    js = JobSpec(command="cmd.exe /C sleep 2.5", working_dir="d:/temp", cores=2)

    job_id = q.submit([js])[0]
    job, q2 = q.find_job(job_id)

    wi = WorkItem(job=job, cores=[0, 1])

    print(wi)

    wi.start()

    for i in range(10):
        print(i)
        time.sleep(0.5)
        print(wi.get_status())
        if not wi.is_running():
            break

    print("done")


def test_work_item_kill():

    q = JobQueue()

    js = JobSpec(command="cmd.exe /C sleep 2.5", working_dir="d:/temp", cores=2)

    job_id = q.submit([js])[0]
    job, q2 = q.find_job(job_id)

    wi = WorkItem(job=job, cores=[0, 1])

    print(wi)

    wi.start()

    for i in range(10):
        print(i)
        time.sleep(0.5)
        wi.kill()
        print(wi.get_status())
        if not wi.is_running():
            break

    print("done")
    print(wi)


def test_pool():

    q = JobQueue()

    js = JobSpec(command="cmd.exe /C sleep 2.5", working_dir="d:/temp", cores=1)

    q.submit([js] * 20)
    # job, q2 = q.find_job(job_id)

    pool = DynamicProcessPool(q, 20)

    pool._start_manager_thread()
    time.sleep(4)
    print(q.running_jobs.values())
    assert len(q.running_jobs) > 0

    time.sleep(10)
    pool.join(wait=True)
    print(q.running_jobs.values())
    assert len(q.running_jobs) == 0


if __name__ == "__main__":
    # test_work_item()
    # test_work_item_kill()
    test_pool()