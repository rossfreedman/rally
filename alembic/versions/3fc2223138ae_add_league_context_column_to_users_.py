"""Add league_context column to users table only

Revision ID: 3fc2223138ae
Revises: 5b40b3419ab4
Create Date: 2025-06-25 21:48:10.877059

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3fc2223138ae'
down_revision: Union[str, None] = '5b40b3419ab4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add league_context column to users table."""
    # Add league_context column to users table
    op.add_column('users', sa.Column('league_context', sa.Integer(), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_users_league_context', 
        'users', 
        'leagues', 
        ['league_context'], 
        ['id']
    )


def downgrade() -> None:
    """Remove league_context column from users table."""
    # Drop foreign key constraint
    op.drop_constraint('fk_users_league_context', 'users', type_='foreignkey')
    
    # Drop the column
    op.drop_column('users', 'league_context')
