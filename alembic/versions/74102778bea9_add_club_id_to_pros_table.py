"""add_club_id_to_pros_table

Revision ID: 74102778bea9
Revises: 2b0c790cc4a1
Create Date: 2025-09-08 20:39:41.617938

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '74102778bea9'
down_revision: Union[str, None] = '2b0c790cc4a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
