-- Migration: Add Captain Messages Table
-- Date: 2025-07-13 12:00:00
-- Description: Adds captain_messages table for team captain messages

BEGIN;

CREATE TABLE IF NOT EXISTS captain_messages (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(id),
    captain_user_id INTEGER NOT NULL REFERENCES users(id),
    message TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for fast lookup by team
CREATE INDEX IF NOT EXISTS idx_captain_messages_team_id ON captain_messages(team_id);

-- Add comment for documentation
COMMENT ON TABLE captain_messages IS 'Stores captain messages for teams. These messages appear in the notifications feed for all team members.';

COMMIT; 