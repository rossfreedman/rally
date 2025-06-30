#!/usr/bin/env python3
"""
Fix All User-Player Associations on Railway
==========================================
This script finds all users without player associations on Railway
and attempts to create associations by matching users with player records.
"""

import os
import sys

# Force Railway environment BEFORE importing database modules
os.environ['RAILWAY_ENVIRONMENT'] = 'production'
os.environ['DATABASE_PUBLIC_URL'] = 'postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway'

# Add the parent directory to path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import database utilities using the existing config system
from database_config import get_db
from database_utils import execute_query, execute_query_one, execute_update


def analyze_association_status():
    """Analyze the current state of user-player associations"""
    print("📊 ANALYZING ASSOCIATION STATUS")
    print("=" * 50)
    
    # Get total users
    total_users = execute_query_one("SELECT COUNT(*) as count FROM users")['count']
    print(f"   Total users in database: {total_users}")
    
    # Get users with associations
    users_with_associations = execute_query_one("""
        SELECT COUNT(DISTINCT user_id) as count 
        FROM user_player_associations
    """)['count']
    print(f"   Users with associations: {users_with_associations}")
    
    # Get users without associations
    users_without = total_users - users_with_associations
    print(f"   Users WITHOUT associations: {users_without}")
    
    if users_without == 0:
        print("   ✅ All users already have associations!")
        return False
    
    # Show some examples of users without associations
    users_without_assoc = execute_query("""
        SELECT u.id, u.email, u.first_name, u.last_name, u.league_context
        FROM users u
        LEFT JOIN user_player_associations upa ON u.id = upa.user_id
        WHERE upa.user_id IS NULL
        ORDER BY u.created_at DESC
        LIMIT 10
    """)
    
    print(f"\n   📋 Examples of users without associations:")
    for user in users_without_assoc:
        context = f" (league_context: {user['league_context']})" if user['league_context'] else ""
        print(f"      • {user['first_name']} {user['last_name']} ({user['email']}){context}")
    
    return True


def find_matching_players(user):
    """Find potential player matches for a user"""
    # Try exact name match first
    players = execute_query("""
        SELECT p.id, p.tenniscores_player_id, p.first_name, p.last_name,
               c.name as club_name, s.name as series_name, 
               l.league_name, l.id as league_db_id, l.league_id as league_string_id,
               p.is_active, p.email as player_email
        FROM players p
        JOIN clubs c ON p.club_id = c.id
        JOIN series s ON p.series_id = s.id  
        JOIN leagues l ON p.league_id = l.id
        WHERE LOWER(TRIM(p.first_name)) = LOWER(TRIM(%s)) 
          AND LOWER(TRIM(p.last_name)) = LOWER(TRIM(%s))
        ORDER BY p.is_active DESC, 
                 CASE WHEN LOWER(c.name) = 'tennaqua' THEN 1 ELSE 2 END,
                 l.league_name
    """, [user['first_name'], user['last_name']])
    
    # If no exact match, try email match
    if not players and user['email']:
        players = execute_query("""
            SELECT p.id, p.tenniscores_player_id, p.first_name, p.last_name,
                   c.name as club_name, s.name as series_name, 
                   l.league_name, l.id as league_db_id, l.league_id as league_string_id,
                   p.is_active, p.email as player_email
            FROM players p
            JOIN clubs c ON p.club_id = c.id
            JOIN series s ON p.series_id = s.id  
            JOIN leagues l ON p.league_id = l.id
            WHERE LOWER(TRIM(p.email)) = LOWER(TRIM(%s))
            ORDER BY p.is_active DESC, l.league_name
        """, [user['email']])
    
    return players


def select_best_player_match(user, players, user_league_context=None):
    """Select the best player match for a user"""
    if not players:
        return None, []
    
    # Scoring system for player selection
    scored_players = []
    
    for player in players:
        score = 0
        reasons = []
        
        # Active players get priority
        if player['is_active']:
            score += 10
            reasons.append("active")
        
        # League context match
        if user_league_context and user_league_context == player['league_db_id']:
            score += 8
            reasons.append("league_context_match")
        
        # Tennaqua preference (Ross's club)
        if player['club_name'] and 'tennaqua' in player['club_name'].lower():
            score += 5
            reasons.append("tennaqua_club")
        
        # Email match
        if (user['email'] and player['player_email'] and 
            user['email'].lower() == player['player_email'].lower()):
            score += 7
            reasons.append("email_match")
        
        # Prefer certain leagues (APTA Chicago is main)
        if 'APTA' in player['league_name']:
            score += 3
            reasons.append("APTA_league")
        
        scored_players.append({
            'player': player,
            'score': score,
            'reasons': reasons
        })
    
    # Sort by score descending
    scored_players.sort(key=lambda x: x['score'], reverse=True)
    
    return scored_players[0]['player'], scored_players[0]['reasons']


def create_association(user_id, player_record, league_context=None):
    """Create a user-player association"""
    try:
        # Update user's league context if provided and different
        if league_context:
            current_context = execute_query_one(
                "SELECT league_context FROM users WHERE id = %s", [user_id])
            
            if not current_context['league_context'] or current_context['league_context'] != league_context:
                execute_update("""
                    UPDATE users 
                    SET league_context = %s
                    WHERE id = %s
                """, [league_context, user_id])
        
        # Create the association
        result = execute_update("""
            INSERT INTO user_player_associations (user_id, tenniscores_player_id, created_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (user_id, tenniscores_player_id) DO NOTHING
        """, [user_id, player_record['tenniscores_player_id']])
        
        return result > 0
            
    except Exception as e:
        print(f"      ❌ Error creating association: {e}")
        return False


