#!/usr/bin/env python3
"""
Test script to verify that the team schedule functionality is working correctly
"""

import requests
import json

def test_team_schedule():
    base_url = "http://127.0.0.1:8080"
    
    # Login credentials - replace with actual test credentials
    login_data = {
        "email": "rossfreedman@gmail.com",
        "password": "test"  # Replace with actual password if different
    }
    
    session = requests.Session()
    
    # Login
    print("🔐 Testing login...")
    login_response = session.post(f"{base_url}/api/login", json=login_data)
    print(f"Login status: {login_response.status_code}")
    
    if login_response.status_code == 200:
        print("✅ Login successful!")
        login_data = login_response.json()
        print(f"User: {login_data.get('user', {}).get('email')}")
        print(f"Club: {login_data.get('user', {}).get('club')}")
        print(f"Series: {login_data.get('user', {}).get('series')}")
        
        # Test the mobile team schedule page
        print("\n📱 Testing mobile team schedule page...")
        page_response = session.get(f"{base_url}/mobile/team-schedule")
        print(f"Team schedule page status: {page_response.status_code}")
        
        if page_response.status_code == 200:
            print("✅ Team schedule page loaded successfully!")
            # Check if the page contains expected elements
            if "team-schedule" in page_response.text and "loadTeamScheduleData" in page_response.text:
                print("✅ Page appears to contain team schedule functionality")
            else:
                print("⚠️  Page loaded but may not contain expected team schedule elements")
        else:
            print(f"❌ Team schedule page failed: {page_response.text}")
        
        # Test the team schedule data API endpoint
        print("\n📊 Testing team schedule data API...")
        api_response = session.get(f"{base_url}/api/team-schedule-data")
        print(f"Team schedule API status: {api_response.status_code}")
        
        if api_response.status_code == 200:
            try:
                data = api_response.json()
                print("✅ Team schedule API response received!")
                
                # Check the data structure
                players_schedule = data.get('players_schedule', {})
                match_dates = data.get('match_dates', [])
                event_details = data.get('event_details', {})
                
                print(f"📋 Found {len(players_schedule)} players in schedule")
                print(f"📅 Found {len(match_dates)} event dates")
                print(f"📝 Found {len(event_details)} event details")
                
                if players_schedule:
                    print("\n👥 Sample players:")
                    for i, (player_name, availability) in enumerate(list(players_schedule.items())[:3]):
                        print(f"   {i+1}. {player_name} - {len(availability)} dates")
                        if availability:
                            sample_date = availability[0]
                            print(f"      Sample: {sample_date.get('date')} - Status: {sample_date.get('availability_status')} - Type: {sample_date.get('event_type')}")
                
                if match_dates:
                    print(f"\n📅 Sample dates: {match_dates[:5]}")
                
                if event_details:
                    print(f"\n📝 Sample events:")
                    for i, (date, details) in enumerate(list(event_details.items())[:3]):
                        print(f"   {date}: {details.get('type')} - {details.get('opponent', details.get('description', 'N/A'))}")
                
                # Check if we got meaningful data
                if players_schedule and match_dates:
                    print("\n✅ SUCCESS: Team schedule data is working correctly!")
                    print("   - Players found ✓")
                    print("   - Dates found ✓") 
                    print("   - Data structure correct ✓")
                else:
                    print("\n⚠️  WARNING: API returned but with limited data")
                    if not players_schedule:
                        print("   - No players found")
                    if not match_dates:
                        print("   - No match dates found")
                        
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON response: {e}")
                print(f"Raw response: {api_response.text[:500]}...")
        else:
            print(f"❌ Team schedule API failed: {api_response.text}")
            
    else:
        print(f"❌ Login failed: {login_response.text}")
        print("Please check your login credentials and try again.")

if __name__ == "__main__":
    test_team_schedule() 