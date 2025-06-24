#!/usr/bin/env python3
"""
Rally Test Database Cleanup Script

This script safely removes test data from the database while preserving
production data. It handles foreign key constraints by cleaning up data
in the correct order.

Usage:
    python scripts/cleanup_test_database.py [--dry-run] [--verbose] [--all-test-data]

Options:
    --dry-run       Show what would be deleted without actually deleting
    --verbose       Show detailed progress information
    --all-test-data Clean up all test data including fixtures
"""

import argparse
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path to import database_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_update


def identify_test_patterns():
    """Define patterns that identify test data"""
    return {
        'email_patterns': [
            '%test%',
            '%example.com%',
            '%weak%',
            '%xss%',
            '%injection%',
            '%api@%',
            '%loadtest%',
            '%duplicate%',
            '%invalid%',
            '%security%',
            '%@test%',
            '%regression%',
        ],
        'name_patterns': [
            'Test%',
            'Invalid%',
            'XSS%',
            'SQL%',
            'Weak%',
            'API%',
            'Load%',
            'Duplicate%',
            'Security%',
        ]
    }


def get_test_user_ids(dry_run=False, verbose=False):
    """Get IDs of users that match test patterns"""
    patterns = identify_test_patterns()
    
    # Build query to find test users
    email_conditions = ' OR '.join([f"email ILIKE '{pattern}'" for pattern in patterns['email_patterns']])
    name_conditions = ' OR '.join([f"first_name ILIKE '{pattern}' OR last_name ILIKE '{pattern}'" for pattern in patterns['name_patterns']])
    
    query = f"""
        SELECT id, email, first_name, last_name, created_at
        FROM users 
        WHERE ({email_conditions}) OR ({name_conditions})
        ORDER BY id
    """
    
    try:
        test_users = execute_query(query)
        
        if verbose:
            print(f"📋 Found {len(test_users)} test users:")
            for user in test_users[:10]:  # Show first 10
                print(f"   ID {user['id']}: {user['email']} ({user['first_name']} {user['last_name']})")
            if len(test_users) > 10:
                print(f"   ... and {len(test_users) - 10} more")
        
        return [user['id'] for user in test_users]
        
    except Exception as e:
        print(f"❌ Error identifying test users: {e}")
        return []


def cleanup_activity_logs(test_user_ids, dry_run=False, verbose=False):
    """Clean up activity logs for test users"""
    if not test_user_ids:
        return 0
        
    query = "SELECT COUNT(*) as count FROM activity_log WHERE user_id = ANY(%s)"
    try:
        result = execute_query(query, [test_user_ids])
        count = result[0]['count'] if result else 0
        
        if verbose:
            print(f"🗂️  Found {count} activity log entries to clean")
            
        if count > 0 and not dry_run:
            delete_query = "DELETE FROM activity_log WHERE user_id = ANY(%s)"
            execute_update(delete_query, [test_user_ids])
            
        return count
    except Exception as e:
        print(f"❌ Error cleaning activity logs: {e}")
        return 0


def cleanup_user_player_associations(test_user_ids, dry_run=False, verbose=False):
    """Clean up user-player associations for test users"""
    if not test_user_ids:
        return 0
        
    query = "SELECT COUNT(*) as count FROM user_player_associations WHERE user_id = ANY(%s)"
    try:
        result = execute_query(query, [test_user_ids])
        count = result[0]['count'] if result else 0
        
        if verbose:
            print(f"🔗 Found {count} user-player associations to clean")
            
        if count > 0 and not dry_run:
            delete_query = "DELETE FROM user_player_associations WHERE user_id = ANY(%s)"
            execute_update(delete_query, [test_user_ids])
            
        return count
    except Exception as e:
        print(f"❌ Error cleaning user-player associations: {e}")
        return 0


