"""Add date field to food table

Revision ID: 21f4a3730c62
Revises: e183fdc0b327
Create Date: 2025-09-19 22:13:34.785605

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '21f4a3730c62'
down_revision: Union[str, None] = 'e183fdc0b327'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add date column to food table
    op.add_column('food', sa.Column('date', sa.Date(), nullable=False, server_default=sa.text('CURRENT_DATE')))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove date column from food table
    op.drop_column('food', 'date')
