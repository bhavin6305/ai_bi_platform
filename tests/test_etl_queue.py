from etl.job_queue import ETLJob, RedisETLQueue
from etl.worker import process_next_job


class FakeQueueClient:
    def __init__(self):
        self.items = []

    def rpush(self, name, payload):
        self.items.append((name, payload))

    def blpop(self, name, timeout):
        return self.items.pop(0) if self.items else None


def test_redis_etl_queue_round_trips_jobs():
    queue = RedisETLQueue(FakeQueueClient(), queue_name="jobs")
    expected = ETLJob("session-1", ["data/staging/file.csv"])

    queue.enqueue(expected)

    assert queue.dequeue(timeout=1) == expected


def test_worker_processes_job_and_removes_staged_files(tmp_path, monkeypatch):
    staged_file = tmp_path / "upload.csv"
    staged_file.write_text("id\n1\n", encoding="utf-8")
    queue = RedisETLQueue(FakeQueueClient())
    queue.enqueue(ETLJob("session-1", [str(staged_file)]))
    processed = []
    monkeypatch.setattr("etl.worker.run_pipeline", lambda **kwargs: processed.append(kwargs))

    assert process_next_job(queue) is True
    assert processed == [{"files": [str(staged_file)], "session_id": "session-1"}]
    assert not staged_file.exists()