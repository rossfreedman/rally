#!/usr/bin/env python3
"""
Debug weather notification UI to test practice pattern matching
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.routes.api_routes import get_upcoming_schedule_notifications
from datetime import datetime

def debug_weather_notification():
    """Debug the weather notification system"""
    
    print("=== Debug Weather Notification UI ===")
    
    # Test with Ross's user data
    user_id = 1  # Ross's user ID
    player_id = "nndz-WlNhd3hMYi9nQT09"  # Ross's player ID
    league_id = "4489"  # APTA Chicago
    team_id = "47092"  # Tennaqua S2B
    
    print(f"Testing with:")
    print(f"  User ID: {user_id}")
    print(f"  Player ID: {player_id}")
    print(f"  League ID: {league_id}")
    print(f"  Team ID: {team_id}")
    
    # Get notifications
    notifications = get_upcoming_schedule_notifications(user_id, player_id, league_id, team_id)
    
    print(f"\nFound {len(notifications)} notifications")
    
    for i, notification in enumerate(notifications):
        print(f"\nNotification {i+1}:")
        print(f"  ID: {notification.get('id')}")
        print(f"  Type: {notification.get('type')}")
        print(f"  Title: {notification.get('title')}")
        print(f"  Message: {notification.get('message')}")
        
        if 'weather' in notification:
            print(f"  Weather data: {notification['weather']}")
        else:
            print(f"  No weather data")
        
        if 'cta' in notification:
            print(f"  CTA: {notification['cta']}")

if __name__ == "__main__":
    debug_weather_notification() 