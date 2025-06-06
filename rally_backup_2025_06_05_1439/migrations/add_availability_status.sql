-- Add availability_status column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'player_availability' 
        AND column_name = 'availability_status'
    ) THEN
        -- Add the column
        ALTER TABLE player_availability ADD COLUMN availability_status INTEGER NOT NULL DEFAULT 3;
        
        -- Add check constraint
        ALTER TABLE player_availability ADD CONSTRAINT valid_availability_status 
            CHECK (availability_status IN (1, 2, 3));
    END IF;
END $$; 