"""add_is_current_menu_to_food_table

Revision ID: ac811b85a0e0
Revises: 2e4a761bf7d0
Create Date: 2025-09-20 08:44:17.460268

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ac811b85a0e0'
down_revision: Union[str, None] = '2e4a761bf7d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('food', sa.Column('is_current_menu', sa.Boolean(), nullable=False, server_default=sa.text('false')))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('food', 'is_current_menu')
