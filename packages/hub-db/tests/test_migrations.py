"""The Alembic migrations build exactly the tables the models declare, and downgrade cleanly."""

from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from hub_db import Base
from hub_db.migrate import alembic_config, upgrade
from sqlalchemy import create_engine, inspect


def test_migrations_match_models(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'hub.db'}"
    upgrade(url)
    engine = create_engine(url)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == []


def test_downgrade_to_base(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'hub.db'}"
    upgrade(url)
    command.downgrade(alembic_config(url), "base")
    assert set(inspect(create_engine(url)).get_table_names()) <= {"alembic_version"}
