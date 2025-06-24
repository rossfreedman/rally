#!/usr/bin/env python3
"""
Quick Test Database Cleanup

A simplified script for quickly cleaning test data before running tests.
This is designed to be called from test runners.

Usage:
    python scripts/quick_cleanup.py
"""

import os
import sys

# Add parent directory to path to import database_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_update


def quick_cleanup():
    """Quickly clean up common test data patterns"""
    print("🧹 Quick test database cleanup...")
    
    try:
        # Clean up in proper order respecting foreign keys
        cleanup_queries = [
            # Activity logs
            "DELETE FROM activity_log WHERE user_id IN (SELECT id FROM users WHERE email ILIKE '%test%' OR email ILIKE '%example%')",
            
            # User-player associations  
            "DELETE FROM user_player_associations WHERE user_id IN (SELECT id FROM users WHERE email ILIKE '%test%' OR email ILIKE '%example%')",
            
            # Poll responses
            "DELETE FROM poll_responses WHERE poll_id IN (SELECT id FROM polls WHERE created_by IN (SELECT id FROM users WHERE email ILIKE '%test%' OR email ILIKE '%example%'))",
            
            # Poll choices
            "DELETE FROM poll_choices WHERE poll_id IN (SELECT id FROM polls WHERE created_by IN (SELECT id FROM users WHERE email ILIKE '%test%' OR email ILIKE '%example%'))",
            
            # Polls
            "DELETE FROM polls WHERE created_by IN (SELECT id FROM users WHERE email ILIKE '%test%' OR email ILIKE '%example%')",
            
            # Test users
            "DELETE FROM users WHERE email ILIKE '%test%' OR email ILIKE '%example%' OR email ILIKE '%weak%' OR email ILIKE '%xss%' OR email ILIKE '%invalid%'",
        ]
        
        total_deleted = 0
        for query in cleanup_queries:
            try:
                result = execute_update(query)
                if hasattr(result, 'rowcount'):
                    total_deleted += result.rowcount
            except Exception as e:
                # Continue even if some queries fail
                pass
        
        print(f"✅ Cleaned up test data (approximate records affected: {total_deleted})")
        return True
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return False


if __name__ == '__main__':
    success = quick_cleanup()
    sys.exit(0 if success else 1) 