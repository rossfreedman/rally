"""cleanup_orphaned_series_name_mappings_table

Revision ID: a7bcfd488790
Revises: 5a3fa8d90683
Create Date: 2025-07-05 07:16:34.581439

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7bcfd488790'
down_revision: Union[str, None] = '5a3fa8d90683'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Cleanup orphaned series_name_mappings table.
    
    This migration safely drops the old series_name_mappings table that should have
    been removed in a previous migration but wasn't properly cleaned up on some environments.
    
    The table is only dropped if:
    1. The new series.display_name column exists
    2. Series records have display names populated
    3. The old table still exists
    """
    
    # Execute the cleanup with proper safety checks
    op.execute("""
        DO $$
        BEGIN
            -- Safety check 1: Ensure display_name column exists
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'series' AND column_name = 'display_name'
            ) THEN
                RAISE EXCEPTION 'Cannot drop series_name_mappings: series.display_name column does not exist. Migration dependency error.';
            END IF;
            
            -- Safety check 2: Ensure series have display names populated
            IF (SELECT COUNT(*) FROM series WHERE display_name IS NOT NULL) = 0 THEN
                RAISE EXCEPTION 'Cannot drop series_name_mappings: No series have display names populated. Data migration incomplete.';
            END IF;
            
            -- Safety check 3: Check if old table exists before trying to drop it
            IF EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'series_name_mappings'
            ) THEN
                -- Log what we're doing
                RAISE NOTICE '🗑️  Dropping orphaned series_name_mappings table (should have been removed in previous migration)';
                
                -- Get count for logging
                DECLARE
                    old_mappings_count INTEGER;
                BEGIN
                    SELECT COUNT(*) INTO old_mappings_count FROM series_name_mappings;
                    RAISE NOTICE '📊 Removing % obsolete mapping records', old_mappings_count;
                END;
                
                -- Drop the table with CASCADE to handle any remaining dependencies
                DROP TABLE series_name_mappings CASCADE;
                
                -- Verify it's gone
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = 'series_name_mappings'
                ) THEN
                    RAISE NOTICE '✅ Successfully removed orphaned series_name_mappings table';
                ELSE
                    RAISE EXCEPTION 'Failed to drop series_name_mappings table';
                END IF;
            ELSE
                RAISE NOTICE 'ℹ️  series_name_mappings table already does not exist - no cleanup needed';
            END IF;
            
            -- Final verification
            DECLARE
                series_count INTEGER;
                display_name_count INTEGER;
            BEGIN
                SELECT COUNT(*) INTO series_count FROM series;
                SELECT COUNT(*) INTO display_name_count FROM series WHERE display_name IS NOT NULL;
                
                RAISE NOTICE '🎉 Migration successful: % series with % display names', series_count, display_name_count;
                RAISE NOTICE '✅ Series name mapping now uses series.display_name column exclusively';
            END;
        END $$;
    """)


def downgrade() -> None:
    """
    Downgrade by recreating the series_name_mappings table.
    
    This is primarily for rollback safety, though in practice this migration
    should not need to be rolled back since it's just cleaning up orphaned data.
    """
    
    # Recreate the mapping table structure
    op.create_table('series_name_mappings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('league_id', sa.String(50), nullable=False),
        sa.Column('user_series_name', sa.String(100), nullable=False),
        sa.Column('database_series_name', sa.String(100), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('league_id', 'user_series_name')
    )
    
    # Migrate display names back to mappings (if needed for rollback)
    op.execute("""
        -- Only migrate back if the necessary tables exist
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'series_leagues') THEN
                INSERT INTO series_name_mappings (league_id, user_series_name, database_series_name)
                SELECT 
                    l.league_id,
                    s.display_name,
                    s.name
                FROM series s
                JOIN series_leagues sl ON s.id = sl.series_id
                JOIN leagues l ON sl.league_id = l.id
                WHERE s.name != s.display_name;
                
                RAISE NOTICE 'Recreated series_name_mappings table for rollback';
            ELSE
                RAISE NOTICE 'Could not fully recreate mappings - series_leagues table not found';
            END IF;
        END $$;
    """)
