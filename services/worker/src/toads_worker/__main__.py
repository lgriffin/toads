from __future__ import annotations

import json
import sys

from redis import Redis
from rq import Worker

from toads_worker import schedule
from toads_worker.jobs.badges import publish_badges
from toads_worker.jobs.home import publish_home_page
from toads_worker.jobs.performance import publish_performance
from toads_worker.jobs.reference import publish_reference_page
from toads_worker.jobs.sheets import import_raid_sheets
from toads_worker.jobs.sync import raid_service, sync_guild_reports
from toads_worker.reports import parse_report_input
from toads_worker.settings import Settings


def _progress(message: str) -> None:
    print(message, file=sys.stderr)


def main() -> None:
    settings = Settings()  # fails fast on a missing variable
    if sys.argv[1:] == ["import-sheets"]:
        # One-off import of the CBA and RPB sheets, for cron or `docker compose run worker toads-worker import-sheets`.
        print(json.dumps(import_raid_sheets(settings), indent=2))
        return
    if sys.argv[1:] == ["publish-home"]:
        # Rebuild the analyzer widgets on members' hub homes, for cron or after analysing new raids.
        print(json.dumps(publish_home_page(settings), indent=2))
        return
    if sys.argv[1:] == ["publish-performance"]:
        # Rebuild the numbers behind each member's "Your performance" widget.
        print(json.dumps(publish_performance(settings), indent=2))
        return
    if sys.argv[1:] == ["publish-badges"]:
        # Rebuild every raider's Toads badges for their /me page.
        print(json.dumps(publish_badges(settings), indent=2))
        return
    if sys.argv[1:] == ["sync"]:
        # Import the guild's newest reports not stored yet (TOADS_SYNC_BATCH of them), as the scheduler does.
        print(json.dumps(sync_guild_reports(settings, progress=_progress), indent=2))
        return
    if len(sys.argv) == 3 and sys.argv[1] == "analyse":
        # Analyse and store one report by code or URL, e.g. one from before the sync's batch reaches it.
        code = parse_report_input(sys.argv[2])
        analysis = raid_service(settings).analyze_and_save(code, progress=_progress)
        print(json.dumps({"imported": code, "title": analysis.metadata.title}, indent=2))
        return
    if sys.argv[1:] == ["schedule"]:
        # The scheduler container: runs the jobs above on their intervals (toads_worker.schedule).
        schedule.run_forever(schedule.jobs_for(settings))
        return
    if sys.argv[1:] == ["publish-reference"]:
        # Refresh the raids officers pick from on the reference comparison page, e.g. after the nightly sync.
        print(json.dumps(publish_reference_page(settings), indent=2))
        return
    Worker(["default", "media"], connection=Redis.from_url(settings.redis_url)).work()


if __name__ == "__main__":
    main()
