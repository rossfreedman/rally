"""
Weather Service for Rally Platform
Provides weather forecast data for schedule locations
"""

import os
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class WeatherForecast:
    """Weather forecast data structure"""
    date: str
    temperature_high: float
    temperature_low: float
    condition: str
    condition_code: str
    precipitation_chance: float
    wind_speed: float
    humidity: float
    icon: str

class WeatherService:
    """Service for fetching and caching weather forecasts"""
    
    def __init__(self):
        self.api_key = os.getenv('OPENWEATHER_API_KEY')
        self.base_url = "http://api.openweathermap.org/data/2.5"
        self.cache_duration = timedelta(hours=2)  # Cache for 2 hours
        
    def get_weather_for_location(self, location: str, date: str) -> Optional[WeatherForecast]:
        """
        Get weather forecast for a specific location and date
        
        Args:
            location: Location string (address or coordinates)
            date: Date in YYYY-MM-DD format
            
        Returns:
            WeatherForecast object or None if not available
        """
        try:
            # First check cache
            cached_forecast = self._get_cached_forecast(location, date)
            if cached_forecast:
                return cached_forecast
            
            # Get coordinates for location
            coords = self._geocode_location(location)
            if not coords:
                logger.warning(f"Could not geocode location: {location}")
                return None
            
            # Fetch weather forecast
            forecast = self._fetch_weather_forecast(coords, date)
            if forecast:
                # Cache the result
                self._cache_forecast(location, date, forecast)
                return forecast
                
        except Exception as e:
            logger.error(f"Error getting weather for {location} on {date}: {str(e)}")
            
        return None
    
    def get_weather_for_schedule_entries(self, schedule_entries: List[Dict]) -> Dict[str, WeatherForecast]:
        """
        Get weather forecasts for multiple schedule entries
        
        Args:
            schedule_entries: List of schedule entry dictionaries with location and date
            
        Returns:
            Dictionary mapping schedule_id to WeatherForecast
        """
        weather_data = {}
        
        for entry in schedule_entries:
            schedule_id = entry.get('id')
            location = entry.get('location')
            date = entry.get('match_date')
            
            if schedule_id and location and date:
                forecast = self.get_weather_for_location(location, date)
                if forecast:
                    weather_data[schedule_id] = forecast
                    
        return weather_data
    
    def _geocode_location(self, location: str) -> Optional[Dict[str, float]]:
        """Geocode a location string to coordinates"""
        if not self.api_key:
            logger.warning("No OpenWeather API key configured")
            return None
            
        try:
            # Use OpenWeatherMap Geocoding API
            url = f"http://api.openweathermap.org/geo/1.0/direct"
            
            # Try multiple location formats, starting with simpler ones
            location_variants = []
            
            # If location contains a comma, try to extract just the city name
            if ',' in location:
                # Try to extract city name from full address
                city_part = location.split(',')[0].strip()
                location_variants.extend([
                    city_part,  # Just the city name
                    f"{city_part}, Illinois",  # City + state
                    f"{city_part}, IL",  # City + abbreviated state
                    location,  # Original full location
                ])
            else:
                # Simple location, try different formats
                location_variants.extend([
                    location,  # Original location
                    f"{location}, Illinois",  # Add state
                    f"{location}, IL",  # Add abbreviated state
                ])
            
            for variant in location_variants:
                logger.info(f"Trying geocoding for: {variant}")
                params = {
                    'q': variant,
                    'limit': 1,
                    'appid': self.api_key
                }
                
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                if data and len(data) > 0:
                    logger.info(f"Geocoding successful for: {variant}")
                    return {
                        'lat': data[0]['lat'],
                        'lon': data[0]['lon']
                    }
            
            # Specific fallbacks for known clubs
            fallback_locations = {
                'tennaqua': 'Deerfield, Illinois, US',
                'valley lo': 'Glenview, Illinois, US',
                'michigan shores': 'Chicago, Illinois, US',
                'indian hill': 'Winnetka, Illinois, US',
                'westmoreland': 'Winnetka, Illinois, US',
                'northmoor': 'Winnetka, Illinois, US',
                'northmoor country club': 'Winnetka, Illinois, US',
            }
            
            location_lower = location.lower()
            for club_key, fallback_location in fallback_locations.items():
                if club_key in location_lower:
                    logger.info(f"Using fallback location for {club_key}: {fallback_location}")
                    fallback_params = {
                        'q': fallback_location,
                        'limit': 1,
                        'appid': self.api_key
                    }
                    
                    fallback_response = requests.get(url, params=fallback_params, timeout=10)
                    fallback_response.raise_for_status()
                    
                    fallback_data = fallback_response.json()
                    if fallback_data and len(fallback_data) > 0:
                        logger.info(f"Fallback geocoding successful for {club_key}")
                        return {
                            'lat': fallback_data[0]['lat'],
                            'lon': fallback_data[0]['lon']
                        }
                
        except Exception as e:
            logger.error(f"Geocoding error for {location}: {str(e)}")
            
        return None
    
    def _fetch_weather_forecast(self, coords: Dict[str, float], date: str) -> Optional[WeatherForecast]:
        """Fetch weather forecast from OpenWeatherMap API"""
        if not self.api_key:
            return None
            
        try:
            # Use 5-day forecast API
            url = f"{self.base_url}/forecast"
            params = {
                'lat': coords['lat'],
                'lon': coords['lon'],
                'appid': self.api_key,
                'units': 'imperial'  # Use Fahrenheit
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Find forecast for the specific date
            target_date = datetime.strptime(date, '%Y-%m-%d').date()
            
            for item in data.get('list', []):
                item_date = datetime.fromtimestamp(item['dt']).date()
                if item_date == target_date:
                    # Use the forecast for 12:00 (noon) if available, otherwise first available
                    main = item['main']
                    weather = item['weather'][0] if item['weather'] else {}
                    wind = item.get('wind', {})
                    
                    return WeatherForecast(
                        date=date,
                        temperature_high=main.get('temp_max', 0),
                        temperature_low=main.get('temp_min', 0),
                        condition=weather.get('main', 'Unknown'),
                        condition_code=weather.get('icon', ''),
                        precipitation_chance=item.get('pop', 0) * 100,  # Convert to percentage
                        wind_speed=wind.get('speed', 0),
                        humidity=main.get('humidity', 0),
                        icon=weather.get('icon', '')
                    )
                    
        except Exception as e:
            logger.error(f"Weather API error: {str(e)}")
            
        return None
    
    def _get_cached_forecast(self, location: str, date: str) -> Optional[WeatherForecast]:
        """Get cached weather forecast from database"""
        try:
            from core.database import get_db
            from datetime import timezone
            
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT weather_data, created_at 
                    FROM weather_cache 
                    WHERE location = %s AND forecast_date = %s
                """, (location, date))
                
                result = cursor.fetchone()
                if result:
                    weather_data, created_at = result
                    
                    # Check if cache is still valid
                    # Make both datetimes timezone-aware for comparison
                    now = datetime.now(timezone.utc)
                    if created_at.tzinfo is None:
                        # If created_at is naive, assume it's UTC
                        created_at = created_at.replace(tzinfo=timezone.utc)
                    
                    cache_age = now - created_at
                    if cache_age < self.cache_duration:
                        # Parse cached data - handle both string and dict cases
                        if isinstance(weather_data, str):
                            data = json.loads(weather_data)
                        elif isinstance(weather_data, dict):
                            data = weather_data
                        else:
                            logger.error(f"Unexpected weather_data type: {type(weather_data)}")
                            return None
                            
                        return WeatherForecast(**data)
                        
        except Exception as e:
            logger.error(f"Cache retrieval error: {str(e)}")
            
        return None
    
    def _cache_forecast(self, location: str, date: str, forecast: WeatherForecast):
        """Cache weather forecast in database"""
        try:
            from core.database import get_db
            
            with get_db() as conn:
                cursor = conn.cursor()
                
                # Convert forecast to JSON
                weather_data = json.dumps({
                    'date': forecast.date,
                    'temperature_high': forecast.temperature_high,
                    'temperature_low': forecast.temperature_low,
                    'condition': forecast.condition,
                    'condition_code': forecast.condition_code,
                    'precipitation_chance': forecast.precipitation_chance,
                    'wind_speed': forecast.wind_speed,
                    'humidity': forecast.humidity,
                    'icon': forecast.icon
                })
                
                # Upsert cache entry
                cursor.execute("""
                    INSERT INTO weather_cache (location, forecast_date, weather_data, created_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (location, forecast_date) 
                    DO UPDATE SET 
                        weather_data = EXCLUDED.weather_data,
                        created_at = CURRENT_TIMESTAMP
                """, (location, date, weather_data))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Cache storage error: {str(e)}")
    
    def get_weather_icon_url(self, icon_code: str) -> str:
        """Get weather icon URL from OpenWeatherMap"""
        return f"http://openweathermap.org/img/wn/{icon_code}@2x.png"
    
    def format_weather_message(self, forecast: WeatherForecast) -> str:
        """Format weather forecast into a user-friendly message"""
        temp_high = int(forecast.temperature_high)
        temp_low = int(forecast.temperature_low)
        precip = int(forecast.precipitation_chance)
        
        message = f"{temp_high}°F/{temp_low}°F"
        
        if precip > 30:
            message += f", {precip}% rain"
        elif forecast.wind_speed > 15:
            message += f", windy"
            
        return message 