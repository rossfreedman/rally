#!/usr/bin/env python3
"""
PRODUCTION: Simulate Denise Siegel's login session building.
This replicates what happens when she logs in - builds her session data.
"""

import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Production database URL
PROD_DB_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

def simulate_login_session():
    """
    Simulate the session building logic from get_session_data_for_user()
    This is what happens after authentication when building the session.
    """
    
    user_email = "siegeldenise@yahoo.com"
    
    print("=" * 80)
    print("PRODUCTION: SIMULATING DENISE SIEGEL'S LOGIN")
    print("=" * 80)
    print(f"User Email: {user_email}")
    print()
    
    conn = psycopg2.connect(PROD_DB_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # This is the exact query from get_session_data_for_user() in session_service.py
        print("STEP 1: Building session data (same logic as get_session_data_for_user)...")
        print("-" * 80)
        
        session_query = """
            SELECT DISTINCT ON (u.id)
                u.id, u.email, u.first_name, u.last_name, u.is_admin,
                u.phone_number, u.ad_deuce_preference, u.dominant_hand, u.league_context,
                
                -- Player data (prioritize UserContext active_team_id first)
                c.name as club, c.logo_filename as club_logo,
                s.name as series, p.tenniscores_player_id,
                c.id as club_id, s.id as series_id, t.id as team_id,
                t.team_name, t.display_name,
                
                -- League data
                l.id as league_db_id, l.league_id as league_string_id, l.league_name,
                
                -- UserContext data
                uc.team_id as context_team_id
            FROM users u
            LEFT JOIN user_contexts uc ON u.id = uc.user_id
            LEFT JOIN user_player_associations upa ON u.id = upa.user_id
            LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id AND p.is_active = true
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            LEFT JOIN teams t ON p.team_id = t.id
            LEFT JOIN leagues l ON t.league_id = l.id
            WHERE u.email = %s
            ORDER BY u.id, 
                     -- PRIORITY 1: League context match (league switching takes precedence)
                     (CASE WHEN p.league_id = u.league_context THEN 1 ELSE 2 END),
                     -- PRIORITY 2: UserContext team_id match (registration choice within league)
                     (CASE WHEN p.team_id = uc.team_id THEN 1 ELSE 2 END),
                     -- PRIORITY 3: Team has team_id (prefer teams over unassigned players)
                     (CASE WHEN p.team_id IS NOT NULL THEN 1 ELSE 2 END),
                     -- PRIORITY 4: Most recent player record (newer registrations first)
                     p.id DESC
            LIMIT 1
        """
        
        cursor.execute(session_query, (user_email,))
        result = cursor.fetchone()
        
        if not result:
            print("✗ No session data returned - login would fail!")
            return
        
        print("✓ Session data built successfully!")
        print()
        
        # Show the session data that would be created
        print("STEP 2: Session data that will be stored in Flask session...")
        print("-" * 80)
        print(f"User Information:")
        print(f"  ID: {result['id']}")
        print(f"  Email: {result['email']}")
        print(f"  Name: {result['first_name']} {result['last_name']}")
        print(f"  Is Admin: {result['is_admin']}")
        print()
        
        print(f"Team/Player Context:")
        print(f"  Tenniscores Player ID: {result['tenniscores_player_id']}")
        print(f"  Club: {result['club']}")
        print(f"  Series: {result['series']}")
        print(f"  Team ID: {result['team_id']}")
        print(f"  Team Name: {result['team_name']}")
        print()
        
        print(f"League Information:")
        print(f"  League ID (DB): {result['league_db_id']}")
        print(f"  League String ID: {result['league_string_id']}")
        print(f"  League Name: {result['league_name']}")
        print()
        
        print(f"Context Information:")
        print(f"  League Context: {result['league_context']}")
        print(f"  User Context Team ID: {result['context_team_id']}")
        print()
        
        # Verify the expected values
        print("=" * 80)
        print("VERIFICATION")
        print("=" * 80)
        
        expected_series = "Series I"
        expected_team_name = "Tennaqua I"
        expected_club = "Tennaqua"
        expected_team_id = 59318
        
        all_correct = True
        
        if result['series'] == expected_series:
            print(f"✅ Series: {result['series']} (CORRECT)")
        else:
            print(f"❌ Series: {result['series']} (EXPECTED: {expected_series})")
            all_correct = False
        
        if result['team_name'] == expected_team_name:
            print(f"✅ Team Name: {result['team_name']} (CORRECT)")
        else:
            print(f"❌ Team Name: {result['team_name']} (EXPECTED: {expected_team_name})")
            all_correct = False
        
        if result['club'] == expected_club:
            print(f"✅ Club: {result['club']} (CORRECT)")
        else:
            print(f"❌ Club: {result['club']} (EXPECTED: {expected_club})")
            all_correct = False
        
        if result['team_id'] == expected_team_id:
            print(f"✅ Team ID: {result['team_id']} (CORRECT)")
        else:
            print(f"❌ Team ID: {result['team_id']} (EXPECTED: {expected_team_id})")
            all_correct = False
        
        print()
        
        if all_correct:
            print("=" * 80)
            print("🎉 SUCCESS! LOGIN SIMULATION PASSED")
            print("=" * 80)
            print()
            print("When Denise logs in, she will see:")
            print(f"  • Team: {result['team_name']}")
            print(f"  • Series: {result['series']}")
            print(f"  • Club: {result['club']}")
            print(f"  • League: {result['league_name']}")
            print()
            print("The fix is working correctly in production! ✅")
            print("=" * 80)
        else:
            print("=" * 80)
            print("❌ VERIFICATION FAILED")
            print("=" * 80)
            print("The session data does not match expected values.")
            print("Additional investigation needed.")
            print("=" * 80)
        
    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    simulate_login_session()

