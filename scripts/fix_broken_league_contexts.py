#!/usr/bin/env python3

"""
Fix Broken League Contexts
==========================

This script detects and fixes users who have league_context settings that don't
match any of their actual player associations. This causes the session service
to return NULL tenniscores_player_id, triggering the profile alert.

Usage:
    python scripts/fix_broken_league_contexts.py [--dry-run] [--specific-user EMAIL]
"""

import sys
import os
import argparse
from datetime import datetime

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_update, execute_query_one


def detect_broken_league_contexts():
    """Detect users with broken league_context settings"""
    print("🔍 DETECTING BROKEN LEAGUE CONTEXTS")
    print("=" * 50)
    
    # Find users whose league_context doesn't match any of their associations
    broken_contexts_query = """
        SELECT DISTINCT
            u.id,
            u.email,
            u.first_name,
            u.last_name,
            u.league_context,
            l_context.league_name as context_league_name,
            COUNT(upa.tenniscores_player_id) as total_associations
        FROM users u
        LEFT JOIN leagues l_context ON u.league_context = l_context.id
        LEFT JOIN user_player_associations upa ON u.id = upa.user_id
        WHERE u.league_context IS NOT NULL  -- Only check users with a context set
        GROUP BY u.id, u.email, u.first_name, u.last_name, u.league_context, l_context.league_name
        HAVING u.league_context NOT IN (
            -- Check if league_context matches any of their actual league associations
            SELECT DISTINCT p.league_id
            FROM user_player_associations upa_inner
            JOIN players p ON upa_inner.tenniscores_player_id = p.tenniscores_player_id
            WHERE upa_inner.user_id = u.id
            AND p.is_active = true
        )
        AND COUNT(upa.tenniscores_player_id) > 0  -- Only users who have associations
        ORDER BY u.email
    """
    
    broken_users = execute_query(broken_contexts_query)
    
    print(f"Found {len(broken_users)} users with broken league_context settings:")
    
    for user in broken_users:
        print(f"\n👤 {user['first_name']} {user['last_name']} ({user['email']})")
        print(f"   Current league_context: {user['league_context']} ({user['context_league_name'] or 'INVALID LEAGUE'})")
        print(f"   Total associations: {user['total_associations']}")
        
        # Get their actual associations
        user_associations = execute_query("""
            SELECT p.league_id, l.league_name, l.league_id as league_string_id,
                   c.name as club_name, s.name as series_name,
                   p.tenniscores_player_id
            FROM user_player_associations upa
            JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
            JOIN leagues l ON p.league_id = l.id
            JOIN clubs c ON p.club_id = c.id
            JOIN series s ON p.series_id = s.id
            WHERE upa.user_id = %s
            AND p.is_active = true
            ORDER BY l.league_name
        """, [user['id']])
        
        print(f"   Actual associations:")
        for assoc in user_associations:
            print(f"     - {assoc['league_name']} (ID: {assoc['league_id']}): {assoc['club_name']} / {assoc['series_name']}")
    
    return broken_users


def suggest_league_context_fix(user_id, email):
    """Suggest the best league_context for a user"""
    
    # Get user's associations with match activity data
    associations_query = """
        SELECT 
            p.league_id,
            l.league_name,
            l.league_id as league_string_id,
            c.name as club_name,
            s.name as series_name,
            p.tenniscores_player_id,
            p.team_id,
            COUNT(ms.id) as match_count,
            MAX(ms.match_date) as last_match_date
        FROM user_player_associations upa
        JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
        JOIN leagues l ON p.league_id = l.id
        JOIN clubs c ON p.club_id = c.id
        JOIN series s ON p.series_id = s.id
        LEFT JOIN match_scores ms ON (
            (ms.home_player_1_id = p.tenniscores_player_id OR 
             ms.home_player_2_id = p.tenniscores_player_id OR
             ms.away_player_1_id = p.tenniscores_player_id OR 
             ms.away_player_2_id = p.tenniscores_player_id)
            AND ms.league_id = p.league_id
        )
        WHERE upa.user_id = %s
        AND p.is_active = true
        GROUP BY p.league_id, l.league_name, l.league_id, c.name, s.name, p.tenniscores_player_id, p.team_id
        ORDER BY 
            (CASE WHEN p.team_id IS NOT NULL THEN 1 ELSE 2 END),  -- Prefer players with teams
            COUNT(ms.id) DESC,  -- Most active league
            MAX(ms.match_date) DESC NULLS LAST  -- Most recent activity
    """
    
    associations = execute_query(associations_query, [user_id])
    
    if not associations:
        return None
    
    # Return the "best" association (first in the ordered list)
    best_association = associations[0]
    
    return {
        "league_id": best_association["league_id"],
        "league_name": best_association["league_name"],
        "club_name": best_association["club_name"],
        "series_name": best_association["series_name"],
        "tenniscores_player_id": best_association["tenniscores_player_id"],
        "match_count": best_association["match_count"],
        "last_match_date": best_association["last_match_date"],
        "reason": "Most active league with team assignment" if best_association["team_id"] else "Most active league"
    }


