#!/usr/bin/env python3
"""
Fix League Context Issue on Railway
===================================
This script specifically fixes the league_context field for users whose
session service is returning empty tenniscores_player_id due to mismatched
or NULL league_context values.
"""

import os
import sys

# Force Railway environment BEFORE importing database modules
os.environ['RAILWAY_ENVIRONMENT'] = 'production'
os.environ['DATABASE_PUBLIC_URL'] = 'postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway'

# Add the parent directory to path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one, execute_update


def diagnose_league_context_issues():
    """Diagnose league_context problems for all users"""
    print("🔍 DIAGNOSING LEAGUE CONTEXT ISSUES")
    print("=" * 50)
    
    # Get users with associations but problematic league_context
    problematic_users = execute_query("""
        SELECT DISTINCT
            u.id, u.email, u.first_name, u.last_name, u.league_context,
            STRING_AGG(DISTINCT l.league_name, ', ') as available_leagues,
            STRING_AGG(DISTINCT l.id::text, ', ') as available_league_ids,
            COUNT(DISTINCT p.tenniscores_player_id) as player_count
        FROM users u
        JOIN user_player_associations upa ON u.id = upa.user_id
        JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
        JOIN leagues l ON p.league_id = l.id
        WHERE p.is_active = TRUE
        GROUP BY u.id, u.email, u.first_name, u.last_name, u.league_context
        HAVING u.league_context IS NULL 
            OR u.league_context NOT IN (
                SELECT DISTINCT p2.league_id 
                FROM players p2 
                JOIN user_player_associations upa2 ON p2.tenniscores_player_id = upa2.tenniscores_player_id 
                WHERE upa2.user_id = u.id AND p2.is_active = TRUE
            )
        ORDER BY u.email
    """)
    
    if not problematic_users:
        print("   ✅ No league_context issues found!")
        return []
    
    print(f"   Found {len(problematic_users)} users with league_context issues:")
    
    for user in problematic_users:
        context_status = f"NULL" if user['league_context'] is None else f"Invalid ({user['league_context']})"
        print(f"\n   • {user['first_name']} {user['last_name']} ({user['email']})")
        print(f"     Current league_context: {context_status}")
        print(f"     Available leagues: {user['available_leagues']}")
        print(f"     Available league IDs: {user['available_league_ids']}")
        print(f"     Player count: {user['player_count']}")
    
    return problematic_users


def test_session_query_for_user(user_email):
    """Test what the session service query returns for a specific user"""
    print(f"\n🧪 TESTING SESSION QUERY FOR: {user_email}")
    print("=" * 60)
    
    # This is the exact query from session_service.py
    session_query = """
        SELECT 
            u.id,
            u.email, 
            u.first_name, 
            u.last_name,
            u.is_admin,
            u.ad_deuce_preference,
            u.dominant_hand,
            u.league_context,
            -- Player data from league_context with ALL required IDs
            p.tenniscores_player_id,
            p.team_id,
            p.club_id,
            p.series_id,
            c.name as club,
            s.name as series,
            l.id as league_db_id,
            l.league_id as league_string_id,
            l.league_name
        FROM users u
        LEFT JOIN user_player_associations upa ON u.id = upa.user_id
        LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id 
            AND p.league_id = u.league_context 
            AND p.is_active = TRUE
        LEFT JOIN clubs c ON p.club_id = c.id
        LEFT JOIN series s ON p.series_id = s.id
        LEFT JOIN leagues l ON p.league_id = l.id
        WHERE u.email = %s
        ORDER BY (CASE WHEN p.tenniscores_player_id IS NOT NULL THEN 1 ELSE 2 END)
        LIMIT 1
    """
    
    result = execute_query_one(session_query, [user_email])
    
    if result:
        print(f"   📊 Session query result:")
        print(f"      User ID: {result['id']}")
        print(f"      League context: {result['league_context']}")
        print(f"      Tennis player ID: {result['tenniscores_player_id']}")
        print(f"      Club: {result['club']}")
        print(f"      Series: {result['series']}")
        print(f"      League: {result['league_name']}")
        
        if result['tenniscores_player_id']:
            print(f"      ✅ Session query would return valid player ID")
        else:
            print(f"      ❌ Session query returns NULL player ID (this causes the alert)")
    else:
        print(f"   ❌ No result from session query")
    
    # Also test what associations exist
    associations = execute_query("""
        SELECT upa.tenniscores_player_id, p.league_id, l.league_name, p.is_active,
               c.name as club, s.name as series
        FROM user_player_associations upa
        JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
        JOIN leagues l ON p.league_id = l.id
        LEFT JOIN clubs c ON p.club_id = c.id
        LEFT JOIN series s ON p.series_id = s.id
        JOIN users u ON upa.user_id = u.id
        WHERE u.email = %s
        ORDER BY p.is_active DESC, l.league_name
    """, [user_email])
    
    print(f"\n   📋 User's actual associations:")
    for assoc in associations:
        status = "ACTIVE" if assoc['is_active'] else "INACTIVE"
        print(f"      • Player ID: {assoc['tenniscores_player_id']} ({status})")
        print(f"        League: {assoc['league_name']} (DB ID: {assoc['league_id']})")
        print(f"        Club: {assoc['club']}, Series: {assoc['series']}")
    
    return result


