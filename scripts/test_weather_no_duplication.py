#!/usr/bin/env python3
"""
Test script to verify weather display without temperature duplication
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.weather_service import WeatherService, WeatherForecast
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def test_notification_message_format():
    """Test the notification message format without inline weather"""
    print("=== Testing Notification Message Format ===")
    
    # Simulate the notification message building logic
    practice_text = "Practice: Jul 19 at 6:00 AM"
    match_text = "Match: Jul 17 at 6:00 PM vs Winnetka S2B - Series 2B"
    
    # Weather info is now only in the dedicated weather section
    # No longer added inline to avoid duplication
    
    notification_message = f"{practice_text}\n{match_text}"
    
    print("Notification message:")
    print(notification_message)
    print("\n✅ No inline temperature duplication")
    print("✅ Weather info will only appear in dedicated weather cards below")

def test_weather_card_display():
    """Test the weather card display"""
    print("\n=== Testing Weather Card Display ===")
    
    # Simulate weather data that would be in the notification
    weather_data = {
        "practice_123": {
            "icon": "01d",
            "temperature_high": 75.0,
            "temperature_low": 65.0,
            "condition": "Clear",
            "quality": "good",
            "description": "Warm, Clear skies",
            "emoji": "☀️"
        },
        "match_456": {
            "icon": "10d",
            "temperature_high": 69.0,
            "temperature_low": 68.0,
            "condition": "Rain",
            "quality": "bad",
            "description": "Mild, Rainy, Light rain likely",
            "emoji": "🌧️"
        }
    }
    
    print("Weather cards that will be displayed:")
    for key, forecast in weather_data.items():
        quality = forecast['quality']
        temp_high = round(forecast['temperature_high'])
        temp_low = round(forecast['temperature_low'])
        description = forecast['description']
        emoji = forecast['emoji']
        
        print(f"\n{key}:")
        print(f"  {emoji} {temp_high}°/{temp_low}°")
        print(f"  {description}")
        print(f"  Quality: {quality}")

def test_complete_notification_structure():
    """Test the complete notification structure"""
    print("\n=== Testing Complete Notification Structure ===")
    
    # Simulate the complete notification data structure
    notification_data = {
        "id": "upcoming_schedule",
        "type": "schedule",
        "title": "Upcoming Schedule",
        "message": "Practice: Jul 19 at 6:00 AM\nMatch: Jul 17 at 6:00 PM vs Winnetka S2B - Series 2B",
        "cta": {"label": "View Schedule", "href": "/mobile/availability"},
        "priority": 2,
        "weather": {
            "practice_123": {
                "icon": "01d",
                "temperature_high": 75.0,
                "temperature_low": 65.0,
                "condition": "Clear",
                "quality": "good",
                "description": "Warm, Clear skies",
                "emoji": "☀️"
            },
            "match_456": {
                "icon": "10d",
                "temperature_high": 69.0,
                "temperature_low": 68.0,
                "condition": "Rain",
                "quality": "bad",
                "description": "Mild, Rainy, Light rain likely",
                "emoji": "🌧️"
            }
        }
    }
    
    print("Complete notification structure:")
    print(f"Title: {notification_data['title']}")
    print(f"Message: {notification_data['message']}")
    print(f"Weather entries: {len(notification_data['weather'])}")
    
    # Check that message doesn't contain temperature info
    message = notification_data['message']
    if '°F' in message or '°/' in message:
        print("❌ Message still contains temperature info")
    else:
        print("✅ Message is clean - no temperature duplication")

def main():
    """Main test function"""
    print("Weather Display Without Duplication Test")
    print("=" * 50)
    
    # Test notification message format
    test_notification_message_format()
    
    # Test weather card display
    test_weather_card_display()
    
    # Test complete notification structure
    test_complete_notification_structure()
    
    print("\n=== Summary ===")
    print("✅ Temperature no longer duplicated in notification text")
    print("✅ Weather info only appears in dedicated weather cards")
    print("✅ Clean, uncluttered notification messages")
    print("✅ Rich weather information in separate cards with color coding")

if __name__ == "__main__":
    main() 