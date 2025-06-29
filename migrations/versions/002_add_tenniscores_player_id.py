"""add tenniscores_player_id to users

Revision ID: 003_add_player_id
Revises: 22cdc4d8bba3
Create Date: 2024-12-18

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "003_add_player_id"
down_revision = "22cdc4d8bba3"
branch_labels = None
depends_on = None


def upgrade():
    # Add tenniscores_player_id column to users table
    op.add_column(
        "users", sa.Column("tenniscores_player_id", sa.String(255), nullable=True)
    )

    # Create index for faster lookups
    op.create_index(
        "idx_users_tenniscores_player_id", "users", ["tenniscores_player_id"]
    )


def downgrade():
    # Remove index first
    op.drop_index("idx_users_tenniscores_player_id", "users")

    # Remove column
    op.drop_column("users", "tenniscores_player_id")
