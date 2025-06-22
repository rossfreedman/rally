"""clear_all_data

Revision ID: 07d5e9498cf9
Revises: import_all_data
Create Date: 2025-06-12 16:05:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "07d5e9498cf9"
down_revision = "import_all_data"  # Updated to point to the correct previous migration
branch_labels = None
depends_on = None


def upgrade():
    # Use TRUNCATE CASCADE to handle all dependencies
    op.execute(
        """
        TRUNCATE TABLE 
            match_scores, schedule, player_history, player_availability,
            series_leagues, club_leagues, players, series, clubs,
            leagues, users, user_activity_logs, user_instructions,
            user_player_associations, series_stats
        CASCADE
    """
    )


def downgrade():
    # No downgrade possible for data deletion
    pass
