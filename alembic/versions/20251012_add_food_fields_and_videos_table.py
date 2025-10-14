"""add food fields and videos table

Revision ID: 20251012_food_videos
Revises: 06076132333a
Create Date: 2025-10-12 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251012_food_videos'
down_revision: Union[str, None] = '06076132333a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add mens_food/womens_food to food table and create videos table."""
    
    # ============================================================================
    # FOOD TABLE: Add mens_food and womens_food columns
    # ============================================================================
    
    # Add the new columns to food table
    op.execute("""
        ALTER TABLE food 
        ADD COLUMN IF NOT EXISTS mens_food TEXT,
        ADD COLUMN IF NOT EXISTS womens_food TEXT;
    """)
    
    # Make food_text nullable for backward compatibility
    op.alter_column('food', 'food_text',
               existing_type=sa.TEXT(),
               nullable=True)
    
    # Migrate existing data: copy food_text to mens_food for backward compatibility
    op.execute("""
        UPDATE food 
        SET mens_food = food_text 
        WHERE mens_food IS NULL AND food_text IS NOT NULL;
    """)
    
    # ============================================================================
    # VIDEOS TABLE: Create new table for team-specific training videos
    # ============================================================================
    
    op.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            url TEXT NOT NULL,
            players TEXT,
            date DATE,
            team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        -- Add indexes for performance
        CREATE INDEX IF NOT EXISTS idx_videos_team_id ON videos(team_id);
        CREATE INDEX IF NOT EXISTS idx_videos_date ON videos(date DESC);
        
        -- Add table comment
        COMMENT ON TABLE videos IS 'Stores team-specific training and practice videos';
        COMMENT ON COLUMN videos.name IS 'Display name for the video';
        COMMENT ON COLUMN videos.url IS 'YouTube or other video platform URL';
        COMMENT ON COLUMN videos.players IS 'Comma-separated list of player names';
        COMMENT ON COLUMN videos.date IS 'Date the video was recorded';
        COMMENT ON COLUMN videos.team_id IS 'Foreign key to teams table';
    """)


def downgrade() -> None:
    """Downgrade schema - remove mens_food/womens_food columns and drop videos table."""
    
    # Drop videos table
    op.execute("DROP TABLE IF EXISTS videos CASCADE;")
    
    # Remove food columns
    op.execute("ALTER TABLE food DROP COLUMN IF EXISTS mens_food, DROP COLUMN IF EXISTS womens_food;")
    
    # Make food_text NOT NULL again
    op.alter_column('food', 'food_text',
               existing_type=sa.TEXT(),
               nullable=False)

