"""Member settings: which name the hub shows, and members' own Warcraft Logs keys (encrypted)

Revision ID: 0005
Revises: 0004
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("members") as batch:
        batch.add_column(sa.Column("name_source", sa.String(16), nullable=False, server_default="discord"))
        batch.add_column(sa.Column("name_character_id", sa.Integer(), nullable=True))
    op.create_table(
        "wcl_credentials",
        sa.Column("member_id", sa.Integer(), sa.ForeignKey("members.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("client_id_encrypted", sa.Text(), nullable=False),
        sa.Column("client_secret_encrypted", sa.Text(), nullable=False),
        sa.Column("client_id_hint", sa.String(8), nullable=False),
        sa.Column(
            "status",
            sa.Enum("unverified", "working", "rejected", name="wclcredentialstatus", native_enum=False, length=16),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("wcl_credentials")
    with op.batch_alter_table("members") as batch:
        batch.drop_column("name_character_id")
        batch.drop_column("name_source")
