"""members, character_claims and audit (phase 2.2 identity and RBAC)

Revision ID: 0001
Revises:
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("discord_user_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("profile_public", sa.Boolean(), nullable=False),
        sa.Column("dms_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "character_claims",
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
        sa.UniqueConstraint("character_id", name="uq_claim_character"),
    )
    op.create_index("ix_character_claims_member_id", "character_claims", ["member_id"])
    op.create_index("ix_character_claims_character_id", "character_claims", ["character_id"])
    op.create_index("ix_character_claims_raid_day_id", "character_claims", ["raid_day_id"])
    op.create_table(
        "audit",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_member_id", sa.Integer(), sa.ForeignKey("members.id"), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("target", sa.String(200), nullable=False),
        sa.Column("raid_day_id", sa.String(32), nullable=True),
        sa.Column("detail", sa.String(500), nullable=True),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_raid_day_id", "audit", ["raid_day_id"])


def downgrade() -> None:
    op.drop_table("audit")
    op.drop_table("character_claims")
    op.drop_table("members")
