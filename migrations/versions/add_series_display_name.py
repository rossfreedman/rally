"""Add display_name to series table

Revision ID: add_series_display_name
Revises: 001_add_club_logo_filename
Create Date: 2024-01-15 14:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_series_display_name'
down_revision = '001_add_club_logo_filename'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Add display_name column to series table
    op.add_column('series', sa.Column('display_name', sa.String(255)))
    
    # 2. Migrate existing mappings
    op.execute("""
        -- Update series table with display names from mappings
        UPDATE series s
        SET display_name = COALESCE(
            (
                SELECT m.user_series_name
                FROM series_name_mappings m
                JOIN leagues l ON m.league_id = l.league_id
                WHERE m.database_series_name = s.name
                LIMIT 1
            ),
            -- Default transformation if no mapping exists
            CASE 
                WHEN s.name LIKE 'Chicago %' THEN REPLACE(s.name, 'Chicago ', 'Series ')
                WHEN s.name LIKE 'Division %' THEN REPLACE(s.name, 'Division ', 'Series ')
                WHEN s.name LIKE 'S%' AND s.name NOT LIKE 'Series %' THEN REPLACE(s.name, 'S', 'Series ')
                ELSE s.name
            END
        );
        
        -- Make display_name NOT NULL after migration
        ALTER TABLE series ALTER COLUMN display_name SET NOT NULL;
        
        -- Create an index for faster lookups
        CREATE INDEX idx_series_display_name ON series(display_name);
        
        -- Drop the now-redundant mapping table
        DROP TABLE series_name_mappings;
    """)

def downgrade():
    # 1. Recreate the mapping table
    op.create_table('series_name_mappings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('league_id', sa.String(50), nullable=False),
        sa.Column('database_series_name', sa.String(255), nullable=False),
        sa.Column('user_series_name', sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 2. Migrate display names back to mappings
    op.execute("""
        INSERT INTO series_name_mappings (league_id, database_series_name, user_series_name)
        SELECT 
            l.league_id,
            s.name,
            s.display_name
        FROM series s
        JOIN series_leagues sl ON s.id = sl.series_id
        JOIN leagues l ON sl.league_id = l.id
        WHERE s.name != s.display_name
    """)
    
    # 3. Drop the display_name column
    op.drop_column('series', 'display_name') 