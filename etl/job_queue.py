import json
import os
from dataclasses import dataclass


QUEUE_NAME = "aibi:etl:jobs"


@dataclass(frozen=True)
class ETLJob:
    session_id: str
    file_paths: list[str]

    def to_json(self) -> str:
        return json.dumps({"session_id": self.session_id, "file_paths": self.file_paths})

    @classmethod
    def from_json(cls, payload: str) -> "ETLJob":
        data = json.loads(payload)
        return cls(session_id=data["session_id"], file_paths=data["file_paths"])


class RedisETLQueue:
    def __init__(self, client, queue_name: str = QUEUE_NAME):
        self.client = client
        self.queue_name = queue_name

    def enqueue(self, job: ETLJob) -> None:
        self.client.rpush(self.queue_name, job.to_json())

    def dequeue(self, timeout: int = 0) -> ETLJob | None:
        item = self.client.blpop(self.queue_name, timeout=timeout)
        if item is None:
            return None
        _, payload = item
        return ETLJob.from_json(payload)


def get_etl_queue() -> RedisETLQueue:
    redis_url = os.getenv("REDIS_URL", "").strip()
    if not redis_url:
        raise ValueError("REDIS_URL is required for asynchronous ETL")

    import redis

    client = redis.Redis.from_url(redis_url, decode_responses=True)
    client.ping()
    return RedisETLQueue(client)