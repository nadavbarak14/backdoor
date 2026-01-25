"""Add external_id to team_seasons

Revision ID: a1b2c3d4e5f6
Revises: 9dd00f102f7e
Create Date: 2026-01-25 12:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "e238ef0d8583"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Apply the migration.

    Adds external_id column to team_seasons table to store competition-specific
    external IDs. This allows the same team to have different external IDs in
    different competitions (e.g., Maccabi Tel Aviv in Winner League vs Euroleague).
    """
    op.add_column(
        "team_seasons",
        sa.Column("external_id", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    """
    Revert the migration.

    Removes external_id column from team_seasons table.
    """
    op.drop_column("team_seasons", "external_id")
