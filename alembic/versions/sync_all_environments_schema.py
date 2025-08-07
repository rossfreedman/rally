"""sync_all_environments_schema

Revision ID: sync_all_env_001
Revises: c28892a55e1d
Create Date: 2025-08-04 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'sync_all_env_001'
down_revision: Union[str, None] = 'c28892a55e1d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to sync all environments."""
    
    # 1. Create missing tables that exist in local but not in staging/production
    
    # Create user_contexts table (if not exists)
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_contexts (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            league_id INTEGER REFERENCES leagues(id),
            team_id INTEGER REFERENCES teams(id),
            series_id INTEGER REFERENCES series(id),
            club VARCHAR(255),
            context_type VARCHAR(50) DEFAULT 'current',
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE(user_id, context_type)
        )
    """)
    
    # Create practice_times table (if not exists)
    op.execute("""
        CREATE TABLE IF NOT EXISTS practice_times (
            id SERIAL PRIMARY KEY,
            team_id INTEGER NOT NULL REFERENCES teams(id),
            practice_date DATE NOT NULL,
            start_time TIME,
            end_time TIME,
            court_number INTEGER,
            notes TEXT,
            created_by INTEGER REFERENCES users(id),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE(team_id, practice_date)
        )
    """)
    
    # Create test_etl_runs table (if not exists)
    op.execute("""
        CREATE TABLE IF NOT EXISTS test_etl_runs (
            id SERIAL PRIMARY KEY,
            run_name VARCHAR(255) NOT NULL,
            start_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            end_time TIMESTAMP WITH TIME ZONE,
            status VARCHAR(50) DEFAULT 'running',
            records_processed INTEGER DEFAULT 0,
            errors_count INTEGER DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    
    # Create practice_times_corrupted_backup table (if not exists)
    op.execute("""
        CREATE TABLE IF NOT EXISTS practice_times_corrupted_backup (
            id SERIAL PRIMARY KEY,
            team_id INTEGER,
            practice_date DATE,
            start_time TIME,
            end_time TIME,
            court_number INTEGER,
            notes TEXT,
            created_by INTEGER,
            created_at TIMESTAMP WITH TIME ZONE,
            backup_reason VARCHAR(255) DEFAULT 'corrupted_data',
            original_id INTEGER
        )
    """)
    
    # Create enhanced_league_contexts_backup table (if not exists)
    op.execute("""
        CREATE TABLE IF NOT EXISTS enhanced_league_contexts_backup (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            league_id INTEGER,
            team_id INTEGER,
            series_id INTEGER,
            club VARCHAR(255),
            context_type VARCHAR(50),
            is_active BOOLEAN,
            created_at TIMESTAMP WITH TIME ZONE,
            updated_at TIMESTAMP WITH TIME ZONE,
            backup_reason VARCHAR(255) DEFAULT 'enhancement_backup',
            original_id INTEGER
        )
    """)
    
    # 2. Add missing columns to existing tables
    
    # Add missing columns to lineup_escrow table
    op.execute("""
        ALTER TABLE lineup_escrow 
        ADD COLUMN IF NOT EXISTS recipient_team_id INTEGER REFERENCES teams(id)
    """)
    
    op.execute("""
        ALTER TABLE lineup_escrow 
        ADD COLUMN IF NOT EXISTS initiator_team_id INTEGER REFERENCES teams(id)
    """)
    
    # Add missing columns to user_player_associations table
    op.execute("""
        ALTER TABLE user_player_associations 
        ADD COLUMN IF NOT EXISTS is_primary BOOLEAN DEFAULT FALSE
    """)
    
    # Add missing columns to match_scores table
    op.execute("""
        ALTER TABLE match_scores 
        ADD COLUMN IF NOT EXISTS match_id VARCHAR(255)
    """)
    
    op.execute("""
        ALTER TABLE match_scores 
        ADD COLUMN IF NOT EXISTS tenniscores_match_id VARCHAR(255)
    """)
    
    # Add missing columns to users table
    op.execute("""
        ALTER TABLE users 
        ADD COLUMN IF NOT EXISTS team_id INTEGER REFERENCES teams(id)
    """)
    
    op.execute("""
        ALTER TABLE users 
        ADD COLUMN IF NOT EXISTS notifications_hidden BOOLEAN DEFAULT FALSE
    """)
    
    # 3. Create indexes for new tables
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_contexts_user_id ON user_contexts(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_contexts_active ON user_contexts(is_active)")
    
    op.execute("CREATE INDEX IF NOT EXISTS idx_practice_times_team_date ON practice_times(team_id, practice_date)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_practice_times_date ON practice_times(practice_date)")
    
    op.execute("CREATE INDEX IF NOT EXISTS idx_test_etl_runs_status ON test_etl_runs(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_test_etl_runs_created ON test_etl_runs(created_at)")
    
    # 4. Create indexes for new columns
    op.execute("CREATE INDEX IF NOT EXISTS idx_lineup_escrow_recipient_team ON lineup_escrow(recipient_team_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_lineup_escrow_initiator_team ON lineup_escrow(initiator_team_id)")
    
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_player_associations_primary ON user_player_associations(is_primary)")
    
    op.execute("CREATE INDEX IF NOT EXISTS idx_match_scores_match_id ON match_scores(match_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_match_scores_tenniscores_match_id ON match_scores(tenniscores_match_id)")
    
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_team_id ON users(team_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_notifications_hidden ON users(notifications_hidden)")


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes for new columns
    op.execute("DROP INDEX IF EXISTS idx_users_notifications_hidden")
    op.execute("DROP INDEX IF EXISTS idx_users_team_id")
    
    op.execute("DROP INDEX IF EXISTS idx_match_scores_tenniscores_match_id")
    op.execute("DROP INDEX IF EXISTS idx_match_scores_match_id")
    
    op.execute("DROP INDEX IF EXISTS idx_user_player_associations_primary")
    
    op.execute("DROP INDEX IF EXISTS idx_lineup_escrow_initiator_team")
    op.execute("DROP INDEX IF EXISTS idx_lineup_escrow_recipient_team")
    
    # Drop indexes for new tables
    op.execute("DROP INDEX IF EXISTS idx_test_etl_runs_created")
    op.execute("DROP INDEX IF EXISTS idx_test_etl_runs_status")
    
    op.execute("DROP INDEX IF EXISTS idx_practice_times_date")
    op.execute("DROP INDEX IF EXISTS idx_practice_times_team_date")
    
    op.execute("DROP INDEX IF EXISTS idx_user_contexts_active")
    op.execute("DROP INDEX IF EXISTS idx_user_contexts_user_id")
    
    # Drop columns (in reverse order)
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS notifications_hidden")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS team_id")
    
    op.execute("ALTER TABLE match_scores DROP COLUMN IF EXISTS tenniscores_match_id")
    op.execute("ALTER TABLE match_scores DROP COLUMN IF EXISTS match_id")
    
    op.execute("ALTER TABLE user_player_associations DROP COLUMN IF EXISTS is_primary")
    
    op.execute("ALTER TABLE lineup_escrow DROP COLUMN IF EXISTS initiator_team_id")
    op.execute("ALTER TABLE lineup_escrow DROP COLUMN IF EXISTS recipient_team_id")
    
    # Drop tables (in reverse order due to foreign key constraints)
    op.execute("DROP TABLE IF EXISTS enhanced_league_contexts_backup")
    op.execute("DROP TABLE IF EXISTS practice_times_corrupted_backup")
    op.execute("DROP TABLE IF EXISTS test_etl_runs")
    op.execute("DROP TABLE IF EXISTS practice_times")
    op.execute("DROP TABLE IF EXISTS user_contexts")