def fix_league_context_for_user(user_email, preferred_league_id=None):
    """Fix league_context for a specific user"""
    print(f"\n🔧 FIXING LEAGUE CONTEXT FOR: {user_email}")
    print("=" * 50)
    
    # Get user's available leagues
    user_leagues = execute_query("""
        SELECT DISTINCT l.id, l.league_id, l.league_name, 
               COUNT(p.id) as player_count,
               MAX(CASE WHEN p.is_active THEN 1 ELSE 0 END) as has_active_players
        FROM users u
        JOIN user_player_associations upa ON u.id = upa.user_id
        JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
        JOIN leagues l ON p.league_id = l.id
        WHERE u.email = %s
        GROUP BY l.id, l.league_id, l.league_name
        ORDER BY has_active_players DESC, player_count DESC, l.league_name
    """, [user_email])
    
    if not user_leagues:
        print(f"   ❌ No leagues found for user")
        return False
    
    print(f"   Available leagues:")
    for i, league in enumerate(user_leagues, 1):
        active_status = "with ACTIVE players" if league['has_active_players'] else "with INACTIVE players"
        print(f"      {i}. {league['league_name']} (ID: {league['id']}) - {league['player_count']} players {active_status}")
    
    # Select league to use
    target_league = None
    
    if preferred_league_id:
        # Use specified league
        for league in user_leagues:
            if league['id'] == preferred_league_id:
                target_league = league
                break
        if not target_league:
            print(f"   ⚠️  Preferred league ID {preferred_league_id} not found")
    
    if not target_league:
        # Auto-select best league (active players, most players, APTA preference)
        for league in user_leagues:
            if league['has_active_players']:
                # Prefer APTA Chicago
                if 'APTA' in league['league_name']:
                    target_league = league
                    break
                # Otherwise take first active league
                elif not target_league:
                    target_league = league
        
        # Fallback to any league
        if not target_league:
            target_league = user_leagues[0]
    
    print(f"   🎯 Selected league: {target_league['league_name']} (DB ID: {target_league['id']})")
    
    # Update user's league_context
    result = execute_update("""
        UPDATE users 
        SET league_context = %s
        WHERE email = %s
    """, [target_league['id'], user_email])
    
    if result > 0:
        print(f"   ✅ Updated league_context to {target_league['id']}")
        return True
    else:
        print(f"   ❌ Failed to update league_context")
        return False


def fix_all_problematic_users():
    """Fix league_context for all problematic users"""
    print(f"\n🔧 FIXING ALL PROBLEMATIC USERS")
    print("=" * 40)
    
    problematic_users = diagnose_league_context_issues()
    
    if not problematic_users:
        return 0
    
    fixed_count = 0
    
    for user in problematic_users:
        print(f"\n   Processing: {user['first_name']} {user['last_name']} ({user['email']})")
        
        # Parse available league IDs
        available_ids = [int(id_str.strip()) for id_str in user['available_league_ids'].split(',')]
        
        # Prefer APTA Chicago if available
        preferred_id = None
        for league_id in available_ids:
            league_info = execute_query_one("SELECT league_name FROM leagues WHERE id = %s", [league_id])
            if league_info and 'APTA' in league_info['league_name']:
                preferred_id = league_id
                break
        
        # Use first available if no APTA found
        if not preferred_id:
            preferred_id = available_ids[0]
        
        success = fix_league_context_for_user(user['email'], preferred_id)
        if success:
            fixed_count += 1
    
    return fixed_count


def main():
    """Main execution function"""
    print("🔧 FIXING LEAGUE CONTEXT ISSUES ON RAILWAY")
    print("=" * 50)
    
    try:
        print("✅ Using Railway database connection")
        
        # Test specific user first (Ross)
        test_session_query_for_user("rossfreedman@gmail.com")
        
        # Diagnose all issues
        problematic_users = diagnose_league_context_issues()
        
        if not problematic_users:
            print(f"\n✅ No issues found! All users should have working sessions.")
            return
        
        # Ask user what to do
        print(f"\n❓ Do you want to fix these league_context issues?")
        print("   1. Yes, fix them all")
        print("   2. Fix just Ross (rossfreedman@gmail.com)")
        print("   3. Cancel")
        
        choice = input("\nEnter choice (1/2/3): ").strip()
        
        if choice == "3":
            print("❌ Cancelled by user")
            return
        elif choice == "2":
            # Fix just Ross
            success = fix_league_context_for_user("rossfreedman@gmail.com")
            if success:
                print(f"\n✅ Fixed Ross's league_context!")
                test_session_query_for_user("rossfreedman@gmail.com")
        elif choice == "1":
            # Fix all
            fixed_count = fix_all_problematic_users()
            print(f"\n✅ Fixed {fixed_count} users' league_context!")
        else:
            print("❌ Invalid choice")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    main() 