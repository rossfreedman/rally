#!/usr/bin/env python3
"""
Test Session Refresh System
===========================

This script tests the automatic session refresh system that fixes league context
issues after ETL imports. It demonstrates the end-to-end workflow and validates
that users no longer need to manually logout/login or switch leagues.

Usage:
    python scripts/test_session_refresh_system.py
    python scripts/test_session_refresh_system.py --create-test-signals
    python scripts/test_session_refresh_system.py --cleanup
"""

import sys
import os
import argparse
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.etl.database_import.session_refresh_service import SessionRefreshService
from database_config import get_db

def test_session_refresh_detection():
    """Test the league ID change detection system"""
    print("🔍 TESTING SESSION REFRESH DETECTION")
    print("=" * 50)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        try:
            # Test league ID change detection
            print("1. Testing league ID change detection...")
            changes = SessionRefreshService.detect_league_id_changes(cursor)
            
            if changes:
                print(f"   ✅ Detected {len(changes)} league ID changes:")
                for change in changes:
                    print(f"      {change['league_name']}: {change['old_id']} → {change['new_id']}")
            else:
                print("   ℹ️  No league ID changes detected")
            
            return len(changes)
            
        except Exception as e:
            print(f"   ❌ Detection test failed: {str(e)}")
            return 0

def test_refresh_signals_creation():
    """Test creation of refresh signals"""
    print("\n📊 TESTING REFRESH SIGNALS CREATION")
    print("=" * 50)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        try:
            # Test refresh signals creation
            print("1. Creating refresh signals...")
            session_refresh = SessionRefreshService()
            signals_created = session_refresh.create_refresh_signals_after_etl(cursor)
            
            if signals_created > 0:
                print(f"   ✅ Created {signals_created} refresh signals")
                
                # Get some example signals
                cursor.execute("""
                    SELECT email, league_name, old_league_id, new_league_id, created_at
                    FROM user_session_refresh_signals
                    ORDER BY created_at DESC
                    LIMIT 5
                """)
                
                examples = cursor.fetchall()
                print("   📋 Example refresh signals:")
                for example in examples:
                    print(f"      {example[0]}: {example[1]} ({example[2]} → {example[3]})")
            else:
                print("   ℹ️  No refresh signals needed")
            
            conn.commit()
            return signals_created
            
        except Exception as e:
            conn.rollback()
            print(f"   ❌ Signals creation test failed: {str(e)}")
            return 0

def test_user_refresh_workflow(test_email="test@example.com"):
    """Test the user session refresh workflow"""
    print(f"\n🔄 TESTING USER REFRESH WORKFLOW")
    print("=" * 50)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        try:
            # Check if user needs refresh
            print(f"1. Checking if {test_email} needs refresh...")
            needs_refresh = SessionRefreshService.should_refresh_session(test_email)
            print(f"   User needs refresh: {needs_refresh}")
            
            if needs_refresh:
                print("2. Refreshing user session...")
                refreshed_session = SessionRefreshService.refresh_user_session(test_email)
                
                if refreshed_session:
                    print(f"   ✅ Session refreshed successfully")
                    print(f"   New league: {refreshed_session.get('league_name', 'Unknown')}")
                    return True
                else:
                    print(f"   ❌ Session refresh failed")
                    return False
            else:
                print("   ℹ️  User doesn't need refresh")
                return True
                
        except Exception as e:
            print(f"   ❌ User refresh test failed: {str(e)}")
            return False

def test_system_status():
    """Test getting system-wide refresh status"""
    print("\n📈 TESTING SYSTEM STATUS")
    print("=" * 50)
    
    try:
        status = SessionRefreshService.get_refresh_status()
        
        print(f"1. System Status:")
        print(f"   Signals table exists: {status.get('signals_table_exists', False)}")
        print(f"   Total signals: {status.get('total_signals', 0)}")
        print(f"   Pending refreshes: {status.get('pending_refreshes', 0)}")
        print(f"   Completed refreshes: {status.get('completed_refreshes', 0)}")
        
        if status.get('recent_signals'):
            print(f"   Recent signals: {len(status['recent_signals'])}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ System status test failed: {str(e)}")
        return False

