"""Add food table for chef notifications

Revision ID: e183fdc0b327
Revises: 74102778bea9
Create Date: 2025-09-19 22:13:15.556574

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e183fdc0b327'
down_revision: Union[str, None] = '74102778bea9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create food table for chef notifications
    op.create_table('food',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('food_text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop food table
    op.drop_table('food')
