from pathlib import Path

from lqts.core.schema import JobQueue


def test_load_queue_file():
    q = JobQueue()
    q.queue_file = Path(__file__).parent / "data" / "lqts.queue.txt"
    q.load()
    print(list(q.queued_jobs.values())[0].model_dump_json())


if __name__ == "__main__":
    test_load_queue_file()
