"""add_series_id_to_series_stats

Revision ID: 5a3fa8d90683
Revises: 6f517e10b193
Create Date: 2025-07-04 14:11:27.014641

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5a3fa8d90683'
down_revision: Union[str, None] = '6f517e10b193'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add series_id foreign key column to series_stats table."""
    # Add series_id column to series_stats table
    op.add_column('series_stats', sa.Column('series_id', sa.Integer(), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key('fk_series_stats_series_id', 'series_stats', 'series', ['series_id'], ['id'])
    
    # Create index for performance
    op.create_index('idx_series_stats_series_id', 'series_stats', ['series_id'])


def downgrade() -> None:
    """Remove series_id foreign key column from series_stats table."""
    # Drop index
    op.drop_index('idx_series_stats_series_id', table_name='series_stats')
    
    # Drop foreign key constraint
    op.drop_constraint('fk_series_stats_series_id', 'series_stats', type_='foreignkey')
    
    # Drop column
    op.drop_column('series_stats', 'series_id')
