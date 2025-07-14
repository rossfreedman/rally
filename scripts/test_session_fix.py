#!/usr/bin/env python3
"""
Test script to verify session service fix for Brian Benavides
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.session_service import get_session_data_for_user
from database_utils import execute_query

def test_brian_benavides_session():
    """Test that Brian Benavides gets the correct session data"""
    print("🧪 Testing Brian Benavides session data...")
    
    email = "bben@gmail.com"
    
    # Get session data
    session_data = get_session_data_for_user(email)
    
    if not session_data:
        print("❌ No session data found for Brian Benavides")
        return False
    
    print(f"✅ Session data found for {email}:")
    print(f"   Club: {session_data.get('club', 'None')}")
    print(f"   Series: {session_data.get('series', 'None')}")
    print(f"   Team ID: {session_data.get('team_id', 'None')}")
    print(f"   Team Name: {session_data.get('team_name', 'None')}")
    print(f"   League Context: {session_data.get('league_context', 'None')}")
    print(f"   League Name: {session_data.get('league_name', 'None')}")
    
    # Check if it's the correct team (should be Tennaqua - Chicago 9)
    expected_club = "Tennaqua"
    expected_series = "Chicago 9"
    
    actual_club = session_data.get('club', '')
    actual_series = session_data.get('series', '')
    
    if actual_club == expected_club and actual_series == expected_series:
        print("✅ SUCCESS: Session shows correct team (Tennaqua - Chicago 9)")
        return True
    else:
        print(f"❌ FAILED: Expected {expected_club} - {expected_series}, got {actual_club} - {actual_series}")
        return False

def check_user_data():
    """Check Brian Benavides user data in database"""
    print("\n🔍 Checking Brian Benavides database data...")
    
    # Check user record
    user_query = """
        SELECT id, email, first_name, last_name, league_context
        FROM users 
        WHERE email = 'bben@gmail.com'
    """
    user = execute_query(user_query)
    
    if user:
        print(f"✅ User found: {user[0]}")
    else:
        print("❌ User not found")
        return
    
    # Check player associations
    associations_query = """
        SELECT 
            upa.tenniscores_player_id,
            p.first_name, p.last_name,
            c.name as club_name,
            s.name as series_name,
            t.team_name,
            l.league_name,
            p.team_id,
            p.league_id
        FROM user_player_associations upa
        JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
        JOIN clubs c ON p.club_id = c.id
        JOIN series s ON p.series_id = s.id
        JOIN teams t ON p.team_id = t.id
        JOIN leagues l ON p.league_id = l.id
        WHERE upa.user_id = %s
        ORDER BY p.league_id, p.team_id
    """
    
    associations = execute_query(associations_query, [user[0]['id']])
    
    print(f"📊 Player associations found: {len(associations)}")
    for i, assoc in enumerate(associations):
        print(f"   {i+1}. {assoc['first_name']} {assoc['last_name']}")
        print(f"      Club: {assoc['club_name']}")
        print(f"      Series: {assoc['series_name']}")
        print(f"      Team: {assoc['team_name']}")
        print(f"      League: {assoc['league_name']}")
        print(f"      Team ID: {assoc['team_id']}")
        print(f"      League ID: {assoc['league_id']}")
        print()

def test_session_query():
    """Test the exact session query to see what it returns"""
    print("\n🔍 Testing exact session query...")
    
    query = """
        SELECT DISTINCT ON (u.id)
            u.id, u.email, u.first_name, u.last_name, u.is_admin,
            u.ad_deuce_preference, u.dominant_hand, u.league_context,
            
            -- Player data (prioritize league_context team)
            c.name as club, c.logo_filename as club_logo,
            s.name as series, p.tenniscores_player_id,
            c.id as club_id, s.id as series_id, t.id as team_id,
            t.team_name, t.display_name,
            
            -- League data
            l.id as league_db_id, l.league_id as league_string_id, l.league_name
        FROM users u
        LEFT JOIN user_player_associations upa ON u.id = upa.user_id
        LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id AND p.is_active = true
        LEFT JOIN clubs c ON p.club_id = c.id
        LEFT JOIN series s ON p.series_id = s.id
        LEFT JOIN teams t ON p.team_id = t.id
        LEFT JOIN leagues l ON p.league_id = l.id
        WHERE u.email = 'bben@gmail.com'
        ORDER BY u.id, 
                 -- PRIORITY 1: League context match (most important)
                 (CASE WHEN p.league_id = u.league_context THEN 1 ELSE 2 END),
                 -- PRIORITY 2: Team has team_id (prefer teams over unassigned players)
                 (CASE WHEN p.team_id IS NOT NULL THEN 1 ELSE 2 END),
                 -- PRIORITY 3: Most recent player record (newer registrations first)
                 p.id DESC
        LIMIT 1
    """
    
    result = execute_query(query)
    
    if result:
        print("✅ Session query result:")
        for key, value in result[0].items():
            print(f"   {key}: {value}")
    else:
        print("❌ No session query result")

if __name__ == "__main__":
    print("🧪 Testing Session Service Fix for Brian Benavides")
    print("=" * 60)
    
    # Check database data first
    check_user_data()
    
    # Test the session query
    test_session_query()
    
    # Test session service
    success = test_brian_benavides_session()
    
    if success:
        print("\n✅ All tests passed! Session service is working correctly.")
    else:
        print("\n❌ Tests failed. Session service still has issues.")
    
    print("\n" + "=" * 60) 