-- Fix user_instructions table team_id foreign key
-- Date: 2024-12-19
-- Description: Add foreign key constraint to existing user_instructions.team_id column

BEGIN;

-- Add foreign key constraint to existing team_id column
-- (The column already exists as INTEGER, we just need to add the FK constraint)
ALTER TABLE user_instructions ADD CONSTRAINT fk_user_instructions_team_id 
FOREIGN KEY (team_id) REFERENCES teams(id);

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_user_instructions_team_id ON user_instructions(team_id);

-- Update comment
COMMENT ON COLUMN user_instructions.team_id IS 'Foreign key reference to teams table';

COMMIT; 