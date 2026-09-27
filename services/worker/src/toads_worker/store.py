"""The analyzer's Postgres storage (wcl-store) for the worker: one engine per database URL, a storage factory
for ``wcl_app.AppContext`` and the ``toads-worker-migrate`` entry point.

wcl-store's tables live in the hub database beside hub-db's. Its Alembic migrations record their revision in
``wcl_store_alembic_version``, so they never touch hub-db's ``alembic_version``.
"""

from __future__ import annotations

from functools import cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Engine
from wcl_app.context import StorageFactory
from wcl_store.postgres import PostgresRaidRepository, make_engine, upgrade

from toads_worker.settings import Settings


@cache
def engine_for(url: str) -> Engine:
    """A pooled engine per database URL, shared by every job in this process."""
    return make_engine(url, pool_pre_ping=True)


def storage(settings: Settings) -> StorageFactory:
    """Opens a wcl-store repository on the hub database for one ``with`` block."""
    engine = engine_for(settings.database_url.get_secret_value())
    return lambda: PostgresRaidRepository(engine)


class MigrateSettings(BaseSettings):
    """Only the database URL: the migration step needs no Redis or Warcraft Logs credentials."""

    model_config = SettingsConfigDict(env_prefix="TOADS_", extra="ignore")

    database_url: SecretStr


def migrate(url: str) -> None:
    """Bring the analyzer tables to wcl-store's latest migration."""
    upgrade(url)


def migrate_main() -> None:
    """``toads-worker-migrate``: run wcl-store's migrations against TOADS_DATABASE_URL."""
    migrate(MigrateSettings().database_url.get_secret_value())
