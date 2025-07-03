"""fix_cnswpl_team_names_final

Revision ID: fix_cnswpl_team_names_final
Revises: fix_cnswpl_team_names
Create Date: 2024-01-15 15:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fix_cnswpl_team_names_final'
down_revision = 'fix_cnswpl_team_names'
branch_labels = None
depends_on = None

def upgrade():
    # Fix CNSWPL team display names with a simpler approach
    op.execute("""
        WITH team_parts AS (
            SELECT 
                t.id,
                t.team_name,
                -- Extract the numeric suffix
                REGEXP_MATCHES(t.team_name, '(.*?)([0-9]+[a-zA-Z]*)$') as parts
            FROM teams t
            JOIN leagues l ON t.league_id = l.id
            WHERE l.league_id = 'CNSWPL'
        )
        UPDATE teams t
        SET display_name = 
            CASE 
                WHEN tp.parts IS NOT NULL THEN
                    (tp.parts[1] || 'Series ' || tp.parts[2])
                ELSE t.team_name
            END
        FROM team_parts tp
        WHERE t.id = tp.id;
    """)

def downgrade():
    # No downgrade needed - this just fixes display names
    pass 