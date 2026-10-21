"""Me: a member's main character, and their requests to swap it to an approved alt, which officers decide

Revision ID: 0031
Revises: 0030
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("members") as batch:
        batch.add_column(sa.Column("main_character_id", sa.Integer(), nullable=True))
    # A member who chose to go by one of their characters raided as it: keep that one first on Me.
    op.execute(
        "UPDATE members SET main_character_id = name_character_id "
        "WHERE name_source = 'character' AND name_character_id IS NOT NULL"
    )
    # Everyone else keeps the character Me opened on before: their approved claims' first name alphabetically.
    op.execute(
        "UPDATE members SET main_character_id = ("
        "SELECT c.character_id FROM character_claims c WHERE c.member_id = members.id AND c.status = 'approved' "
        "ORDER BY lower(c.character_name), c.id LIMIT 1"
        ") WHERE main_character_id IS NULL"
    )
    op.create_table(
        "main_swap_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("member_id", sa.Integer(), sa.ForeignKey("members.id"), nullable=False),
        sa.Column("character_id", sa.Integer(), nullable=False),
        sa.Column("character_name", sa.String(64), nullable=False),
        sa.Column("raid_day_id", sa.String(32), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "approved", "rejected", name="claimstatus", native_enum=False, length=16),
            nullable=False,
        ),
        sa.Column("reason", sa.String(200), nullable=True),
        sa.Column("decided_by", sa.Integer(), sa.ForeignKey("members.id"), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_main_swap_requests_member_id", "main_swap_requests", ["member_id"])


def downgrade() -> None:
    op.drop_index("ix_main_swap_requests_member_id", table_name="main_swap_requests")
    op.drop_table("main_swap_requests")
    with op.batch_alter_table("members") as batch:
        batch.drop_column("main_character_id")