def create_test_refresh_signals():
    """Create test refresh signals for demonstration"""
    print("\n🧪 CREATING TEST REFRESH SIGNALS")
    print("=" * 50)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        try:
            # Create test signals table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_session_refresh_signals (
                    user_id INTEGER PRIMARY KEY,
                    email VARCHAR(255) NOT NULL,
                    old_league_id INTEGER,
                    new_league_id INTEGER,
                    league_name VARCHAR(255),
                    refresh_reason VARCHAR(255) DEFAULT 'etl_league_id_change',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    refreshed_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
                    is_refreshed BOOLEAN DEFAULT FALSE
                )
            """)
            
            # Get a real user for testing
            cursor.execute("""
                SELECT u.id, u.email, u.league_context, l.league_name
                FROM users u
                LEFT JOIN leagues l ON u.league_context = l.id
                WHERE u.email IS NOT NULL
                LIMIT 1
            """)
            
            test_user = cursor.fetchone()
            
            if test_user:
                user_id, email, league_context, league_name = test_user
                
                # Create test refresh signal
                cursor.execute("""
                    INSERT INTO user_session_refresh_signals 
                    (user_id, email, old_league_id, new_league_id, league_name, refresh_reason)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET
                        old_league_id = 999,  -- Fake old ID
                        new_league_id = EXCLUDED.new_league_id,
                        league_name = EXCLUDED.league_name,
                        created_at = NOW(),
                        is_refreshed = FALSE,
                        refresh_reason = 'test_signal'
                """, (user_id, email, 999, league_context, league_name or "Test League", "test_signal"))
                
                conn.commit()
                print(f"   ✅ Created test refresh signal for {email}")
                print(f"   League: {league_name} (999 → {league_context})")
                return True
            else:
                print("   ❌ No users found to create test signals")
                return False
                
        except Exception as e:
            conn.rollback()
            print(f"   ❌ Failed to create test signals: {str(e)}")
            return False

def cleanup_refresh_signals():
    """Clean up all refresh signals"""
    print("\n🧹 CLEANING UP REFRESH SIGNALS")
    print("=" * 50)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        try:
            # Check if table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'user_session_refresh_signals'
                )
            """)
            
            if cursor.fetchone()[0]:
                # Get count before cleanup
                cursor.execute("SELECT COUNT(*) FROM user_session_refresh_signals")
                before_count = cursor.fetchone()[0]
                
                # Drop the table
                cursor.execute("DROP TABLE user_session_refresh_signals")
                conn.commit()
                
                print(f"   ✅ Cleaned up {before_count} refresh signals")
                print(f"   Dropped user_session_refresh_signals table")
                return True
            else:
                print("   ℹ️  No refresh signals table found")
                return True
                
        except Exception as e:
            conn.rollback()
            print(f"   ❌ Cleanup failed: {str(e)}")
            return False

def show_integration_guide():
    """Show how to integrate the middleware into the Flask app"""
    print("\n📚 INTEGRATION GUIDE")
    print("=" * 50)
    
    print("""
To integrate the session refresh middleware into your Flask app:

1. Add to app/__init__.py or main app file:

   from app.middleware.session_refresh_middleware import SessionRefreshMiddleware
   
   app = create_app()
   SessionRefreshMiddleware(app)

2. Optional: Add response headers middleware:

   from app.middleware.session_refresh_middleware import SessionRefreshResponseMiddleware
   SessionRefreshResponseMiddleware(app)

3. Optional: Add template notifications:

   from app.middleware.session_refresh_middleware import register_template_functions
   register_template_functions(app)

4. API Endpoints Available:
   - GET /api/session-refresh-status  (check refresh status)
   - POST /api/refresh-session        (manual refresh)
   - POST /api/cleanup-session-refresh-signals (admin cleanup)

5. How It Works:
   - ETL runs → Creates refresh signals for affected users
   - User visits app → Middleware checks for refresh signals
   - If signal exists → Automatically refreshes session with new league context
   - User continues without disruption → No manual logout/login needed

6. Testing:
   - Run this script with --create-test-signals to test
   - Check /api/session-refresh-status to see current status
   - Monitor logs for automatic refresh messages
""")

def main():
    parser = argparse.ArgumentParser(description='Test session refresh system')
    parser.add_argument('--create-test-signals', action='store_true',
                       help='Create test refresh signals for demonstration')
    parser.add_argument('--cleanup', action='store_true',
                       help='Clean up all refresh signals')
    parser.add_argument('--test-email', default='test@example.com',
                       help='Email to use for user refresh testing')
    
    args = parser.parse_args()
    
    print("🔄 SESSION REFRESH SYSTEM TEST")
    print("=" * 60)
    print(f"📅 Test run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if args.cleanup:
        cleanup_refresh_signals()
        return
    
    if args.create_test_signals:
        create_test_refresh_signals()
        print("\n✅ Test signals created. You can now test the refresh workflow.")
        return
    
    # Run comprehensive tests
    tests_passed = 0
    total_tests = 4
    
    # Test 1: Detection
    if test_session_refresh_detection() >= 0:
        tests_passed += 1
    
    # Test 2: Signals creation
    if test_refresh_signals_creation() >= 0:
        tests_passed += 1
    
    # Test 3: User refresh workflow
    if test_user_refresh_workflow(args.test_email):
        tests_passed += 1
    
    # Test 4: System status
    if test_system_status():
        tests_passed += 1
    
    # Show results
    print(f"\n📊 TEST RESULTS")
    print("=" * 50)
    print(f"Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("✅ All tests passed! Session refresh system is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    # Show integration guide
    show_integration_guide()

if __name__ == "__main__":
    main() 