"""replace_pricing_columns_with_text_field

Revision ID: e1dbd53d0194
Revises: 472a7c0c46ec
Create Date: 2025-10-18 13:09:15.747047

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1dbd53d0194'
down_revision: Union[str, None] = '472a7c0c46ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Replace individual pricing columns with single pricing_info text field."""
    # Add pricing_info TEXT column
    op.add_column('pros', sa.Column('pricing_info', sa.Text(), nullable=True))
    
    # Populate pricing_info for Olga Martinsone (custom pricing)
    op.execute("""
        UPDATE pros 
        SET pricing_info = 'Private Lessons:
• 30 minutes – $55
• 45 minutes – $85
• 60 minutes – $100
Semi-Private (2 players):
• 60 minutes – $55 per person
Group Lessons:
• 3 players + pro – $40 per person
• 4+ players + pro – $35 per person'
        WHERE name = 'Olga Martinsone' AND is_active = true
    """)
    
    # Populate pricing_info for Mike Simms and others (default pricing)
    op.execute("""
        UPDATE pros 
        SET pricing_info = 'Private Lessons:
• 30 minutes – $50
• 45 minutes – $75
• 60 minutes – $90
Semi-Private (2 players):
• 60 minutes – $50 per person
Group Lessons:
• 3 players + pro – $35 per person
• 4+ players + pro – $30 per person'
        WHERE is_active = true 
        AND pricing_info IS NULL
    """)
    
    # Drop the individual pricing columns
    op.drop_column('pros', 'private_30min_price')
    op.drop_column('pros', 'private_45min_price')
    op.drop_column('pros', 'private_60min_price')
    op.drop_column('pros', 'semi_private_60min_price')
    op.drop_column('pros', 'group_3players_price')
    op.drop_column('pros', 'group_4plus_price')


def downgrade() -> None:
    """Restore individual pricing columns from pricing_info text field."""
    # Add back the individual pricing columns
    op.add_column('pros', sa.Column('private_30min_price', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('pros', sa.Column('private_45min_price', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('pros', sa.Column('private_60min_price', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('pros', sa.Column('semi_private_60min_price', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('pros', sa.Column('group_3players_price', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('pros', sa.Column('group_4plus_price', sa.Numeric(precision=10, scale=2), nullable=True))
    
    # Drop pricing_info column
    op.drop_column('pros', 'pricing_info')
