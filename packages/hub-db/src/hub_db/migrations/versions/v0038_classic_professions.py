"""Classic Forever professions: Jewelcrafting and the Alchemy and Tailoring specialisations arrive with TBC, so take
them out of what members listed (and any Jewelcrafting crafter naming)

Revision ID: 0038
Revises: 0037
"""

from __future__ import annotations

from alembic import op

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM guild_crafters WHERE profession = 'jewelcrafting'")
    op.execute("DELETE FROM member_professions WHERE profession = 'jewelcrafting'")
    op.execute("UPDATE member_professions SET specialisation = NULL WHERE profession IN ('alchemy', 'tailoring')")


def downgrade() -> None:
    # What was removed is not kept; the TBC catalogue reads the remaining rows as they are.
    pass
