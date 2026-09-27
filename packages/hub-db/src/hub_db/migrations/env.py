"""Alembic environment for hub-db. The URL comes from `hub_db.migrate`, never from an ini file."""

from __future__ import annotations

from alembic import context
from hub_db.models import Base
from sqlalchemy import create_engine

url = context.config.attributes["url"]
engine = create_engine(url)
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()
engine.dispose()
