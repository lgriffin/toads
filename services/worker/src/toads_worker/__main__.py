from __future__ import annotations

import json
import sys

from redis import Redis
from rq import Worker

from toads_worker.jobs.sheets import import_raid_sheets
from toads_worker.settings import Settings


def main() -> None:
    settings = Settings()  # fails fast on a missing variable
    if sys.argv[1:] == ["import-sheets"]:
        # One-off import of the CBA and RPB sheets, for cron or `docker compose run worker toads-worker import-sheets`.
        print(json.dumps(import_raid_sheets(settings), indent=2))
        return
    Worker(["default", "media"], connection=Redis.from_url(settings.redis_url)).work()


if __name__ == "__main__":
    main()
