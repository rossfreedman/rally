#!/usr/bin/env python3
"""
Test script to verify the registration transaction fix

This script tests that users are not added to the database when registration fails
due to duplicate player ID associations.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.auth_service_refactored import register_user
from database_utils import execute_query_one, execute_query, execute_update
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_test_data():
    """Clean up any test data"""
    try:
        execute_update("DELETE FROM user_player_associations WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test_registration_%')")
        execute_update("DELETE FROM users WHERE email LIKE 'test_registration_%'")
        logger.info("Cleaned up test data")
    except Exception as e:
        logger.error(f"Error cleaning up test data: {e}")

def test_registration_with_existing_player_association():
    """Test that registration fails and doesn't create user when player ID is already associated"""
    
    print("\n🧪 Testing Registration Transaction Fix")
    print("=" * 50)
    
    # Clean up first
    cleanup_test_data()
    
    # Find an existing player association to test against
    existing_association = execute_query_one("""
        SELECT upa.tenniscores_player_id, u.email, p.first_name, p.last_name, 
               c.name as club_name, s.name as series_name, l.league_id
        FROM user_player_associations upa
        JOIN users u ON upa.user_id = u.id
        JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
        JOIN clubs c ON p.club_id = c.id
        JOIN series s ON p.series_id = s.id
        JOIN leagues l ON p.league_id = l.id
        WHERE p.is_active = true
        LIMIT 1
    """)
    
    if not existing_association:
        print("❌ No existing player associations found to test against")
        return False
    
    player_id = existing_association['tenniscores_player_id']
    existing_email = existing_association['email']
    
    print(f"📍 Testing with existing player: {existing_association['first_name']} {existing_association['last_name']}")
    print(f"   Player ID: {player_id}")
    print(f"   Already associated with: {existing_email}")
    print(f"   Club: {existing_association['club_name']}")
    print(f"   Series: {existing_association['series_name']}")
    print(f"   League: {existing_association['league_id']}")
    
    # Count users before registration attempt
    user_count_before = execute_query_one("SELECT COUNT(*) as count FROM users")['count']
    print(f"\n📊 Users in database before test: {user_count_before}")
    
    # Try to register a new user with the same player details
    test_email = "test_registration_duplicate@example.com"
    
    print(f"\n🔄 Attempting to register duplicate user: {test_email}")
    print(f"   Using same player details as existing association")
    
    result = register_user(
        email=test_email,
        password="testpassword123",
        first_name=existing_association['first_name'],
        last_name=existing_association['last_name'],
        league_id=existing_association['league_id'],
        club_name=existing_association['club_name'],
        series_name=existing_association['series_name']
    )
    
    # Check if registration failed as expected
    if not result["success"]:
        print(f"✅ Registration failed as expected: {result['error']}")
        
        # Check that no user was created
        user_count_after = execute_query_one("SELECT COUNT(*) as count FROM users")['count']
        print(f"📊 Users in database after test: {user_count_after}")
        
        if user_count_after == user_count_before:
            print("✅ SUCCESS: No user record was created when association failed")
            
            # Double-check that the test email doesn't exist
            test_user = execute_query_one("SELECT id FROM users WHERE email = %s", [test_email])
            if not test_user:
                print("✅ VERIFIED: Test email not found in database")
                return True
            else:
                print("❌ FAILED: Test user was created despite registration failure")
                return False
        else:
            print("❌ FAILED: User count changed - user was created despite registration failure")
            return False
    else:
        print(f"❌ FAILED: Registration succeeded when it should have failed")
        print(f"   Result: {result}")
        return False

def test_successful_registration():
    """Test that normal registration still works"""
    
    print("\n🧪 Testing Normal Registration")
    print("=" * 30)
    
    # Count users before registration
    user_count_before = execute_query_one("SELECT COUNT(*) as count FROM users")['count']
    
    # Try to register a new user without any player association
    test_email = "test_registration_normal@example.com"
    
    print(f"🔄 Attempting normal registration: {test_email}")
    
    result = register_user(
        email=test_email,
        password="testpassword123",
        first_name="Test",
        last_name="User"
    )
    
    if result["success"]:
        print("✅ Registration succeeded as expected")
        
        # Check that user was created
        user_count_after = execute_query_one("SELECT COUNT(*) as count FROM users")['count']
        
        if user_count_after == user_count_before + 1:
            print("✅ SUCCESS: User was created for normal registration")
            return True
        else:
            print("❌ FAILED: User count didn't increase")
            return False
    else:
        print(f"❌ FAILED: Normal registration failed: {result['error']}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Registration Transaction Fix Tests")
    
    try:
        # Test 1: Registration with duplicate player association should fail and not create user
        test1_passed = test_registration_with_existing_player_association()
        
        # Test 2: Normal registration should still work
        test2_passed = test_successful_registration()
        
        print(f"\n📝 Test Results:")
        print(f"  Test 1 (Duplicate Association): {'✅ PASS' if test1_passed else '❌ FAIL'}")
        print(f"  Test 2 (Normal Registration): {'✅ PASS' if test2_passed else '❌ FAIL'}")
        
        if test1_passed and test2_passed:
            print("\n🎉 All tests passed! Registration transaction fix is working correctly.")
        else:
            print("\n⚠️  Some tests failed. Please check the implementation.")
            
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        print(f"❌ Test execution failed: {e}")
    finally:
        # Clean up test data
        cleanup_test_data()

if __name__ == "__main__":
    main() 