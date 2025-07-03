"""add_team_display_name

Revision ID: add_team_display_name
Revises: 7a812bc7dcb7
Create Date: 2024-01-15 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_team_display_name'
down_revision = '7a812bc7dcb7'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Add display_name column to teams table
    op.add_column('teams', sa.Column('display_name', sa.String(255)))
    
    # 2. Migrate existing team names to display names
    op.execute("""
        -- Update teams table with display names
        UPDATE teams t
        SET display_name = COALESCE(
            (
                SELECT m.user_input_format
                FROM team_format_mappings m
                JOIN leagues l ON m.league_id = l.league_id
                WHERE m.database_series_format = t.team_name
                LIMIT 1
            ),
            -- Default transformation based on league format
            CASE 
                -- APTA Chicago: "Tennaqua - 22" -> "Tennaqua Series 22"
                WHEN t.team_name LIKE '% - %' THEN 
                    REPLACE(
                        t.team_name, 
                        ' - ', 
                        ' Series '
                    )
                -- NSTF: "Tennaqua S2B" -> "Tennaqua Series 2B"
                WHEN t.team_name LIKE '% S%' AND l.league_id = 'NSTF' THEN 
                    REPLACE(
                        t.team_name, 
                        ' S', 
                        ' Series '
                    )
                -- CNSWPL: "Tennaqua 1" -> "Tennaqua Series 1"
                WHEN t.team_name ~ '[0-9]$' AND l.league_id = 'CNSWPL' THEN 
                    REGEXP_REPLACE(
                        t.team_name, 
                        '([0-9]+)$', 
                        ' Series \1'
                    )
                ELSE t.team_name
            END
        )
        FROM leagues l
        WHERE t.league_id = l.id;
        
        -- Make display_name NOT NULL after migration
        ALTER TABLE teams ALTER COLUMN display_name SET NOT NULL;
        
        -- Create an index for faster lookups
        CREATE INDEX idx_teams_display_name ON teams(display_name);
        
        -- Drop the now-redundant mapping table
        DROP TABLE IF EXISTS team_format_mappings;
    """)

def downgrade():
    # 1. Recreate the mapping table
    op.create_table('team_format_mappings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('league_id', sa.String(50), nullable=False),
        sa.Column('user_input_format', sa.String(100), nullable=False),
        sa.Column('database_series_format', sa.String(100), nullable=False),
        sa.Column('mapping_type', sa.String(50), server_default='team_mapping', nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 2. Migrate display names back to mappings
    op.execute("""
        INSERT INTO team_format_mappings (league_id, user_input_format, database_series_format)
        SELECT 
            l.league_id,
            t.display_name,
            t.team_name
        FROM teams t
        JOIN leagues l ON t.league_id = l.id
        WHERE t.team_name != t.display_name
    """)
    
    # 3. Drop the display_name column
    op.drop_column('teams', 'display_name') 