"""Hands reference jobs to the worker's RQ queue by function path, so the API never imports the worker."""

from __future__ import annotations

from functools import cached_property

from redis import Redis, RedisError
from rq import Queue

from toads_api.reference.service import QueueUnavailable

JOB_FUNCTION = "toads_worker.jobs.reference.run_reference_job"
# Importing another guild's report fetches every fight's events; allow it a while.
JOB_TIMEOUT_SECONDS = 1800


class RqEnqueue:
    def __init__(self, redis_url: str, queue: str = "default") -> None:
        self._redis_url = redis_url
        self._queue_name = queue

    @cached_property
    def _queue(self) -> Queue:
        return Queue(self._queue_name, connection=Redis.from_url(self._redis_url))

    def __call__(self, job_id: str) -> None:
        try:
            self._queue.enqueue(JOB_FUNCTION, job_id, job_timeout=JOB_TIMEOUT_SECONDS)
        except (RedisError, OSError) as exc:
            raise QueueUnavailable from exc
