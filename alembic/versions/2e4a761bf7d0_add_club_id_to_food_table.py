"""Add club_id to food table

Revision ID: 2e4a761bf7d0
Revises: 21f4a3730c62
Create Date: 2025-09-19 22:15:49.661480

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e4a761bf7d0'
down_revision: Union[str, None] = '21f4a3730c62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add club_id column to food table
    op.add_column('food', sa.Column('club_id', sa.Integer(), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key('fk_food_club_id', 'food', 'clubs', ['club_id'], ['id'])
    
    # Update existing records to have a default club_id (assuming club with id=1 exists)
    # This is a temporary solution - in production, you'd want to handle this more carefully
    op.execute("UPDATE food SET club_id = 1 WHERE club_id IS NULL")
    
    # Make club_id NOT NULL after updating existing records
    op.alter_column('food', 'club_id', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove foreign key constraint
    op.drop_constraint('fk_food_club_id', 'food', type_='foreignkey')
    
    # Remove club_id column
    op.drop_column('food', 'club_id')
