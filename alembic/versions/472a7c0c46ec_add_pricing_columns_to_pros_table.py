"""add_pricing_columns_to_pros_table

Revision ID: 472a7c0c46ec
Revises: 1a9c5410ef91
Create Date: 2025-10-18 13:02:47.087183

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '472a7c0c46ec'
down_revision: Union[str, None] = '1a9c5410ef91'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add pricing columns to pros table for lesson scheduling."""
    # Add pricing columns for different lesson types
    op.add_column('pros', sa.Column('private_30min_price', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('pros', sa.Column('private_45min_price', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('pros', sa.Column('private_60min_price', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('pros', sa.Column('semi_private_60min_price', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('pros', sa.Column('group_3players_price', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('pros', sa.Column('group_4plus_price', sa.Numeric(precision=10, scale=2), nullable=True))
    
    # Populate pricing data for existing pros
    # Olga Martinsone pricing
    op.execute("""
        UPDATE pros 
        SET private_30min_price = 55.00,
            private_45min_price = 85.00,
            private_60min_price = 100.00,
            semi_private_60min_price = 55.00,
            group_3players_price = 40.00,
            group_4plus_price = 35.00
        WHERE name = 'Olga Martinsone' AND is_active = true
    """)
    
    # Mike Simms pricing
    op.execute("""
        UPDATE pros 
        SET private_30min_price = 50.00,
            private_45min_price = 75.00,
            private_60min_price = 90.00,
            semi_private_60min_price = 50.00,
            group_3players_price = 35.00,
            group_4plus_price = 30.00
        WHERE name = 'Mike Simms' AND is_active = true
    """)
    
    # Default pricing for any other active pros
    op.execute("""
        UPDATE pros 
        SET private_30min_price = 50.00,
            private_45min_price = 75.00,
            private_60min_price = 90.00,
            semi_private_60min_price = 50.00,
            group_3players_price = 35.00,
            group_4plus_price = 30.00
        WHERE is_active = true 
        AND private_30min_price IS NULL
    """)


def downgrade() -> None:
    """Remove pricing columns from pros table."""
    op.drop_column('pros', 'group_4plus_price')
    op.drop_column('pros', 'group_3players_price')
    op.drop_column('pros', 'semi_private_60min_price')
    op.drop_column('pros', 'private_60min_price')
    op.drop_column('pros', 'private_45min_price')
    op.drop_column('pros', 'private_30min_price')
