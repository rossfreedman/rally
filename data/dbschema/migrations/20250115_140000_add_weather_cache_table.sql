-- Add weather cache table for storing weather forecast data
-- Date: 2025-01-15
-- Description: Create weather_cache table to store weather forecasts and reduce API calls

BEGIN;

-- Create weather_cache table
CREATE TABLE IF NOT EXISTS weather_cache (
    id SERIAL PRIMARY KEY,
    location VARCHAR(500) NOT NULL,
    forecast_date DATE NOT NULL,
    weather_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create unique index on location and date
CREATE UNIQUE INDEX IF NOT EXISTS idx_weather_cache_location_date 
ON weather_cache(location, forecast_date);

-- Create index on created_at for cache cleanup
CREATE INDEX IF NOT EXISTS idx_weather_cache_created_at 
ON weather_cache(created_at);

-- Add comments
COMMENT ON TABLE weather_cache IS 'Cache for weather forecast data to reduce API calls';
COMMENT ON COLUMN weather_cache.location IS 'Location string (address or coordinates)';
COMMENT ON COLUMN weather_cache.forecast_date IS 'Date for the weather forecast';
COMMENT ON COLUMN weather_cache.weather_data IS 'JSON data containing weather forecast information';
COMMENT ON COLUMN weather_cache.created_at IS 'When this cache entry was created';

-- Create function to automatically update updated_at
CREATE OR REPLACE FUNCTION update_weather_cache_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update updated_at
CREATE TRIGGER trigger_update_weather_cache_updated_at
    BEFORE UPDATE ON weather_cache
    FOR EACH ROW
    EXECUTE FUNCTION update_weather_cache_updated_at();

COMMIT; 