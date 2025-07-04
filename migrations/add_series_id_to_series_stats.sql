-- Add series_id FK to series_stats Table
-- Date: 2024-01-10
-- Description: Add series_id foreign key to series_stats table to enable ID-based queries instead of string matching

BEGIN;

-- Add series_id column to series_stats table
ALTER TABLE series_stats ADD COLUMN IF NOT EXISTS series_id INTEGER REFERENCES series(id);

-- Create index for performance on series_id
CREATE INDEX IF NOT EXISTS idx_series_stats_series_id ON series_stats(series_id);

-- Add comment to document the purpose
COMMENT ON COLUMN series_stats.series_id IS 'Foreign key reference to series table - replaces string-based series matching';

COMMIT; 