"""remove_deprecated_user_foreign_keys

Revision ID: 8bb36e1c74da
Revises: 07d5e9498cf9
Create Date: 2025-06-12 22:45:30.189890

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8bb36e1c74da"
down_revision: Union[str, None] = "07d5e9498cf9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Remove deprecated foreign key fields from users table.

    These fields were used when there was a one-to-one relationship between users and players,
    but now we use the user_player_associations table for a proper many-to-many relationship.
    """
    # Drop indexes first
    try:
        op.drop_index("idx_users_league_id", table_name="users")
    except Exception:
        pass  # Index may not exist

    try:
        op.drop_index("idx_users_tenniscores_player_id", table_name="users")
    except Exception:
        pass  # Index may not exist

    # Drop foreign key constraints
    try:
        op.drop_constraint("fk_users_club_id", "users", type_="foreignkey")
    except Exception:
        pass  # Constraint may not exist

    try:
        op.drop_constraint("fk_users_series_id", "users", type_="foreignkey")
    except Exception:
        pass  # Constraint may not exist

    try:
        op.drop_constraint("users_club_id_fkey1", "users", type_="foreignkey")
    except Exception:
        pass  # Constraint may not exist

    try:
        op.drop_constraint("users_league_id_fkey", "users", type_="foreignkey")
    except Exception:
        pass  # Constraint may not exist

    try:
        op.drop_constraint("users_series_id_fkey1", "users", type_="foreignkey")
    except Exception:
        pass  # Constraint may not exist

    # Remove the deprecated columns
    op.drop_column("users", "series_id")
    op.drop_column("users", "league_id")
    op.drop_column("users", "club_id")
    op.drop_column("users", "tenniscores_player_id")


def downgrade() -> None:
    """
    Re-add the deprecated foreign key fields to users table.
    Note: This will lose data since the fields are being removed in upgrade.
    """
    # Add back the deprecated columns
    op.add_column("users", sa.Column("series_id", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("league_id", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("club_id", sa.Integer(), nullable=True))
    op.add_column(
        "users", sa.Column("tenniscores_player_id", sa.String(255), nullable=True)
    )

    # Re-add foreign key constraints
    try:
        op.create_foreign_key(
            "users_series_id_fkey", "users", "series", ["series_id"], ["id"]
        )
    except Exception:
        pass  # May fail if series table doesn't exist

    try:
        op.create_foreign_key(
            "users_league_id_fkey", "users", "leagues", ["league_id"], ["id"]
        )
    except Exception:
        pass  # May fail if leagues table doesn't exist

    try:
        op.create_foreign_key(
            "users_club_id_fkey", "users", "clubs", ["club_id"], ["id"]
        )
    except Exception:
        pass  # May fail if clubs table doesn't exist

    # Re-add indexes
    try:
        op.create_index("idx_users_series_id", "users", ["series_id"], unique=False)
    except Exception:
        pass

    try:
        op.create_index("idx_users_league_id", "users", ["league_id"], unique=False)
    except Exception:
        pass

    try:
        op.create_index("idx_users_club_id", "users", ["club_id"], unique=False)
    except Exception:
        pass

    try:
        op.create_index(
            "idx_users_tenniscores_player_id",
            "users",
            ["tenniscores_player_id"],
            unique=False,
        )
    except Exception:
        pass
