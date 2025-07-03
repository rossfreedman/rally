"""fix_cnswpl_team_names

Revision ID: fix_cnswpl_team_names
Revises: fix_team_display_names
Create Date: 2024-01-15 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fix_cnswpl_team_names'
down_revision = 'fix_team_display_names'
branch_labels = None
depends_on = None

def upgrade():
    # Fix CNSWPL team display names to put "Series" before the number
    op.execute("""
        UPDATE teams t
        SET display_name = 
            CASE 
                -- CNSWPL: "Tennaqua 1" -> "Tennaqua Series 1"
                WHEN l.league_id = 'CNSWPL' AND t.team_name ~ '.*[0-9]+[a-zA-Z]*$' THEN
                    REGEXP_REPLACE(
                        t.team_name,
                        '([0-9]+[a-zA-Z]*)$',
                        'Series \1'
                    )
                ELSE t.display_name
            END
        FROM leagues l
        WHERE t.league_id = l.id;
    """)

def downgrade():
    # No downgrade needed - this just fixes display names
    pass 