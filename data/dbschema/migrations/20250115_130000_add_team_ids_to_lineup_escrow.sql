-- Migration: Add Team IDs to Lineup Escrow Table
-- Date: 2025-01-15 13:00:00
-- Description: Adds team_id columns to lineup_escrow table for better team tracking

-- Add team ID columns to lineup_escrow table
ALTER TABLE lineup_escrow 
ADD COLUMN initiator_team_id INTEGER REFERENCES teams(id),
ADD COLUMN recipient_team_id INTEGER REFERENCES teams(id);

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_lineup_escrow_initiator_team ON lineup_escrow(initiator_team_id);
CREATE INDEX IF NOT EXISTS idx_lineup_escrow_recipient_team ON lineup_escrow(recipient_team_id);

-- Add comments for documentation
COMMENT ON COLUMN lineup_escrow.initiator_team_id IS 'Team ID of the initiator (sender) of the lineup escrow';
COMMENT ON COLUMN lineup_escrow.recipient_team_id IS 'Team ID of the recipient (receiver) of the lineup escrow'; 