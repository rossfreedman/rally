#!/usr/bin/env python3
"""
Debug Mobile Settings API Endpoints
==================================

Test script to debug the mobile settings page Series/Division display issue.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one
import json

def test_user_settings_api():
    """Test the get-user-settings API endpoint"""
    print("🔍 Testing get-user-settings API endpoint...")
    
    # Use a known user email for testing
    test_email = "rossfreedman@gmail.com"  # Replace with actual test email
    
    try:
        # Get basic user data including league_context
        user_data = execute_query_one(
            """
            SELECT u.first_name, u.last_name, u.email, u.is_admin, 
                   u.ad_deuce_preference, u.dominant_hand, u.league_context
            FROM users u
            WHERE u.email = %s
        """,
            (test_email,),
        )
        
        if not user_data:
            print(f"❌ No user found with email: {test_email}")
            return False
        
        print(f"✅ Found user: {user_data['first_name']} {user_data['last_name']}")
        print(f"   League context: {user_data['league_context']}")
        
        # Get player association data
        from app.models.database_models import User, UserPlayerAssociation, SessionLocal
        
        db_session = SessionLocal()
        try:
            user_record = db_session.query(User).filter(User.email == test_email).first()
            
            if user_record:
                print(f"✅ Found user record with ID: {user_record.id}")
                
                # Get all associations for this user
                associations = (
                    db_session.query(UserPlayerAssociation)
                    .filter(UserPlayerAssociation.user_id == user_record.id)
                    .all()
                )
                
                print(f"✅ Found {len(associations)} player associations")
                
                selected_player = None
                
                # First priority: find player matching league_context
                if user_record.league_context and associations:
                    for assoc in associations:
                        player = assoc.get_player(db_session)
                        if player and player.league and player.league.id == user_record.league_context:
                            selected_player = player
                            print(f"✅ Found player matching league context: {player.full_name}")
                            break
                
                # Second priority: use first available player
                if not selected_player and associations:
                    for assoc in associations:
                        player = assoc.get_player(db_session)
                        if player and player.club and player.series and player.league:
                            selected_player = player
                            print(f"✅ Using first available player: {player.full_name}")
                            break
                
                # Extract player data if found
                if selected_player:
                    club_name = selected_player.club.name if selected_player.club else ""
                    raw_series_name = selected_player.series.name if selected_player.series else ""
                    league_id = selected_player.league.league_id if selected_player.league else ""
                    league_name = selected_player.league.league_name if selected_player.league else ""
                    
                    print(f"✅ Player data:")
                    print(f"   Club: {club_name}")
                    print(f"   Raw series: {raw_series_name}")
                    print(f"   League ID: {league_id}")
                    print(f"   League name: {league_name}")
                    
                    # Get display name from series table if available
                    series_name = raw_series_name
                    if raw_series_name:
                        try:
                            display_name_query = """
                                SELECT display_name
                                FROM series
                                WHERE name = %s
                                LIMIT 1
                            """
                            
                            display_result = execute_query_one(display_name_query, (raw_series_name,))
                            
                            if display_result and display_result["display_name"]:
                                series_name = display_result["display_name"]
                                print(f"✅ Found display name: '{raw_series_name}' -> '{series_name}'")
                            else:
                                print(f"⚠️  No display name found for '{raw_series_name}'")
                        except Exception as e:
                            print(f"❌ Error getting display name: {e}")
                    
                    print(f"✅ Final series name: {series_name}")
                    return True
                else:
                    print(f"❌ No player found for user")
                    return False
        finally:
            db_session.close()
            
    except Exception as e:
        print(f"❌ Error testing user settings API: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_series_api():
    """Test the get-user-facing-series-by-league API endpoint"""
    print("\n🔍 Testing get-user-facing-series-by-league API endpoint...")
    
    # Test with a known league
    test_league_id = "APTA_CHICAGO"  # Replace with actual league ID
    
    try:
        # SIMPLIFIED: Get series with display names using the new display_name column
        simplified_query = """
            SELECT DISTINCT 
                s.name as database_series_name,
                COALESCE(s.display_name, s.name) as display_name
            FROM series s
            JOIN series_leagues sl ON s.id = sl.series_id
            JOIN leagues l ON sl.league_id = l.id
            WHERE l.league_id = %s
            ORDER BY s.name
        """
        series_data = execute_query(simplified_query, (test_league_id,))
        
        print(f"✅ Found {len(series_data)} series for league {test_league_id}")
        
        for series_item in series_data:
            database_name = series_item["database_series_name"]
            display_name = series_item["display_name"]
            
            print(f"   Series: {database_name} -> {display_name}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error testing series API: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all debug tests"""
    print("🔍 Mobile Settings Debug Test")
    print("=" * 50)
    
    success1 = test_user_settings_api()
    success2 = test_series_api()
    
    if success1 and success2:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 