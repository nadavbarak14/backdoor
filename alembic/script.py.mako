"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """
    Apply the migration.

    This function contains the operations to upgrade the database schema
    to this revision. Operations should be idempotent where possible.
    """
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """
    Revert the migration.

    This function contains the operations to downgrade the database schema
    from this revision. It should exactly reverse the upgrade operations.
    """
    ${downgrades if downgrades else "pass"}
