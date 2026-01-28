"""Add external_ids to Season model and normalize season names

Revision ID: 3e82c0f7c143
Revises: a1b2c3d4e5f6
Create Date: 2026-01-28 09:56:04.908012+00:00

This migration:
1. Adds the external_ids JSON column to seasons table
2. Migrates existing Euroleague-style season names (e.g., "E2025") to
   standardized YYYY-YY format (e.g., "2025-26")
3. Stores the original source-specific IDs in external_ids
"""

import json
import re
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3e82c0f7c143"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Regex patterns for detecting season formats
EUROLEAGUE_PATTERN = re.compile(r"^([EU])(\d{4})$")  # E2025 or U2025
STANDARD_PATTERN = re.compile(r"^(\d{4})-(\d{2})$")  # 2025-26


def normalize_season_name(year: int) -> str:
    """Convert a start year to YYYY-YY format."""
    next_year_suffix = str((year + 1) % 100).zfill(2)
    return f"{year}-{next_year_suffix}"


def upgrade() -> None:
    """
    Apply the migration.

    1. Add external_ids column with server default
    2. Normalize season names from source-specific to YYYY-YY format
    """
    # Add external_ids column with server default for existing rows
    with op.batch_alter_table("seasons", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "external_ids",
                sa.JSON(),
                nullable=False,
                server_default="{}",
            )
        )

    # Get connection for data migration
    conn = op.get_bind()

    # Fetch all seasons that may need migration
    seasons = conn.execute(sa.text("SELECT id, name FROM seasons")).fetchall()

    for season_id, name in seasons:
        new_name = name
        external_ids = {}

        # Check if name matches Euroleague format (E2025 or U2025)
        match = EUROLEAGUE_PATTERN.match(name)
        if match:
            competition = match.group(1)
            year = int(match.group(2))
            new_name = normalize_season_name(year)
            source_name = "euroleague" if competition == "E" else "eurocup"
            external_ids[source_name] = name

        # Update the season if name changed or we have external_ids
        if new_name != name or external_ids:
            conn.execute(
                sa.text(
                    "UPDATE seasons SET name = :name, external_ids = :external_ids "
                    "WHERE id = :id"
                ),
                {
                    "name": new_name,
                    "external_ids": json.dumps(external_ids),
                    "id": season_id,
                },
            )

    # Remove server default after data migration
    with op.batch_alter_table("seasons", schema=None) as batch_op:
        batch_op.alter_column(
            "external_ids",
            server_default=None,
        )


def downgrade() -> None:
    """
    Revert the migration.

    Restores original Euroleague-style names from external_ids and removes column.
    """
    conn = op.get_bind()

    # Restore original names for Euroleague seasons
    seasons = conn.execute(
        sa.text("SELECT id, name, external_ids FROM seasons")
    ).fetchall()

    for season_id, name, external_ids_json in seasons:
        if external_ids_json:
            try:
                external_ids = json.loads(external_ids_json)
                # Restore euroleague or eurocup name if present
                original_name = external_ids.get("euroleague") or external_ids.get(
                    "eurocup"
                )
                if original_name:
                    conn.execute(
                        sa.text("UPDATE seasons SET name = :name WHERE id = :id"),
                        {"name": original_name, "id": season_id},
                    )
            except (json.JSONDecodeError, TypeError):
                pass

    with op.batch_alter_table("seasons", schema=None) as batch_op:
        batch_op.drop_column("external_ids")
