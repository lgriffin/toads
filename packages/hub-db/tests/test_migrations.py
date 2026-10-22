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


def test_0043_pins_for_each_night_the_docs_it_showed(tmp_path: Path) -> None:
    from sqlalchemy import text

    url = f"sqlite:///{tmp_path / 'hub.db'}"
    command.upgrade(alembic_config(url), "0042")
    engine = create_engine(url)
    now = "2026-10-22 20:00:00"
    with engine.begin() as conn:
        for doc_id, raid, day in ((1, "mc", None), (2, "mc", "wed"), (3, "bwl", None), (4, "zg", "sun")):
            conn.execute(
                text(
                    "INSERT INTO strategy_docs (id, raid, raid_day_id, title, url, created_at) "
                    "VALUES (:i, :r, :d, 't', 'https://docs.google.com/x', :now)"
                ),
                {"i": doc_id, "r": raid, "d": day, "now": now},
            )
        for day, raid, position in (("wed", "mc", 0), ("wed", "bwl", 1), ("sun", "zg", 0), ("thu", "aq40", 0)):
            conn.execute(
                text("INSERT INTO night_raid_choices (raid_day_id, raid, position, set_at) VALUES (:d, :r, :p, :now)"),
                {"d": day, "r": raid, "p": position, "now": now},
            )
    command.upgrade(alembic_config(url), "0043")
    with engine.connect() as conn:
        pins = conn.execute(
            text("SELECT raid_day_id, doc_id, position FROM night_strategy_docs ORDER BY raid_day_id, position")
        ).all()
    # Wednesday kept its own MC doc and the every-night BWL one; Thursday's AQ40 had no doc to show.
    assert [tuple(p) for p in pins] == [("sun", 4, 0), ("wed", 2, 0), ("wed", 3, 1)]
    command.downgrade(alembic_config(url), "0042")
    with engine.connect() as conn:
        choices = conn.execute(
            text("SELECT raid_day_id, raid, position FROM night_raid_choices ORDER BY raid_day_id, position")
        ).all()
    assert [tuple(c) for c in choices] == [("sun", "zg", 0), ("wed", "mc", 0), ("wed", "bwl", 1)]
