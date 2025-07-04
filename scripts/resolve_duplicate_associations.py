#!/usr/bin/env python3
"""
Resolve Duplicate Player Associations
====================================

This script identifies and resolves duplicate player associations in the staging database
before applying the unique constraint migration.
"""

import os
import sys
import subprocess
import logging
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from database_utils import execute_query, execute_query_one, execute_update

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def identify_duplicates():
    """Identify duplicate player associations"""
    print("🔍 Identifying duplicate player associations...")
    
    query = """
        SELECT 
            upa.tenniscores_player_id,
            COUNT(DISTINCT upa.user_id) as user_count,
            STRING_AGG(DISTINCT u.email, ', ') as user_emails,
            STRING_AGG(DISTINCT u.id::text, ', ') as user_ids
        FROM user_player_associations upa
        JOIN users u ON upa.user_id = u.id
        GROUP BY upa.tenniscores_player_id
        HAVING COUNT(DISTINCT upa.user_id) > 1
        ORDER BY user_count DESC
    """
    
    duplicates = execute_query(query)
    
    if not duplicates:
        print("✅ No duplicate associations found!")
        return []
    
    print(f"❌ Found {len(duplicates)} duplicate associations:")
    for dup in duplicates:
        print(f"  - Player ID: {dup['tenniscores_player_id']}")
        print(f"    Users: {dup['user_count']} ({dup['user_emails']})")
        print(f"    User IDs: {dup['user_ids']}")
        print()
    
    return duplicates

def get_player_details(player_id):
    """Get player details for the duplicate player ID"""
    query = """
        SELECT 
            p.first_name, p.last_name, p.email,
            c.name as club_name,
            s.name as series_name,
            l.league_name,
            p.is_active
        FROM players p
        LEFT JOIN clubs c ON p.club_id = c.id
        LEFT JOIN series s ON p.series_id = s.id
        LEFT JOIN leagues l ON p.league_id = l.id
        WHERE p.tenniscores_player_id = %s
        LIMIT 1
    """
    
    return execute_query_one(query, [player_id])

def get_user_details_for_association(player_id):
    """Get user details for users associated with the duplicate player ID"""
    query = """
        SELECT 
            u.id, u.email, u.first_name, u.last_name, u.created_at,
            upa.created_at as association_created_at
        FROM user_player_associations upa
        JOIN users u ON upa.user_id = u.id
        WHERE upa.tenniscores_player_id = %s
        ORDER BY upa.created_at ASC
    """
    
    return execute_query(query, [player_id])

def resolve_duplicate_association(player_id, user_details):
    """
    Resolve duplicate association by keeping the first user and removing others
    """
    print(f"\n🔧 Resolving duplicate for player ID: {player_id}")
    
    # Get player details
    player = get_player_details(player_id)
    if player:
        print(f"   Player: {player['first_name']} {player['last_name']} ({player['club_name']}, {player['series_name']})")
    
    print("   Associated users:")
    for i, user in enumerate(user_details):
        print(f"     {i+1}. {user['email']} (ID: {user['id']}) - Created: {user['association_created_at']}")
    
    # Strategy: Keep the first association (oldest) and remove the others
    keep_user = user_details[0]
    remove_users = user_details[1:]
    
    print(f"\n   📌 Strategy: Keep oldest association ({keep_user['email']})")
    print(f"   🗑️  Remove {len(remove_users)} newer association(s)")
    
    # Remove duplicate associations
    for user in remove_users:
        print(f"      Removing association: {user['email']} → {player_id}")
        
        # Delete the association
        delete_query = """
            DELETE FROM user_player_associations 
            WHERE user_id = %s AND tenniscores_player_id = %s
        """
        
        try:
            execute_update(delete_query, [user['id'], player_id])
            print(f"      ✅ Removed association for {user['email']}")
        except Exception as e:
            print(f"      ❌ Error removing association for {user['email']}: {e}")
            return False
    
    print(f"   ✅ Duplicate resolved - {keep_user['email']} remains associated with {player_id}")
    return True

def resolve_all_duplicates():
    """Resolve all duplicate associations"""
    print("🚀 Resolving Duplicate Player Associations")
    print("=" * 60)
    
    # Identify duplicates
    duplicates = identify_duplicates()
    
    if not duplicates:
        return True
    
    print(f"📋 Found {len(duplicates)} duplicate(s) to resolve...")
    
    # Resolve each duplicate
    success_count = 0
    for dup in duplicates:
        player_id = dup['tenniscores_player_id']
        
        # Get detailed user information
        user_details = get_user_details_for_association(player_id)
        
        # Resolve the duplicate
        if resolve_duplicate_association(player_id, user_details):
            success_count += 1
        else:
            print(f"❌ Failed to resolve duplicate for {player_id}")
    
    print(f"\n📊 Resolution Summary:")
    print(f"   Total duplicates: {len(duplicates)}")
    print(f"   Successfully resolved: {success_count}")
    print(f"   Failed: {len(duplicates) - success_count}")
    
    if success_count == len(duplicates):
        print("\n✅ All duplicates resolved successfully!")
        return True
    else:
        print("\n❌ Some duplicates could not be resolved")
        return False

def verify_no_duplicates():
    """Verify that no duplicates remain"""
    print("\n🔍 Verifying no duplicates remain...")
    
    remaining = identify_duplicates()
    
    if not remaining:
        print("✅ Verification passed - no duplicates found!")
        return True
    else:
        print(f"❌ Verification failed - {len(remaining)} duplicates still exist")
        return False

def main():
    """Main function"""
    print("🚀 Duplicate Association Resolution for Staging")
    print("=" * 60)
    
    try:
        # Resolve all duplicates
        if resolve_all_duplicates():
            # Verify resolution
            if verify_no_duplicates():
                print("\n🎉 All duplicates resolved! Ready to apply unique constraint.")
                print("\n📝 Next step:")
                print("   Run: python3 scripts/apply_migration_to_staging.py")
                return 0
            else:
                print("\n⚠️  Verification failed - manual intervention may be required")
                return 1
        else:
            print("\n❌ Failed to resolve all duplicates")
            return 1
            
    except Exception as e:
        logger.error(f"Script execution failed: {e}")
        print(f"❌ Script execution failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 