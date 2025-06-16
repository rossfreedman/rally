-- Add Team Polls Tables
-- Created: 2024-01-01
-- Description: Creates tables for team polls feature: polls, poll_choices, and poll_responses

-- Create polls table to store each poll
CREATE TABLE IF NOT EXISTS polls (
    id SERIAL PRIMARY KEY,
    team_id INTEGER, -- Will reference teams table when available
    created_by INTEGER REFERENCES users(id),
    question TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create poll_choices table to store multiple-choice options for each poll
CREATE TABLE IF NOT EXISTS poll_choices (
    id SERIAL PRIMARY KEY,
    poll_id INTEGER REFERENCES polls(id) ON DELETE CASCADE,
    choice_text TEXT NOT NULL
);

-- Create poll_responses table to store each player's response
CREATE TABLE IF NOT EXISTS poll_responses (
    id SERIAL PRIMARY KEY,
    poll_id INTEGER REFERENCES polls(id) ON DELETE CASCADE,
    choice_id INTEGER REFERENCES poll_choices(id),
    player_id INTEGER REFERENCES players(id),
    responded_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (poll_id, player_id) -- only one vote per player per poll
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_polls_created_by ON polls(created_by);
CREATE INDEX IF NOT EXISTS idx_polls_team_id ON polls(team_id);
CREATE INDEX IF NOT EXISTS idx_poll_choices_poll_id ON poll_choices(poll_id);
CREATE INDEX IF NOT EXISTS idx_poll_responses_poll_id ON poll_responses(poll_id);
CREATE INDEX IF NOT EXISTS idx_poll_responses_player_id ON poll_responses(player_id);

-- Add comments for documentation
COMMENT ON TABLE polls IS 'Stores team polls created by captains';
COMMENT ON TABLE poll_choices IS 'Stores multiple choice options for each poll';
COMMENT ON TABLE poll_responses IS 'Stores player responses/votes for polls';
COMMENT ON COLUMN polls.team_id IS 'Future reference to teams table';
COMMENT ON COLUMN polls.created_by IS 'User ID of the captain who created the poll';
COMMENT ON COLUMN poll_responses.player_id IS 'Player ID who responded to the poll'; 