#!/usr/bin/env python3
"""
Test Database Utilities

Collection of utility functions for managing test database state.
"""

import os
import sys
from datetime import datetime

# Add parent directory to path to import database_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_update


def get_test_user_count():
    """Get count of test users in database"""
    try:
        query = """
            SELECT COUNT(*) as count FROM users 
            WHERE email ILIKE '%test%' OR email ILIKE '%example%' 
            OR email ILIKE '%weak%' OR email ILIKE '%xss%'
        """
        result = execute_query(query)
        return result[0]['count'] if result else 0
    except Exception:
        return 0


def is_database_clean():
    """Check if database is clean of test data"""
    return get_test_user_count() == 0


def create_test_isolation():
    """Ensure clean test environment"""
    from scripts.quick_cleanup import quick_cleanup
    return quick_cleanup()


def get_database_health():
    """Get overall database health statistics"""
    tables = {
        'users': 'SELECT COUNT(*) as count FROM users',
        'polls': 'SELECT COUNT(*) as count FROM polls', 
        'poll_responses': 'SELECT COUNT(*) as count FROM poll_responses',
        'players': 'SELECT COUNT(*) as count FROM players',
        'teams': 'SELECT COUNT(*) as count FROM teams',
        'matches': 'SELECT COUNT(*) as count FROM match_scores',
    }
    
    stats = {}
    for table, query in tables.items():
        try:
            result = execute_query(query)
            stats[table] = result[0]['count'] if result else 0
        except Exception:
            stats[table] = 'Error'
    
    # Add test data info
    stats['test_users'] = get_test_user_count()
    stats['is_clean'] = is_database_clean()
    stats['checked_at'] = datetime.now().isoformat()
    
    return stats


def print_database_status():
    """Print formatted database status"""
    stats = get_database_health()
    
    print("📊 Database Status")
    print("-" * 30)
    print(f"Users: {stats['users']}")
    print(f"Players: {stats['players']}")
    print(f"Teams: {stats['teams']}")
    print(f"Polls: {stats['polls']}")
    print(f"Poll Responses: {stats['poll_responses']}")
    print(f"Matches: {stats['matches']}")
    print("-" * 30)
    print(f"Test Users: {stats['test_users']}")
    print(f"Clean Status: {'✅ Clean' if stats['is_clean'] else '⚠️ Has Test Data'}")
    print(f"Checked: {stats['checked_at']}")


def full_cleanup():
    """Comprehensive cleanup of all test data including reference data"""
    try:
        import subprocess
        print("🧹 Running comprehensive test database cleanup...")
        
        # Run comprehensive cleanup with reference data
        cmd = ["python", "scripts/cleanup_test_database.py", 
               "--include-reference-data", "--verbose"]
        
        # Auto-confirm for automated cleanup
        result = subprocess.run(cmd, input="y\n", text=True, capture_output=True)
        
        if result.returncode == 0:
            print("✅ Comprehensive cleanup completed successfully!")
            print("   - Removed fake leagues, clubs, series")
            print("   - Cleaned test users and associated data")
            print_database_status()
        else:
            print(f"❌ Cleanup failed: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Error running comprehensive cleanup: {e}")


def quick_cleanup_runner():
    """Quick cleanup using the fast cleanup script"""
    try:
        import subprocess
        print("⚡ Running quick test data cleanup...")
        
        result = subprocess.run(["python", "scripts/quick_cleanup.py"], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Quick cleanup completed!")
            print(result.stdout)
        else:
            print(f"❌ Quick cleanup failed: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Error running quick cleanup: {e}")


def verify_cleanup():
    """Verify database is clean of test data"""
    clean = is_database_clean()
    test_count = get_test_user_count()
    
    if clean:
        print("✅ Database is clean - no test data found")
    else:
        print(f"⚠️  Database has test data - {test_count} test users found")
        print("   Run 'python scripts/test_database_utils.py full' to clean")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Rally Test Database Utilities")
        print("Usage: python scripts/test_database_utils.py <command>")
        print()
        print("Commands:")
        print("  status     - Show current database status")
        print("  verify     - Verify database is clean")
        print("  reset      - Quick reset to clean state")
        print("  full       - Comprehensive cleanup (includes reference data)")
        print("  quick      - Quick cleanup (fast)")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'status':
        print_database_status()
    elif command == 'verify':
        verify_cleanup()
    elif command == 'reset':
        quick_cleanup_runner()
    elif command == 'full':
        full_cleanup()
    elif command == 'quick':
        quick_cleanup_runner()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1) 