def cleanup_poll_responses(test_user_ids, dry_run=False, verbose=False):
    """Clean up poll responses from polls created by test users"""
    if not test_user_ids:
        return 0
        
    query = """
        SELECT COUNT(*) as count 
        FROM poll_responses pr
        JOIN polls p ON pr.poll_id = p.id
        WHERE p.created_by = ANY(%s)
    """
    try:
        result = execute_query(query, [test_user_ids])
        count = result[0]['count'] if result else 0
        
        if verbose:
            print(f"🗳️  Found {count} poll responses to clean")
            
        if count > 0 and not dry_run:
            delete_query = """
                DELETE FROM poll_responses 
                WHERE poll_id IN (SELECT id FROM polls WHERE created_by = ANY(%s))
            """
            execute_update(delete_query, [test_user_ids])
            
        return count
    except Exception as e:
        print(f"❌ Error cleaning poll responses: {e}")
        return 0


def cleanup_poll_choices(test_user_ids, dry_run=False, verbose=False):
    """Clean up poll choices from polls created by test users"""
    if not test_user_ids:
        return 0
        
    query = """
        SELECT COUNT(*) as count 
        FROM poll_choices pc
        JOIN polls p ON pc.poll_id = p.id
        WHERE p.created_by = ANY(%s)
    """
    try:
        result = execute_query(query, [test_user_ids])
        count = result[0]['count'] if result else 0
        
        if verbose:
            print(f"📝 Found {count} poll choices to clean")
            
        if count > 0 and not dry_run:
            delete_query = """
                DELETE FROM poll_choices 
                WHERE poll_id IN (SELECT id FROM polls WHERE created_by = ANY(%s))
            """
            execute_update(delete_query, [test_user_ids])
            
        return count
    except Exception as e:
        print(f"❌ Error cleaning poll choices: {e}")
        return 0


def cleanup_polls(test_user_ids, dry_run=False, verbose=False):
    """Clean up polls created by test users"""
    if not test_user_ids:
        return 0
        
    query = "SELECT COUNT(*) as count FROM polls WHERE created_by = ANY(%s)"
    try:
        result = execute_query(query, [test_user_ids])
        count = result[0]['count'] if result else 0
        
        if verbose:
            print(f"📊 Found {count} polls to clean")
            
        if count > 0 and not dry_run:
            delete_query = "DELETE FROM polls WHERE created_by = ANY(%s)"
            execute_update(delete_query, [test_user_ids])
            
        return count
    except Exception as e:
        print(f"❌ Error cleaning polls: {e}")
        return 0


def cleanup_test_users(test_user_ids, dry_run=False, verbose=False):
    """Clean up test users themselves"""
    if not test_user_ids:
        return 0
        
    count = len(test_user_ids)
    
    if verbose:
        print(f"👤 Found {count} test users to clean")
        
    if count > 0 and not dry_run:
        delete_query = "DELETE FROM users WHERE id = ANY(%s)"
        execute_update(delete_query, [test_user_ids])
        
    return count


def cleanup_recent_test_data(hours=24, dry_run=False, verbose=False):
    """Clean up test data created in the last N hours"""
    cutoff_time = datetime.now() - timedelta(hours=hours)
    
    # Find recent test users
    query = """
        SELECT id FROM users 
        WHERE created_at > %s 
        AND (email ILIKE '%test%' OR email ILIKE '%example%')
    """
    
    try:
        result = execute_query(query, [cutoff_time])
        recent_user_ids = [row['id'] for row in result]
        
        if verbose and recent_user_ids:
            print(f"⏰ Found {len(recent_user_ids)} test users created in last {hours} hours")
            
        return recent_user_ids
    except Exception as e:
        print(f"❌ Error finding recent test data: {e}")
        return []


def get_database_stats():
    """Get current database statistics"""
    stats = {}
    
    tables = ['users', 'polls', 'poll_choices', 'poll_responses', 'user_player_associations', 'activity_log']
    
    for table in tables:
        try:
            result = execute_query(f"SELECT COUNT(*) as count FROM {table}")
            stats[table] = result[0]['count'] if result else 0
        except Exception:
            stats[table] = 'Error'
    
    return stats


