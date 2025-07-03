"""fix_team_display_names

Revision ID: fix_team_display_names
Revises: add_team_display_name
Create Date: 2024-01-15 15:15:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fix_team_display_names'
down_revision = 'add_team_display_name'
branch_labels = None
depends_on = None

def upgrade():
    # Fix the display names with proper transformations
    op.execute("""
        UPDATE teams t
        SET display_name = 
            CASE 
                -- APTA Chicago: "Tennaqua - 22" -> "Tennaqua Series 22"
                WHEN t.team_name LIKE '% - %' THEN 
                    REPLACE(t.team_name, ' - ', ' Series ')
                -- NSTF: "Tennaqua S2B" -> "Tennaqua Series 2B"
                WHEN t.team_name LIKE '% S%' AND l.league_id = 'NSTF' THEN 
                    REPLACE(t.team_name, ' S', ' Series ')
                -- CNSWPL: "Tennaqua 1" -> "Tennaqua Series 1"
                WHEN t.team_name ~ '.*[0-9]+$' AND l.league_id = 'CNSWPL' THEN 
                    t.team_name || ' Series'
                ELSE t.team_name
            END
        FROM leagues l
        WHERE t.league_id = l.id;
    """)

def downgrade():
    # No downgrade needed - this just fixes display names
    pass 