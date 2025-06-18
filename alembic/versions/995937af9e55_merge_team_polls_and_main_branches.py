"""merge_team_polls_and_main_branches

Revision ID: 995937af9e55
Revises: fddbba0e1328, add_team_polls_001
Create Date: 2025-06-17 19:49:25.525207

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '995937af9e55'
down_revision: Union[str, None] = ('fddbba0e1328', 'add_team_polls_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