def main():
    parser = argparse.ArgumentParser(description='Clean up Rally test database')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be deleted without actually deleting')
    parser.add_argument('--verbose', action='store_true',
                       help='Show detailed progress information')
    parser.add_argument('--all-test-data', action='store_true',
                       help='Clean up all test data including fixtures')
    parser.add_argument('--recent-only', type=int, metavar='HOURS',
                       help='Only clean test data from the last N hours')
    parser.add_argument('--include-reference-data', action='store_true',
                       help='Also clean up test reference data (leagues, clubs, series)')
    
    args = parser.parse_args()
    
    print("🧹 Rally Test Database Cleanup")
    print("=" * 50)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No data will be deleted")
        print()
    
    # Show initial stats
    if args.verbose:
        print("📊 Current database statistics:")
        initial_stats = get_database_stats()
        for table, count in initial_stats.items():
            print(f"   {table}: {count}")
        print()
    
    # Clean up reference data first if requested
    if args.include_reference_data:
        print("🗂️  Step 1: Cleaning reference data (leagues, clubs, series)...")
        try:
            import subprocess
            cmd = ["python", "scripts/cleanup_reference_data.py"]
            if args.dry_run:
                cmd.append("--dry-run")
            if args.verbose:
                cmd.append("--verbose")
            
            if not args.dry_run:
                # Auto-confirm for reference data cleanup
                result = subprocess.run(cmd, input="y\n", text=True, capture_output=True)
                if result.returncode == 0:
                    print("   ✅ Reference data cleanup completed")
                else:
                    print(f"   ⚠️  Reference data cleanup had issues: {result.stderr}")
            else:
                result = subprocess.run(cmd, capture_output=True, text=True)
                print("   🔍 Reference data dry run completed")
        except Exception as e:
            print(f"   ❌ Error running reference data cleanup: {e}")
        print()

    # Identify test users and related data
    print("🔍 Identifying test data...")
    test_users = get_test_user_ids(args.dry_run, args.verbose)
    
    if not test_users:
        print("✅ No test users found to clean up!")
        if not args.include_reference_data:
            return
        else:
            print("   Note: Reference data cleanup may have already run above.")
            return
    
    print(f"\n🎯 Found {len(test_users)} test users to process")
    
    if not args.dry_run:
        # Confirm deletion for large amounts of data
        if len(test_users) > 50:
            response = input(f"⚠️  About to delete data for {len(test_users)} users. Continue? (y/N): ")
            if response.lower() != 'y':
                print("❌ Cleanup cancelled")
                return
    
    print("\n🗂️  Cleaning up in proper order to respect foreign keys...")
    
    # Clean up in proper order to respect foreign key constraints
    cleanup_steps = [
        ("Activity Logs", cleanup_activity_logs),
        ("User-Player Associations", cleanup_user_player_associations),
        ("Poll Responses", cleanup_poll_responses),
        ("Poll Choices", cleanup_poll_choices),
        ("Polls", cleanup_polls),
        ("Test Users", cleanup_test_users),
    ]
    
    total_cleaned = 0
    for step_name, cleanup_func in cleanup_steps:
        if args.verbose:
            print(f"\n🔧 Processing: {step_name}")
        
        try:
            count = cleanup_func(test_users, args.dry_run, args.verbose)
            total_cleaned += count
            
            if count > 0:
                status = "would delete" if args.dry_run else "deleted"
                print(f"   ✅ {status.title()} {count} {step_name.lower()}")
            elif args.verbose:
                print(f"   ⏭️  No {step_name.lower()} found")
                
        except Exception as e:
            print(f"   ❌ Error processing {step_name}: {e}")
    
    # Show final stats
    print(f"\n📈 Summary:")
    print(f"   Users processed: {len(test_users)}")
    print(f"   Total records: {total_cleaned}")
    
    if not args.dry_run:
        print("   Status: ✅ Cleanup completed successfully!")
        
        if args.verbose:
            print("\n📊 Final database statistics:")
            final_stats = get_database_stats()
            for table, count in final_stats.items():
                print(f"   {table}: {count}")
    else:
        print("   Status: 🔍 Dry run completed (no data deleted)")
        print("\n💡 Run without --dry-run to actually delete the data")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Cleanup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1) 