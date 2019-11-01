import requests
from lqts.job_runner import run_command
from lqts.schema import Job, DEFAULT_CONFIG
import time
import ujson
from multiprocessing import cpu_count


def worker():

    while True:

        response = requests.get(f"{DEFAULT_CONFIG.url}/job_request")

        # try:

        job = Job(**ujson.loads(response.json()))
        if not response.json():
            time.sleep(2)
            continue

        print(f"Starting job {job.job_id}")
        job = run_command(job)

        response = requests.put(f"{DEFAULT_CONFIG.url}/job_done", data=job.dict())
        print("Job done")
        # except:
        #     pass


class WorkerPool:
    
    def __init__(self, max_cores: int = cpu_count - 2):

        self.max_cores = max_cores


    def _runloop(self):
        """
        This is the loop that manages getting job completetions, taking care of the sub-processes
         and keeping the queue moving
        """
        while True:

            self.process_completions()

            if self.__abort:
                return

    def submit(self, func: Callable, job: Job):

        self.q_count += 1
        # f = MyFuture(func, args, job_id, call_back=call_back)
        future = cf.Future()
        # if job_id is None:
        #     job_id = self.q_count

        # if args is None:
        #     args = tuple()

        # if kwargs is None:
        #     kwargs = {}

        work_item = _WorkItem(
            job=job,
            future=future,
            fn=func,
            # args=args,
            # kwargs=kwargs
        )

        with self.q_lock:
            self.log.debug("Submitting {}".format(job.job_id))
            self._queue.append(work_item)
            self._results[job.job_id] = work_item
        # self.feed_queue()

        return future

if __name__ == "__main__":
    main()
