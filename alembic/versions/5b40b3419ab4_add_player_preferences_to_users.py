"""add_player_preferences_to_users

Revision ID: 5b40b3419ab4
Revises: e2aff5194d57
Create Date: 2025-06-22 20:30:26.526042

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5b40b3419ab4"
down_revision: Union[str, None] = "e2aff5194d57"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add player preferences columns to users table
    op.add_column(
        "users", sa.Column("ad_deuce_preference", sa.String(length=50), nullable=True)
    )
    op.add_column(
        "users", sa.Column("dominant_hand", sa.String(length=20), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove player preferences columns from users table
    op.drop_column("users", "dominant_hand")
    op.drop_column("users", "ad_deuce_preference")
