#!/usr/bin/env python3
"""
Fix Duplicate Player Associations in Production

This script identifies and resolves cases where multiple users are associated 
with the same player ID, which violates the intended 1-player-to-1-user mapping.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from database_utils import execute_query, execute_query_one, execute_update

def analyze_duplicate_associations():
    """Analyze all duplicate player associations"""
    
    print("🔍 ANALYZING DUPLICATE PLAYER ASSOCIATIONS")
    print("=" * 50)
    
    # Find all player IDs with multiple user associations
    duplicates_query = """
        SELECT 
            upa.tenniscores_player_id,
            COUNT(*) as user_count,
            ARRAY_AGG(upa.user_id ORDER BY u.created_at ASC) as user_ids,
            ARRAY_AGG(u.email ORDER BY u.created_at ASC) as emails,
            ARRAY_AGG(u.created_at ORDER BY u.created_at ASC) as created_dates,
            ARRAY_AGG(u.last_login ORDER BY u.created_at ASC) as last_logins
        FROM user_player_associations upa
        JOIN users u ON upa.user_id = u.id
        GROUP BY upa.tenniscores_player_id
        HAVING COUNT(*) > 1
        ORDER BY COUNT(*) DESC
    """
    
    duplicates = execute_query(duplicates_query)
    
    if not duplicates:
        print("✅ No duplicate player associations found!")
        return []
    
    print(f"🚨 Found {len(duplicates)} player IDs with multiple user associations:")
    
    duplicate_analysis = []
    
    for i, dup in enumerate(duplicates, 1):
        player_id = dup['tenniscores_player_id']
        user_count = dup['user_count']
        user_ids = dup['user_ids']
        emails = dup['emails']
        created_dates = dup['created_dates']
        last_logins = dup['last_logins']
        
        print(f"\n{i}. Player ID: {player_id}")
        print(f"   Associated with {user_count} users:")
        
        # Get player details
        player_info_query = """
            SELECT DISTINCT p.first_name, p.last_name, l.league_name, c.name as club_name, s.name as series_name
            FROM players p
            LEFT JOIN leagues l ON p.league_id = l.id
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE p.tenniscores_player_id = %s
            LIMIT 1
        """
        
        player_info = execute_query_one(player_info_query, [player_id])
        if player_info:
            print(f"   Player: {player_info['first_name']} {player_info['last_name']}")
            print(f"   League: {player_info['league_name']}")
            print(f"   Club: {player_info['club_name']}")
            print(f"   Series: {player_info['series_name']}")
        
        user_details = []
        for j, (user_id, email, created_date, last_login) in enumerate(zip(user_ids, emails, created_dates, last_logins)):
            
            # Check user activity level
            activity_query = """
                SELECT 
                    COUNT(DISTINCT upa2.tenniscores_player_id) as total_associations,
                    u.first_name, u.last_name
                FROM users u
                LEFT JOIN user_player_associations upa2 ON u.id = upa2.user_id
                WHERE u.id = %s
                GROUP BY u.id, u.first_name, u.last_name
            """
            
            activity = execute_query_one(activity_query, [user_id])
            total_associations = activity['total_associations'] if activity else 0
            user_name = f"{activity['first_name']} {activity['last_name']}" if activity else "Unknown"
            
            user_detail = {
                "user_id": user_id,
                "email": email,
                "name": user_name,
                "created_at": created_date,
                "last_login": last_login,
                "total_associations": total_associations,
                "is_oldest": j == 0  # First in the ordered list
            }
            
            user_details.append(user_detail)
            
            login_status = "Never logged in" if not last_login else f"Last: {last_login}"
            priority_marker = " ⭐ (OLDEST)" if j == 0 else ""
            
            print(f"     {j+1}. User {user_id}: {email} ({user_name})")
            print(f"        Created: {created_date}")
            print(f"        Login: {login_status}")
            print(f"        Total Associations: {total_associations}{priority_marker}")
        
        duplicate_analysis.append({
            "player_id": player_id,
            "player_info": player_info,
            "user_count": user_count,
            "user_details": user_details
        })
    
    return duplicate_analysis


def recommend_fix_strategy(duplicate_analysis):
    """Recommend which user should keep each association"""
    
    print(f"\n🎯 RECOMMENDED FIX STRATEGY")
    print("=" * 50)
    
    fix_plan = []
    
    for dup in duplicate_analysis:
        player_id = dup['player_id']
        user_details = dup['user_details']
        
        print(f"\nPlayer ID: {player_id}")
        
        # Strategy: Keep the oldest user (first to register) unless they never logged in
        # and another user has logged in recently
        
        oldest_user = user_details[0]  # First in chronological order
        most_recent_login = None
        most_active_user = None
        
        for user in user_details:
            if user['last_login'] and (not most_recent_login or user['last_login'] > most_recent_login):
                most_recent_login = user['last_login']
                most_active_user = user
        
        # Decision logic
        if oldest_user['last_login']:
            # Oldest user has logged in - they keep it
            keep_user = oldest_user
            reason = "Oldest user who has logged in"
        elif most_active_user:
            # Oldest never logged in, but another user has - give it to the active user
            keep_user = most_active_user
            reason = "Most recent active user (oldest never logged in)"
        else:
            # Nobody has logged in - keep oldest
            keep_user = oldest_user
            reason = "Oldest user (default - nobody has logged in)"
        
        remove_users = [u for u in user_details if u['user_id'] != keep_user['user_id']]
        
        print(f"   KEEP: User {keep_user['user_id']} ({keep_user['email']}) - {reason}")
        print(f"   REMOVE: {len(remove_users)} duplicate association(s)")
        
        for user in remove_users:
            print(f"     - User {user['user_id']} ({user['email']})")
        
        fix_plan.append({
            "player_id": player_id,
            "keep_user": keep_user,
            "remove_users": remove_users,
            "reason": reason
        })
    
    return fix_plan


def apply_fixes(fix_plan, dry_run=True):
    """Apply the fixes to remove duplicate associations"""
    
    mode = "DRY RUN" if dry_run else "LIVE EXECUTION"
    print(f"\n🔧 APPLYING FIXES - {mode}")
    print("=" * 50)
    
    if dry_run:
        print("⚠️  DRY RUN MODE - No changes will be made to the database")
    else:
        print("🚨 LIVE MODE - Changes will be applied to the database")
        
        # Safety check
        confirmation = input("\nType 'CONFIRM' to proceed with live fixes: ")
        if confirmation != 'CONFIRM':
            print("❌ Aborted - user did not confirm")
            return False
    
    fixes_applied = 0
    
    for fix in fix_plan:
        player_id = fix['player_id']
        keep_user = fix['keep_user']
        remove_users = fix['remove_users']
        
        print(f"\nFixing Player ID: {player_id}")
        print(f"  Keeping: User {keep_user['user_id']} ({keep_user['email']})")
        
        for user in remove_users:
            print(f"  Removing: User {user['user_id']} ({user['email']})")
            
            if not dry_run:
                # Remove the duplicate association
                rows_deleted = execute_update(
                    "DELETE FROM user_player_associations WHERE user_id = %s AND tenniscores_player_id = %s",
                    [user['user_id'], player_id]
                )
                
                if rows_deleted > 0:
                    print(f"    ✅ Removed association for User {user['user_id']}")
                    fixes_applied += 1
                else:
                    print(f"    ⚠️  No association found to remove for User {user['user_id']}")
            else:
                print(f"    📝 Would remove association for User {user['user_id']}")
                fixes_applied += 1
    
    print(f"\n📊 SUMMARY:")
    print(f"   Total fixes {'applied' if not dry_run else 'planned'}: {fixes_applied}")
    
    if not dry_run:
        print(f"   Duplicate associations removed from database")
        
        # Verify no duplicates remain
        remaining_duplicates = execute_query("""
            SELECT 
                upa.tenniscores_player_id,
                COUNT(*) as user_count
            FROM user_player_associations upa
            GROUP BY upa.tenniscores_player_id
            HAVING COUNT(*) > 1
        """)
        
        if remaining_duplicates:
            print(f"   ⚠️  WARNING: {len(remaining_duplicates)} duplicates still remain!")
        else:
            print(f"   ✅ SUCCESS: No duplicate associations remain")
    
    return True


def main():
    """Main execution function"""
    
    print("🏓 RALLY DUPLICATE PLAYER ASSOCIATION FIX")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)
    
    # Check environment
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "local")
    print(f"Environment: {railway_env}")
    
    if railway_env == "production":
        print("⚠️  RUNNING ON PRODUCTION - Use extreme caution!")
        
        confirmation = input("\nType 'PRODUCTION' to confirm you want to run this on production: ")
        if confirmation != 'PRODUCTION':
            print("❌ Aborted - production not confirmed")
            return
    
    # Step 1: Analyze duplicates
    duplicate_analysis = analyze_duplicate_associations()
    
    if not duplicate_analysis:
        print("\n✅ No action needed - no duplicate associations found")
        return
    
    # Step 2: Recommend fixes
    fix_plan = recommend_fix_strategy(duplicate_analysis)
    
    # Step 3: Apply fixes (dry run first)
    print("\n" + "=" * 50)
    apply_fixes(fix_plan, dry_run=True)
    
    # Option to run live
    if railway_env == "production":
        print("\n" + "=" * 50)
        run_live = input("\nRun live fixes? Type 'YES' to proceed: ")
        if run_live == 'YES':
            apply_fixes(fix_plan, dry_run=False)
        else:
            print("Dry run completed. Live fixes not applied.")
    else:
        print("\nDry run completed. To run live fixes, set RAILWAY_ENVIRONMENT=production")


if __name__ == "__main__":
    main() 