def fix_broken_league_contexts(broken_users, dry_run=False):
    """Fix broken league contexts by setting them to the user's most active league"""
    print(f"\n🔧 FIXING BROKEN LEAGUE CONTEXTS")
    print("=" * 50)
    
    fixed_count = 0
    failed_count = 0
    
    for user in broken_users:
        try:
            print(f"\n👤 Fixing {user['first_name']} {user['last_name']} ({user['email']})...")
            
            # Get suggested fix
            suggestion = suggest_league_context_fix(user['id'], user['email'])
            
            if not suggestion:
                print(f"   ❌ No valid associations found")
                failed_count += 1
                continue
            
            print(f"   Suggested league_context: {suggestion['league_id']} ({suggestion['league_name']})")
            print(f"   Reason: {suggestion['reason']}")
            print(f"   Match activity: {suggestion['match_count']} matches")
            if suggestion['last_match_date']:
                print(f"   Last match: {suggestion['last_match_date']}")
            
            if not dry_run:
                # Apply the fix
                execute_update("""
                    UPDATE users 
                    SET league_context = %s
                    WHERE id = %s
                """, [suggestion['league_id'], user['id']])
                
                # Verify the fix works
                test_session_query = """
                    SELECT p.tenniscores_player_id, l.league_name, c.name as club, s.name as series
                    FROM users u
                    LEFT JOIN user_player_associations upa ON u.id = upa.user_id
                    LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id 
                        AND p.league_id = u.league_context 
                        AND p.is_active = TRUE
                    LEFT JOIN leagues l ON p.league_id = l.id
                    LEFT JOIN clubs c ON p.club_id = c.id
                    LEFT JOIN series s ON p.series_id = s.id
                    WHERE u.id = %s
                    LIMIT 1
                """
                
                test_result = execute_query_one(test_session_query, [user['id']])
                
                if test_result and test_result['tenniscores_player_id']:
                    print(f"   ✅ Fix verified - session now returns: {test_result['tenniscores_player_id']}")
                    print(f"      League: {test_result['league_name']}, Club: {test_result['club']}")
                    fixed_count += 1
                else:
                    print(f"   ❌ Fix failed - session still returns NULL")
                    failed_count += 1
            else:
                print(f"   [DRY RUN] Would set league_context to {suggestion['league_id']}")
                
        except Exception as e:
            print(f"   ❌ Error fixing user {user['email']}: {e}")
            failed_count += 1
    
    return fixed_count, failed_count


