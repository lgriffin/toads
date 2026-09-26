from __future__ import annotations

from redis import Redis
from rq import Worker

from toads_worker.settings import Settings


def main() -> None:
    settings = Settings()  # fails fast on a missing variable
    Worker(["default", "media"], connection=Redis.from_url(settings.redis_url)).work()


if __name__ == "__main__":
    main()
