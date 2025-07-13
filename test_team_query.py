#!/usr/bin/env python3
"""
Test script to verify the team query works with correct column names
"""

from database_utils import execute_query_one

def test_team_query():
    """Test the team query with correct column names"""
    print("🧪 Testing Team Query...")
    
    # Test query with correct column name
    team_query = """
        SELECT 
            t.id as team_id,
            t.team_name as team_name,
            l.league_name as league_name,
            s.name as series_name,
            COUNT(p.id) as member_count,
            COUNT(CASE WHEN u.phone_number IS NOT NULL AND u.phone_number != '' THEN 1 END) as members_with_phones
        FROM teams t
        JOIN leagues l ON t.league_id = l.id
        JOIN series s ON t.series_id = s.id
        JOIN players p ON t.id = p.team_id
        LEFT JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
        LEFT JOIN users u ON upa.user_id = u.id
        WHERE upa.user_id = 1  -- Test with user ID 1
        GROUP BY t.id, t.team_name, l.league_name, s.name
        LIMIT 1
    """
    
    try:
        result = execute_query_one(team_query)
        if result:
            print("✅ Team query successful!")
            print(f"Team ID: {result['team_id']}")
            print(f"Team Name: {result['team_name']}")
            print(f"League: {result['league_name']}")
            print(f"Series: {result['series_name']}")
            print(f"Member Count: {result['member_count']}")
            print(f"Members with Phones: {result['members_with_phones']}")
        else:
            print("⚠️ No team found for user ID 1")
            
    except Exception as e:
        print(f"❌ Error in team query: {e}")

if __name__ == "__main__":
    test_team_query() 