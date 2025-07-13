-- Migration: Add Lineup Escrow and Saved Lineups Tables
-- Date: 2025-01-15 12:00:00
-- Description: Adds tables for lineup escrow functionality and saved lineups

-- Create lineup_escrow table
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
);

-- Create lineup_escrow_views table
CREATE TABLE IF NOT EXISTS lineup_escrow_views (
    id SERIAL PRIMARY KEY,
    escrow_id INTEGER NOT NULL REFERENCES lineup_escrow(id),
    viewer_user_id INTEGER REFERENCES users(id),
    viewer_contact VARCHAR(255) NOT NULL,
    viewed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ip_address VARCHAR(45)
);

-- Create saved_lineups table
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
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_lineup_escrow_token ON lineup_escrow(escrow_token);
CREATE INDEX IF NOT EXISTS idx_lineup_escrow_status ON lineup_escrow(status);
CREATE INDEX IF NOT EXISTS idx_lineup_escrow_initiator ON lineup_escrow(initiator_user_id);
CREATE INDEX IF NOT EXISTS idx_lineup_escrow_views_escrow_id ON lineup_escrow_views(escrow_id);
CREATE INDEX IF NOT EXISTS idx_saved_lineups_user_team ON saved_lineups(user_id, team_id);
CREATE INDEX IF NOT EXISTS idx_saved_lineups_active ON saved_lineups(is_active);

-- Add comments for documentation
COMMENT ON TABLE lineup_escrow IS 'Stores lineup escrow sessions for fair lineup disclosure between captains';
COMMENT ON TABLE lineup_escrow_views IS 'Tracks who has viewed lineup escrow results';
COMMENT ON TABLE saved_lineups IS 'Stores saved lineup configurations for users and teams'; 