def check_system_wide_league_context_health():
    """Check overall system health for league contexts"""
    print("\n💊 SYSTEM-WIDE LEAGUE CONTEXT HEALTH")
    print("=" * 50)
    
    # Total users with associations
    total_users_with_assoc = execute_query_one("""
        SELECT COUNT(DISTINCT u.id) as count
        FROM users u
        JOIN user_player_associations upa ON u.id = upa.user_id
    """)['count']
    
    # Users with NULL league_context
    null_context_count = execute_query_one("""
        SELECT COUNT(DISTINCT u.id) as count
        FROM users u
        JOIN user_player_associations upa ON u.id = upa.user_id
        WHERE u.league_context IS NULL
    """)['count']
    
    # Users with valid league_context
    valid_context_count = execute_query_one("""
        SELECT COUNT(DISTINCT u.id) as count
        FROM users u
        JOIN user_player_associations upa ON u.id = upa.user_id
        JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
        WHERE u.league_context = p.league_id AND p.is_active = true
    """)['count']
    
    # Users with broken league_context  
    broken_context_count = total_users_with_assoc - null_context_count - valid_context_count
    
    print(f"📊 League Context Statistics:")
    print(f"   Total users with associations: {total_users_with_assoc}")
    print(f"   Users with NULL context: {null_context_count}")
    print(f"   Users with valid context: {valid_context_count}")
    print(f"   Users with broken context: {broken_context_count}")
    
    if total_users_with_assoc > 0:
        health_score = (valid_context_count / total_users_with_assoc) * 100
        print(f"\n💊 HEALTH SCORE: {health_score:.1f}%")
        
        if health_score < 70:
            print("🚨 CRITICAL: Many users have broken league contexts")
        elif health_score < 90:
            print("⚠️  WARNING: Some users have broken league contexts")
        else:
            print("✅ GOOD: Most users have valid league contexts")
    
    return {
        "total": total_users_with_assoc,
        "null": null_context_count,
        "valid": valid_context_count,
        "broken": broken_context_count
    }


def main():
    parser = argparse.ArgumentParser(description="Fix broken league_context settings")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be done without making changes")
    parser.add_argument("--specific-user", type=str,
                       help="Process only this specific user (by email)")
    
    args = parser.parse_args()
    
    print("🔧 RALLY LEAGUE CONTEXT REPAIR SYSTEM")
    print("=" * 50)
    print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if args.dry_run:
        print("🚫 DRY RUN MODE - No changes will be made")
    
    try:
        # Step 1: System health check
        health_stats = check_system_wide_league_context_health()
        
        # Step 2: Detect broken contexts
        if args.specific_user:
            # Check specific user
            user_query = execute_query_one("""
                SELECT id, email, first_name, last_name, league_context
                FROM users 
                WHERE LOWER(email) = LOWER(%s)
            """, [args.specific_user])
            
            if not user_query:
                print(f"❌ User not found: {args.specific_user}")
                return 1
            
            # Test if this user has a broken context
            broken_users = []
            suggestion = suggest_league_context_fix(user_query['id'], user_query['email'])
            
            if user_query['league_context'] and suggestion:
                # Check if current context matches any associations
                current_context_valid = execute_query_one("""
                    SELECT COUNT(*) as count
                    FROM user_player_associations upa
                    JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                    WHERE upa.user_id = %s 
                    AND p.league_id = %s 
                    AND p.is_active = true
                """, [user_query['id'], user_query['league_context']])
                
                if current_context_valid['count'] == 0:
                    broken_users = [user_query]
                    print(f"🎯 User {args.specific_user} has broken league_context")
                else:
                    print(f"✅ User {args.specific_user} has valid league_context")
            else:
                print(f"ℹ️  User {args.specific_user} has NULL league_context")
        else:
            # Check all users
            broken_users = detect_broken_league_contexts()
        
        # Step 3: Fix broken contexts
        if broken_users:
            fixed_count, failed_count = fix_broken_league_contexts(broken_users, dry_run=args.dry_run)
            
            print(f"\n📊 REPAIR RESULTS:")
            print(f"   Users processed: {len(broken_users)}")
            if not args.dry_run:
                print(f"   Successfully fixed: {fixed_count}")
                print(f"   Failed to fix: {failed_count}")
                
                if fixed_count > 0:
                    print(f"\n🎉 SUCCESS: Fixed {fixed_count} broken league contexts!")
                    print("   Users should no longer see the profile alert")
            else:
                print(f"   [DRY RUN] Would attempt to fix {len(broken_users)} users")
        else:
            print("\n✅ No broken league contexts found - system is healthy!")
        
        # Step 4: Final health check
        if not args.dry_run and broken_users:
            print("\n" + "=" * 50)
            final_health = check_system_wide_league_context_health()
            
            if final_health["broken"] < health_stats["broken"]:
                improvement = health_stats["broken"] - final_health["broken"]
                print(f"📈 IMPROVEMENT: Fixed {improvement} broken contexts")
        
        print(f"\n🏁 Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 