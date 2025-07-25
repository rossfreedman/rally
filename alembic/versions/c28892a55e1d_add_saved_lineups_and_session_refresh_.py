"""add_saved_lineups_and_session_refresh_tables

Revision ID: c28892a55e1d
Revises: 20484d947d9d
Create Date: 2025-07-25 13:05:04.995239

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c28892a55e1d'
down_revision: Union[str, None] = '20484d947d9d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create saved_lineups table (if not exists)
    op.execute("""
        CREATE TABLE IF NOT EXISTS saved_lineups (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            team_id INTEGER NOT NULL REFERENCES teams(id),
            lineup_name VARCHAR(255) NOT NULL,
            lineup_data TEXT NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE(user_id, team_id, lineup_name)
        )
    """)

    # Create lineup_escrow table (if not exists)
    op.execute("""
        CREATE TABLE IF NOT EXISTS lineup_escrow (
            id SERIAL PRIMARY KEY,
            escrow_token VARCHAR(255) NOT NULL UNIQUE,
            initiator_user_id INTEGER NOT NULL REFERENCES users(id),
            recipient_name VARCHAR(255) NOT NULL,
            recipient_contact VARCHAR(255) NOT NULL,
            contact_type VARCHAR(20) NOT NULL,
            initiator_lineup TEXT NOT NULL,
            recipient_lineup TEXT,
            status VARCHAR(50) NOT NULL DEFAULT 'pending',
            initiator_submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            recipient_submitted_at TIMESTAMP WITH TIME ZONE,
            expires_at TIMESTAMP WITH TIME ZONE,
            subject VARCHAR(255),
            message_body TEXT NOT NULL,
            initiator_notified BOOLEAN DEFAULT FALSE,
            recipient_notified BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    # Create lineup_escrow_views table (if not exists)
    op.execute("""
        CREATE TABLE IF NOT EXISTS lineup_escrow_views (
            id SERIAL PRIMARY KEY,
            escrow_id INTEGER NOT NULL REFERENCES lineup_escrow(id),
            viewer_user_id INTEGER REFERENCES users(id),
            viewer_contact VARCHAR(255) NOT NULL,
            viewed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            ip_address VARCHAR(45)
        )
    """)

    # Create user_session_refresh_signals table (if not exists) 
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_session_refresh_signals (
            user_id INTEGER PRIMARY KEY REFERENCES users(id),
            email VARCHAR(255) NOT NULL,
            old_league_id INTEGER,
            new_league_id INTEGER,
            league_name VARCHAR(255),
            refresh_reason VARCHAR(255) DEFAULT 'etl_league_id_change',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            refreshed_at TIMESTAMP WITH TIME ZONE,
            is_refreshed BOOLEAN DEFAULT FALSE
        )
    """)

    # Create indexes if they don't exist
    op.execute("CREATE INDEX IF NOT EXISTS idx_saved_lineups_user_team ON saved_lineups(user_id, team_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_saved_lineups_active ON saved_lineups(is_active)")
    
    op.execute("CREATE INDEX IF NOT EXISTS idx_lineup_escrow_token ON lineup_escrow(escrow_token)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_lineup_escrow_status ON lineup_escrow(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_lineup_escrow_initiator ON lineup_escrow(initiator_user_id)")
    
    op.execute("CREATE INDEX IF NOT EXISTS idx_lineup_escrow_views_escrow_id ON lineup_escrow_views(escrow_id)")
    
    op.execute("CREATE INDEX IF NOT EXISTS idx_session_refresh_email ON user_session_refresh_signals(email)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_session_refresh_refreshed ON user_session_refresh_signals(is_refreshed)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_session_refresh_created ON user_session_refresh_signals(created_at)")


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS idx_session_refresh_created")
    op.execute("DROP INDEX IF EXISTS idx_session_refresh_refreshed") 
    op.execute("DROP INDEX IF EXISTS idx_session_refresh_email")
    
    op.execute("DROP INDEX IF EXISTS idx_lineup_escrow_views_escrow_id")
    
    op.execute("DROP INDEX IF EXISTS idx_lineup_escrow_initiator")
    op.execute("DROP INDEX IF EXISTS idx_lineup_escrow_status")
    op.execute("DROP INDEX IF EXISTS idx_lineup_escrow_token")
    
    op.execute("DROP INDEX IF EXISTS idx_saved_lineups_active")
    op.execute("DROP INDEX IF EXISTS idx_saved_lineups_user_team")

    # Drop tables (in reverse order due to foreign key constraints)
    op.execute("DROP TABLE IF EXISTS user_session_refresh_signals")
    op.execute("DROP TABLE IF EXISTS lineup_escrow_views")
    op.execute("DROP TABLE IF EXISTS lineup_escrow")
    op.execute("DROP TABLE IF EXISTS saved_lineups")
