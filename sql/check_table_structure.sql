\d player_availability;

SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'player_availability'; 