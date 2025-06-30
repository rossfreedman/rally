#!/usr/bin/env python3
"""
Test My Club Page Functions
Tests the exact functions called by the my-club page to identify where sparse data is coming from
"""

import psycopg2
from urllib.parse import urlparse
import sys
import os

# Add the app directory to path so we can import the mobile service
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

RAILWAY_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

def connect_to_railway():
    """Connect to Railway database"""
    parsed = urlparse(RAILWAY_URL)
    conn_params = {
        "dbname": parsed.path[1:],
        "user": parsed.username,
        "password": parsed.password,
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "sslmode": "require",
        "connect_timeout": 30,
    }
    return psycopg2.connect(**conn_params)

def execute_query_one(conn, query, params=None):
    """Execute query and return one result"""
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                row = cursor.fetchone()
                return dict(zip(columns, row)) if row else None
            return None
    except Exception as e:
        print(f"   ❌ Query failed: {e}")
        return None

def create_test_user_session():
    """Create a test user session for Ross Freedman based on the database data"""
    conn = connect_to_railway()
    
    # Get the user session data for Ross Freedman
    session_query = """
        SELECT u.id, u.email, u.first_name, u.last_name,
               l.id as league_db_id, l.league_id, l.league_name,
               c.name as club_name, s.name as series_name,
               p.tenniscores_player_id
        FROM users u
        JOIN user_player_associations upa ON u.id = upa.user_id AND upa.is_primary = true
        JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
        JOIN leagues l ON p.league_id = l.id
        JOIN clubs c ON p.club_id = c.id
        JOIN series s ON p.series_id = s.id
        WHERE p.tenniscores_player_id = %s
        LIMIT 1
    """
    
    user_data = execute_query_one(conn, session_query, ["nndz-WkMrK3didjlnUT09"])
    conn.close()
    
    if not user_data:
        print("❌ Could not create test user session")
        return None
    
    # Create session format that matches what the actual app expects
    test_user = {
        "id": user_data["id"],
        "email": user_data["email"],
        "first_name": user_data["first_name"],
        "last_name": user_data["last_name"],
        "club": user_data["club_name"],
        "series": user_data["series_name"],
        "league_id": user_data["league_db_id"],  # This should be the integer primary key
        "league_name": user_data["league_name"],
        "tenniscores_player_id": user_data["tenniscores_player_id"]
    }
    
    print(f"✅ Created test user session:")
    print(f"   Name: {test_user['first_name']} {test_user['last_name']}")
    print(f"   Club: {test_user['club']}")
    print(f"   League: {test_user['league_id']} ({test_user['league_name']})")
    print(f"   Series: {test_user['series']}")
    
    return test_user

def test_get_recent_matches_for_user_club(user):
    """Test the get_recent_matches_for_user_club function"""
    print(f"\n🔍 TESTING get_recent_matches_for_user_club")
    print("=" * 60)
    
    try:
        # Import the actual function from mobile_service
        from app.services.mobile_service import get_recent_matches_for_user_club
        
        # Call the actual function
        matches_by_date = get_recent_matches_for_user_club(user)
        
        if matches_by_date:
            total_matches = sum(len(matches) for matches in matches_by_date.values())
            print(f"   ✅ Found matches for {len(matches_by_date)} dates")
            print(f"   ✅ Total matches: {total_matches}")
            
            # Show sample data
            for i, (date, matches) in enumerate(matches_by_date.items()):
                if i >= 3:  # Only show first 3 dates
                    break
                print(f"   📅 {date}: {len(matches)} matches")
                
            return matches_by_date
        else:
            print(f"   ❌ No matches returned")
            return {}
            
    except Exception as e:
        print(f"   ❌ Function failed: {e}")
        import traceback
        traceback.print_exc()
        return {}

def test_get_mobile_club_data(user):
    """Test the main get_mobile_club_data function"""
    print(f"\n🔍 TESTING get_mobile_club_data")
    print("=" * 60)
    
    try:
        # Import the actual function from mobile_service
        from app.services.mobile_service import get_mobile_club_data
        
        # Call the actual function
        club_data = get_mobile_club_data(user)
        
        print(f"   📊 Results:")
        print(f"      Team name: {club_data.get('team_name', 'None')}")
        print(f"      Weekly results: {len(club_data.get('weekly_results', []))} weeks")
        print(f"      Standings: {len(club_data.get('tennaqua_standings', []))} teams")
        print(f"      Head-to-head: {len(club_data.get('head_to_head', []))} opponents")
        print(f"      Player streaks: {len(club_data.get('player_streaks', []))} players")
        
        if 'error' in club_data:
            print(f"   ❌ Error in club data: {club_data['error']}")
        
        # Show some sample data
        if club_data.get('weekly_results'):
            first_week = club_data['weekly_results'][0]
            print(f"   📅 Latest week ({first_week.get('date', 'Unknown')}):")
            for result in first_week.get('results', [])[:2]:  # Show first 2 results
                print(f"      - {result.get('series', 'Unknown')} vs {result.get('opponent', 'Unknown')}: {result.get('score', 'No score')}")
        
        return club_data
        
    except Exception as e:
        print(f"   ❌ Function failed: {e}")
        import traceback
        traceback.print_exc()
        return {}

def test_database_config():
    """Test that database configuration is working"""
    print(f"\n🔍 TESTING database configuration")
    print("=" * 60)
    
    try:
        # Import database utilities
        from database_utils import execute_query_one as db_execute_query_one
        
        # Test a simple query
        result = db_execute_query_one("""
            SELECT COUNT(*) as count FROM match_scores 
            WHERE league_id = 4489 
            AND (home_team LIKE '%Tennaqua%' OR away_team LIKE '%Tennaqua%')
        """)
        
        if result:
            print(f"   ✅ Database query successful: {result['count']} matches")
        else:
            print(f"   ❌ Database query returned no results")
            
    except Exception as e:
        print(f"   ❌ Database config failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main testing function"""
    print("🚀 MY CLUB PAGE FUNCTIONS TEST")
    print("=" * 50)
    print("Testing the exact functions used by the my-club page...")
    
    try:
        # Test database configuration
        test_database_config()
        
        # Create test user session
        test_user = create_test_user_session()
        
        if not test_user:
            print("❌ Cannot proceed without test user")
            return
        
        # Test individual functions
        matches_data = test_get_recent_matches_for_user_club(test_user)
        club_data = test_get_mobile_club_data(test_user)
        
        # Summary
        print(f"\n🎯 SUMMARY")
        print("=" * 60)
        print(f"   📊 Recent matches function:")
        if matches_data:
            total_matches = sum(len(matches) for matches in matches_data.values())
            print(f"      ✅ Returned {total_matches} matches across {len(matches_data)} dates")
        else:
            print(f"      ❌ Returned no matches")
        
        print(f"   📊 Club data function:")
        if club_data and not club_data.get('error'):
            weekly_count = len(club_data.get('weekly_results', []))
            standings_count = len(club_data.get('tennaqua_standings', []))
            print(f"      ✅ Returned {weekly_count} weeks, {standings_count} standings")
        else:
            error_msg = club_data.get('error', 'Unknown error') if club_data else 'No data returned'
            print(f"      ❌ Failed: {error_msg}")
        
        print(f"\n💡 If functions return data here but my-club page shows sparse data,")
        print(f"    the issue may be in template rendering or front-end JavaScript.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 