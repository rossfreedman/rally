#!/usr/bin/env python3
"""
Test script to verify that the analyze-me functionality is using tenniscores_player_id
"""

import requests
import json

# Test the API endpoint directly
def test_analyze_me():
    base_url = "http://127.0.0.1:8080"
    
    # First, let's test the login to get a session
    login_data = {
        "email": "rossfreedman@gmail.com",
        "password": "test"  # Replace with actual password if different
    }
    
    session = requests.Session()
    
    # Login
    login_response = session.post(f"{base_url}/api/login", json=login_data)
    print(f"Login status: {login_response.status_code}")
    
    if login_response.status_code == 200:
        print("Login successful!")
        login_data = login_response.json()
        print(f"Login response: {login_data}")
        
        # Test the research-me API endpoint
        research_response = session.get(f"{base_url}/api/research-me")
        print(f"Research-me status: {research_response.status_code}")
        
        if research_response.status_code == 200:
            data = research_response.json()
            print("Research-me API response received!")
            print(f"Current season: {data.get('current_season')}")
            print(f"Career stats: {data.get('career_stats')}")
            print(f"Court analysis keys: {list(data.get('court_analysis', {}).keys())}")
            print(f"Player history: {data.get('player_history')}")
            print(f"Error (if any): {data.get('error')}")
            
            # Check if we got meaningful data (indicates successful player search)
            career_stats = data.get('career_stats', {})
            if career_stats and career_stats.get('matches') != 'N/A':
                print("✅ SUCCESS: Player data found! The tenniscores_player_id search is working.")
                print(f"   Found player with {career_stats.get('matches')} matches and {career_stats.get('winRate')}% win rate")
            else:
                print("❌ WARNING: No meaningful player data found. May need to check search logic.")
        else:
            print(f"Research-me failed: {research_response.text}")
            
        # Test the mobile analyze-me page
        analyze_response = session.get(f"{base_url}/mobile/analyze-me")
        print(f"Mobile analyze-me status: {analyze_response.status_code}")
        
        if analyze_response.status_code == 200:
            print("✅ Mobile analyze-me page loaded successfully!")
            # Check if the page contains player data
            if "Ross Freedman" in analyze_response.text or "current_pti" in analyze_response.text:
                print("✅ Page appears to contain player-specific data")
            else:
                print("⚠️  Page loaded but may not contain player-specific data")
        else:
            print(f"❌ Mobile analyze-me failed: {analyze_response.text}")
    else:
        print(f"❌ Login failed: {login_response.text}")

if __name__ == "__main__":
    test_analyze_me() 