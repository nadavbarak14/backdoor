"""Add positions column to players and player_team_histories

Changes Player.position (String) -> Player.positions (JSON array)
Changes PlayerTeamHistory.position (String) -> PlayerTeamHistory.positions (JSON array)

This migration supports players having multiple positions (e.g., G/F).
Positions are stored as JSON arrays of position abbreviations: ["PG", "SG"]

Revision ID: 9caca686de8a
Revises: 3e82c0f7c143
Create Date: 2026-01-29 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9caca686de8a"
down_revision: str | None = "3e82c0f7c143"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Migrate from single position string to positions JSON array.

    1. Add new positions column (JSON array)
    2. Migrate existing data: "PG" -> ["PG"], "G-F" -> ["G", "F"]
    3. Drop old position column
    """
    # ==== PLAYERS TABLE ====
    # Add new positions column
    op.add_column(
        "players",
        sa.Column("positions", sa.JSON(), nullable=False, server_default="[]"),
    )

    # Migrate existing position data to positions array
    # Handle multi-position strings like "G-F" by splitting on common separators
    op.execute(
        """
        UPDATE players
        SET positions = CASE
            WHEN position IS NULL OR position = '' THEN '[]'
            WHEN position LIKE '%-%' THEN json_array(
                TRIM(SUBSTR(position, 1, INSTR(position, '-') - 1)),
                TRIM(SUBSTR(position, INSTR(position, '-') + 1))
            )
            WHEN position LIKE '%/%' THEN json_array(
                TRIM(SUBSTR(position, 1, INSTR(position, '/') - 1)),
                TRIM(SUBSTR(position, INSTR(position, '/') + 1))
            )
            ELSE json_array(TRIM(position))
        END
        """
    )

    # Drop old position column
    op.drop_column("players", "position")

    # ==== PLAYER_TEAM_HISTORIES TABLE ====
    # Add new positions column
    op.add_column(
        "player_team_histories",
        sa.Column("positions", sa.JSON(), nullable=False, server_default="[]"),
    )

    # Migrate existing position data
    op.execute(
        """
        UPDATE player_team_histories
        SET positions = CASE
            WHEN position IS NULL OR position = '' THEN '[]'
            WHEN position LIKE '%-%' THEN json_array(
                TRIM(SUBSTR(position, 1, INSTR(position, '-') - 1)),
                TRIM(SUBSTR(position, INSTR(position, '-') + 1))
            )
            WHEN position LIKE '%/%' THEN json_array(
                TRIM(SUBSTR(position, 1, INSTR(position, '/') - 1)),
                TRIM(SUBSTR(position, INSTR(position, '/') + 1))
            )
            ELSE json_array(TRIM(position))
        END
        """
    )

    # Drop old position column
    op.drop_column("player_team_histories", "position")


def downgrade() -> None:
    """
    Revert to single position string.

    Takes the first position from the array.
    """
    # ==== PLAYERS TABLE ====
    # Add back old position column
    op.add_column(
        "players",
        sa.Column("position", sa.String(20), nullable=True),
    )

    # Migrate positions array back to single position (take first)
    op.execute(
        """
        UPDATE players
        SET position = CASE
            WHEN positions IS NULL OR positions = '[]' THEN NULL
            ELSE json_extract(positions, '$[0]')
        END
        """
    )

    # Drop positions column
    op.drop_column("players", "positions")

    # ==== PLAYER_TEAM_HISTORIES TABLE ====
    # Add back old position column
    op.add_column(
        "player_team_histories",
        sa.Column("position", sa.String(20), nullable=True),
    )

    # Migrate positions array back to single position (take first)
    op.execute(
        """
        UPDATE player_team_histories
        SET position = CASE
            WHEN positions IS NULL OR positions = '[]' THEN NULL
            ELSE json_extract(positions, '$[0]')
        END
        """
    )

    # Drop positions column
    op.drop_column("player_team_histories", "positions")
