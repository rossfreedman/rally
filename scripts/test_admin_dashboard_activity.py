#!/usr/bin/env python3
"""
Test script to verify admin dashboard shows most recent activity for users
"""

import sys
import os
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.dashboard_service import get_top_active_players

def test_admin_dashboard_activity():
    """Test that the admin dashboard shows most recent activity for users"""
    print("🧪 Testing admin dashboard most recent activity display...")
    
    try:
        # Get top active players with activity data
        top_players = get_top_active_players(limit=10, filters={
            "exclude_admin": True,
            "exclude_impersonated": False
        })
        
        if not top_players:
            print("❌ No top players found")
            return False
        
        print(f"✅ Found {len(top_players)} top active players")
        
        # Check if each player has last_activity data
        print("\n📊 Checking last activity data for each player:")
        for i, player in enumerate(top_players[:5]):  # Show first 5 players
            last_activity = player.get('last_activity')
            if last_activity:
                if isinstance(last_activity, str):
                    last_activity = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                formatted_time = last_activity.strftime('%Y-%m-%d %H:%M:%S')
            else:
                formatted_time = "No activity data"
            
            print(f"  {i+1}. {player['first_name']} {player['last_name']} (ID: {player['id']})")
            print(f"      Activity Count: {player.get('activity_count', 0)}")
            print(f"      Last Activity: {formatted_time}")
            print(f"      Club: {player.get('club_name', 'Unknown')}")
            print(f"      Series: {player.get('series_name', 'Unknown')}")
            print()
        
        # Verify that all players have last_activity data
        players_with_activity = [p for p in top_players if p.get('last_activity')]
        players_without_activity = [p for p in top_players if not p.get('last_activity')]
        
        print(f"📈 Activity Data Summary:")
        print(f"  Total players: {len(top_players)}")
        print(f"  Players with activity data: {len(players_with_activity)}")
        print(f"  Players without activity data: {len(players_without_activity)}")
        
        if players_without_activity:
            print(f"  ⚠️  Players missing activity data:")
            for player in players_without_activity:
                print(f"    - {player['first_name']} {player['last_name']}")
        
        # Check if players are sorted by activity count (descending)
        activity_counts = [p.get('activity_count', 0) for p in top_players]
        is_sorted = all(activity_counts[i] >= activity_counts[i+1] for i in range(len(activity_counts)-1))
        
        if is_sorted:
            print("✅ Players are correctly sorted by activity count (highest first)")
        else:
            print("❌ Players are NOT correctly sorted by activity count")
        
        # Show some additional statistics
        total_activities = sum(p.get('activity_count', 0) for p in top_players)
        avg_activities = total_activities / len(top_players) if top_players else 0
        
        print(f"\n📊 Additional Statistics:")
        print(f"  Total activities across all players: {total_activities}")
        print(f"  Average activities per player: {avg_activities:.1f}")
        print(f"  Most active player: {top_players[0]['first_name']} {top_players[0]['last_name']} ({top_players[0].get('activity_count', 0)} activities)")
        
        return len(players_with_activity) > 0 and is_sorted
        
    except Exception as e:
        print(f"❌ Error testing admin dashboard activity: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_admin_dashboard_activity()
    sys.exit(0 if success else 1) 