# Weather Integration Guide for Rally Platform

## Overview

The Rally platform now includes weather forecast integration for the Upcoming Schedule notification card. This feature provides users with weather information for their upcoming practices and matches, helping them prepare appropriately for outdoor activities.

## Features

### 🌤️ Weather Forecast Display
- **Temperature Range**: Shows high/low temperatures for practice and match dates
- **Weather Conditions**: Displays current weather conditions (sunny, cloudy, rain, etc.)
- **Weather Icons**: Visual weather icons from OpenWeatherMap
- **Precipitation Chance**: Shows rain probability when significant (>30%)
- **Wind Information**: Indicates windy conditions when wind speed >15 mph

### 📍 Location Intelligence
- **Club Addresses**: Uses stored club addresses for accurate location data
- **Fallback Locations**: Falls back to club name + state if address unavailable
- **Geocoding**: Automatically converts addresses to coordinates for weather lookup

### 💾 Smart Caching
- **2-Hour Cache**: Weather data cached for 2 hours to reduce API calls
- **Database Storage**: Weather forecasts stored in `weather_cache` table
- **Automatic Refresh**: Cache automatically refreshes when expired

## Technical Implementation

### 1. Weather Service (`app/services/weather_service.py`)

The core weather service provides:
- **OpenWeatherMap Integration**: Uses free OpenWeatherMap API
- **Geocoding**: Converts addresses to coordinates
- **Forecast Fetching**: Retrieves 5-day weather forecasts
- **Data Caching**: Stores and retrieves cached weather data
- **Error Handling**: Graceful fallback when weather data unavailable

### 2. Database Schema

#### Weather Cache Table
```sql
CREATE TABLE weather_cache (
    id SERIAL PRIMARY KEY,
    location VARCHAR(500) NOT NULL,
    forecast_date DATE NOT NULL,
    weather_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

#### Enhanced Schedule Query
The schedule notification now includes:
- Club addresses from the `clubs` table
- Team relationships for accurate location mapping
- Weather data integration

### 3. Frontend Integration

#### Notification Enhancement
- **Weather Icons**: Small weather icons displayed below schedule text
- **Temperature Display**: High/low temperatures shown with weather icons
- **Responsive Design**: Weather elements adapt to mobile screen sizes

#### Weather Icon Generation
```javascript
function generateWeatherIcons(weatherData) {
    // Creates weather icon elements with temperature display
    // Uses OpenWeatherMap icon URLs
    // Handles missing icons gracefully
}
```

## Setup Instructions

### 1. Get OpenWeatherMap API Key

1. Visit [OpenWeatherMap](https://openweathermap.org/api)
2. Sign up for a free account
3. Get your API key from the dashboard
4. The free tier includes:
   - 1,000 API calls per day
   - 5-day weather forecasts
   - Geocoding API

### 2. Configure Environment Variable

Add to your `.env` file:
```bash
OPENWEATHER_API_KEY=your_api_key_here
```

### 3. Run Database Migration

Deploy the weather cache table:
```bash
python data/dbschema/dbschema_workflow.py --auto
```

### 4. Test the Integration

Run the test script to verify everything works:
```bash
python scripts/test_weather_integration.py
```

## Usage Examples

### Example Notification Output

**Without Weather:**
```
Practice: Jan 15 at 6:30 PM
Match: Jan 17 at 7:00 PM vs Tennaqua
```

**With Weather:**
```
Practice: Jan 15 at 6:30 PM • 45°F/32°F
Match: Jan 17 at 7:00 PM vs Tennaqua • 52°F/38°F, 40% rain
```

### Weather Icon Display
- **Sunny**: ☀️ with temperature range
- **Cloudy**: ☁️ with temperature range  
- **Rainy**: 🌧️ with precipitation percentage
- **Windy**: 💨 with wind indicator

## API Rate Limits & Costs

### OpenWeatherMap Free Tier
- **1,000 API calls per day**
- **5-day forecast data**
- **Geocoding included**
- **No credit card required**

### Caching Strategy
- **2-hour cache duration** reduces API calls by ~90%
- **Location-based caching** prevents duplicate requests
- **Automatic cache cleanup** prevents database bloat

### Estimated Usage
- **50 users**: ~25 API calls per day
- **100 users**: ~50 API calls per day
- **500 users**: ~250 API calls per day

## Error Handling

### Graceful Degradation
- **No API Key**: Weather features disabled, notifications work normally
- **API Errors**: Weather data omitted, schedule still displays
- **Geocoding Failures**: Falls back to club name + state
- **Cache Errors**: Falls back to direct API calls

### Logging
- **Warning logs** for API failures
- **Error logs** for critical issues
- **Debug logs** for troubleshooting

## Performance Considerations

### Database Impact
- **Minimal**: Weather cache table is small and indexed
- **Automatic cleanup**: Old cache entries can be purged
- **Efficient queries**: Uses unique indexes for fast lookups

### API Performance
- **Async calls**: Weather fetching doesn't block notifications
- **Timeout handling**: 10-second timeout prevents hanging
- **Connection pooling**: Reuses HTTP connections

### Frontend Performance
- **Lazy loading**: Weather icons load asynchronously
- **Error handling**: Missing icons don't break the UI
- **Responsive design**: Works on all screen sizes

## Troubleshooting

### Common Issues

#### 1. No Weather Data Displayed
- Check `OPENWEATHER_API_KEY` environment variable
- Verify API key is valid and has remaining calls
- Check logs for geocoding errors

#### 2. Incorrect Locations
- Verify club addresses in database
- Check geocoding results in logs
- Update club addresses if needed

#### 3. Cache Issues
- Check `weather_cache` table exists
- Verify database permissions
- Clear cache manually if needed

### Debug Commands

```bash
# Test weather service
python scripts/test_weather_integration.py

# Check cache table
psql -d rally -c "SELECT * FROM weather_cache LIMIT 5;"

# Clear old cache entries
psql -d rally -c "DELETE FROM weather_cache WHERE created_at < NOW() - INTERVAL '24 hours';"
```

## Future Enhancements

### Potential Improvements
- **Hourly forecasts**: More precise timing for matches
- **Weather alerts**: Severe weather notifications
- **Historical data**: Track weather impact on performance
- **Multiple providers**: Fallback weather APIs
- **Push notifications**: Weather-based alerts

### Integration Opportunities
- **Availability updates**: Weather-based availability suggestions
- **Match rescheduling**: Weather-based postponement recommendations
- **Equipment recommendations**: Weather-appropriate gear suggestions

## Support

For issues with weather integration:
1. Check the troubleshooting section above
2. Review application logs for error messages
3. Test with the provided test script
4. Verify API key and rate limits

The weather integration is designed to be robust and fail gracefully, ensuring that the core notification system continues to work even if weather data is unavailable. 