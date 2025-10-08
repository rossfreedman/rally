"""add_beer_table_only

Revision ID: beer_table_only
Revises: ac811b85a0e0
Create Date: 2025-09-21 13:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'beer_table_only'
down_revision: Union[str, None] = 'ac811b85a0e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add beer table only."""
    # Create beer table
    op.create_table('beer',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('beer_text', sa.Text(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('club_id', sa.Integer(), nullable=False),
        sa.Column('is_current_beer', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['club_id'], ['clubs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add indexes for better performance
    op.create_index('idx_beer_club_current_beer', 'beer', ['club_id', 'is_current_beer'], 
                   postgresql_where=sa.text('is_current_beer = TRUE'))
    op.create_index('idx_beer_club_date', 'beer', ['club_id', 'date'])


def downgrade() -> None:
    """Remove beer table."""
    op.drop_index('idx_beer_club_date', table_name='beer')
    op.drop_index('idx_beer_club_current_beer', table_name='beer')
    op.drop_table('beer')
