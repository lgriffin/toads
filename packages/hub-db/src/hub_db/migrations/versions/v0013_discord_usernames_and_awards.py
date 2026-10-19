"""Members' Discord usernames, and the awards officers give members

Revision ID: 0013
Revises: 0012
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("members", sa.Column("discord_username", sa.String(32), nullable=True))
    op.create_table(
        "member_awards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("member_id", sa.Integer(), sa.ForeignKey("members.id", ondelete="CASCADE"), nullable=False),
        sa.Column("award_id", sa.String(48), nullable=False),
        sa.Column("period", sa.String(7), nullable=False, server_default=""),
        sa.Column("note", sa.String(200), nullable=True),
        sa.Column("awarded_by", sa.Integer(), sa.ForeignKey("members.id", ondelete="SET NULL"), nullable=True),
        sa.Column("awarded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("member_id", "award_id", "period", name="uq_member_award"),
    )
    op.create_index("ix_member_awards_member_id", "member_awards", ["member_id"])
    op.create_index("ix_member_awards_award_id", "member_awards", ["award_id"])


def downgrade() -> None:
    op.drop_index("ix_member_awards_award_id", table_name="member_awards")
    op.drop_index("ix_member_awards_member_id", table_name="member_awards")
    op.drop_table("member_awards")
    op.drop_column("members", "discord_username")