def fix_all_user_associations(dry_run=False):
    """Fix associations for all users without them"""
    print(f"\n🔧 FIXING USER ASSOCIATIONS (DRY RUN: {dry_run})")
    print("=" * 60)
    
    # Get all users without associations
    users_without_assoc = execute_query("""
        SELECT u.id, u.email, u.first_name, u.last_name, u.league_context
        FROM users u
        LEFT JOIN user_player_associations upa ON u.id = upa.user_id
        WHERE upa.user_id IS NULL
        ORDER BY u.created_at
    """)
    
    if not users_without_assoc:
        print("   ✅ All users already have associations!")
        return 0
    
    print(f"   Found {len(users_without_assoc)} users without associations")
    
    fixed_count = 0
    failed_count = 0
    skipped_count = 0
    
    for i, user in enumerate(users_without_assoc, 1):
        print(f"\n   [{i}/{len(users_without_assoc)}] Processing: {user['first_name']} {user['last_name']} ({user['email']})")
        
        # Find matching players
        players = find_matching_players(user)
        
        if not players:
            print(f"      ⚠️  No matching players found")
            skipped_count += 1
            continue
        
        # Select best match
        best_player, reasons = select_best_player_match(user, players, user['league_context'])
        
        print(f"      🎯 Best match: {best_player['first_name']} {best_player['last_name']}")
        print(f"         Player ID: {best_player['tenniscores_player_id']}")
        print(f"         Club: {best_player['club_name']}")
        print(f"         Series: {best_player['series_name']}")
        print(f"         League: {best_player['league_name']}")
        print(f"         Status: {'ACTIVE' if best_player['is_active'] else 'INACTIVE'}")
        print(f"         Reasons: {', '.join(reasons)}")
        
        if not dry_run:
            # Create the association
            success = create_association(
                user['id'], 
                best_player, 
                league_context=best_player['league_db_id']
            )
            
            if success:
                print(f"      ✅ Created association")
                fixed_count += 1
            else:
                print(f"      ❌ Failed to create association")
                failed_count += 1
        else:
            print(f"      🔍 Would create association (dry run)")
            fixed_count += 1
    
    print(f"\n📊 SUMMARY:")
    print(f"   ✅ Fixed: {fixed_count}")
    print(f"   ❌ Failed: {failed_count}")
    print(f"   ⚠️  Skipped: {skipped_count}")
    
    return fixed_count


def verify_fixes():
    """Verify that the fixes worked"""
    print(f"\n🔍 VERIFYING FIXES")
    print("=" * 30)
    
    # Check association counts
    total_users = execute_query_one("SELECT COUNT(*) as count FROM users")['count']
    users_with_associations = execute_query_one("""
        SELECT COUNT(DISTINCT user_id) as count 
        FROM user_player_associations
    """)['count']
    
    print(f"   Total users: {total_users}")
    print(f"   Users with associations: {users_with_associations}")
    print(f"   Coverage: {users_with_associations}/{total_users} ({100*users_with_associations/total_users:.1f}%)")
    
    # Show sample successful associations
    sample_associations = execute_query("""
        SELECT u.email, u.first_name, u.last_name,
               upa.tenniscores_player_id, upa.created_at,
               p.first_name as player_first, p.last_name as player_last,
               c.name as club_name, l.league_name
        FROM user_player_associations upa
        JOIN users u ON upa.user_id = u.id
        JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
        JOIN clubs c ON p.club_id = c.id
        JOIN leagues l ON p.league_id = l.id
        ORDER BY upa.created_at DESC
        LIMIT 5
    """)
    
    print(f"\n   Recent associations:")
    for assoc in sample_associations:
        print(f"      • {assoc['first_name']} {assoc['last_name']} → {assoc['player_first']} {assoc['player_last']}")
        print(f"        Club: {assoc['club_name']}, League: {assoc['league_name']}")


def main():
    """Main execution function"""
    print("🔧 FIXING ALL USER-PLAYER ASSOCIATIONS ON RAILWAY")
    print("=" * 60)
    
    try:
        print("✅ Using Railway database connection")
        
        # Analyze current status
        needs_fixing = analyze_association_status()
        
        if not needs_fixing:
            return
        
        # Ask user if they want to proceed
        print(f"\n❓ Do you want to proceed with fixing user associations?")
        print("   1. Yes, fix them (LIVE)")
        print("   2. Dry run first (see what would happen)")
        print("   3. Cancel")
        
        choice = input("\nEnter choice (1/2/3): ").strip()
        
        if choice == "3":
            print("❌ Cancelled by user")
            return
        elif choice == "2":
            # Dry run
            fix_all_user_associations(dry_run=True)
        elif choice == "1":
            # Live run
            fixed_count = fix_all_user_associations(dry_run=False)
            if fixed_count > 0:
                verify_fixes()
                print(f"\n✅ SUCCESS! Fixed {fixed_count} user associations.")
                print(f"   Users should no longer see the yellow alert banner.")
        else:
            print("❌ Invalid choice")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    main() 