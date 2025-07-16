#!/usr/bin/env python3
"""
Demo Weather Notification
Shows how the weather integration will look once API key is active
"""

import json
from datetime import datetime, timedelta

def create_demo_notification():
    """Create a demo notification with sample weather data"""
    
    # Sample weather data (what you'll see once API key is active)
    demo_weather_data = {
        "practice_123": {
            "date": (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
            "temperature_high": 75.0,
            "temperature_low": 62.0,
            "condition": "Clear",
            "condition_code": "01d",
            "precipitation_chance": 10.0,
            "wind_speed": 8.0,
            "humidity": 65.0,
            "icon": "01d"
        },
        "match_456": {
            "date": (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d'),
            "temperature_high": 68.0,
            "temperature_low": 55.0,
            "condition": "Rain",
            "condition_code": "10d",
            "precipitation_chance": 40.0,
            "wind_speed": 12.0,
            "humidity": 80.0,
            "icon": "10d"
        }
    }
    
    # Create demo notification
    demo_notification = {
        "id": "upcoming_schedule",
        "type": "schedule",
        "title": "Upcoming Schedule",
        "message": "Practice: Jul 19 at 6:00 AM • 75°F/62°F\nMatch: Jul 21 at 7:00 PM vs Tennaqua • 68°F/55°F, 40% rain",
        "cta": {"label": "View Schedule", "href": "/mobile/availability"},
        "priority": 2,
        "weather": demo_weather_data
    }
    
    return demo_notification

def generate_weather_icons_html(weather_data):
    """Generate HTML for weather icons (same as frontend)"""
    icons_html = ""
    
    for key, forecast in weather_data.items():
        if forecast and forecast.get('icon'):
            icon_url = f"http://openweathermap.org/img/wn/{forecast['icon']}@2x.png"
            temp_high = int(forecast['temperature_high'])
            temp_low = int(forecast['temperature_low'])
            
            icons_html += f"""
                <div style="display: inline-flex; align-items: center; gap: 4px; background: #eff6ff; border-radius: 8px; padding: 4px 8px; margin-right: 8px;">
                    <img src="{icon_url}" alt="{forecast['condition']}" style="width: 24px; height: 24px;">
                    <span style="font-size: 12px; font-weight: 500; color: #374151;">
                        {temp_high}°/{temp_low}°
                    </span>
                </div>
            """
    
    return icons_html

def main():
    """Show demo of weather integration"""
    
    print("🌤️ Weather Integration Demo")
    print("=" * 50)
    print()
    
    # Create demo notification
    notification = create_demo_notification()
    
    print("📱 What you'll see in the Upcoming Schedule notification:")
    print()
    print(f"Title: {notification['title']}")
    print(f"Message: {notification['message']}")
    print()
    
    # Show weather icons
    print("🌡️ Weather Icons (will appear below the message):")
    weather_icons = generate_weather_icons_html(notification['weather'])
    print(weather_icons)
    print()
    
    print("📊 Weather Data Structure:")
    for key, forecast in notification['weather'].items():
        print(f"  {key}:")
        print(f"    Temperature: {forecast['temperature_high']}°F/{forecast['temperature_low']}°F")
        print(f"    Condition: {forecast['condition']}")
        print(f"    Precipitation: {forecast['precipitation_chance']}%")
        print(f"    Wind: {forecast['wind_speed']} mph")
        print(f"    Icon: {forecast['icon']}")
        print()
    
    print("=" * 50)
    print("🔧 Next Steps:")
    print("   1. Wait 1-2 hours for your API key to activate")
    print("   2. Run: python scripts/test_openweather_key.py")
    print("   3. Once working, visit: http://127.0.0.1:8080/mobile/home_submenu")
    print("   4. You'll see real weather data in your notifications!")
    print()
    print("📚 Documentation: docs/WEATHER_INTEGRATION_GUIDE.md")

if __name__ == "__main__":
    main() 