"""Run the hub-db Alembic migrations: `hub-db-migrate` (reads TOADS_DATABASE_URL) or `upgrade(url)`."""

from __future__ import annotations

import os

from alembic import command
from alembic.config import Config


def alembic_config(url: str) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", "hub_db:migrations")
    # Passed as an attribute, not an ini option, so passwords are never %-interpolated or written out.
    cfg.attributes["url"] = url
    return cfg


def upgrade(url: str, revision: str = "head") -> None:
    command.upgrade(alembic_config(url), revision)


def main() -> None:
    upgrade(os.environ["TOADS_DATABASE_URL"])


if __name__ == "__main__":
    main()
