"""merge_heads

Revision ID: 06076132333a
Revises: beer_table_only, match_scores_prev_seas
Create Date: 2025-10-11 15:41:41.449398

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '06076132333a'
down_revision: Union[str, None] = ('beer_table_only', 'match_scores_prev_seas')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
