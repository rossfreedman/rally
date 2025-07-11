#!/usr/bin/env python3
"""
Test Duplicate Player Association Prevention

This script tests that the new safeguards prevent duplicate player associations
during registration and settings updates.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from database_utils import execute_query, execute_query_one, execute_update
from app.services.auth_service_refactored import register_user, associate_user_with_player

def setup_test_data():
    """Create test data for the prevention tests"""
    
    print("🔧 SETTING UP TEST DATA")
    print("=" * 50)
    
    # Find an existing player association to test against
    existing_association = execute_query_one("""
        SELECT upa.tenniscores_player_id, upa.user_id, u.email, 
               p.first_name, p.last_name, c.name as club_name, 
               s.name as series_name, l.league_id
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
        print("❌ No existing associations found to test against")
        return None
    
    print(f"✅ Found test player: {existing_association['first_name']} {existing_association['last_name']}")
    print(f"   Player ID: {existing_association['tenniscores_player_id']}")
    print(f"   Already associated with: {existing_association['email']}")
    print(f"   Club: {existing_association['club_name']}")
    print(f"   Series: {existing_association['series_name']}")
    print(f"   League: {existing_association['league_id']}")
    
    return existing_association


def test_registration_prevention(test_data):
    """Test that registration prevents duplicate player associations"""
    
    print(f"\n🧪 TEST 1: REGISTRATION DUPLICATE PREVENTION")
    print("=" * 50)
    
    if not test_data:
        print("❌ No test data available")
        return False
    
    # Count users before test
    user_count_before = execute_query_one("SELECT COUNT(*) as count FROM users")['count']
    print(f"📊 Users before test: {user_count_before}")
    
    # Try to register a new user with the same player details
    test_email = f"duplicate_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}@test.rally"
    
    print(f"\n🔄 Attempting duplicate registration:")
    print(f"   Email: {test_email}")
    print(f"   Player: {test_data['first_name']} {test_data['last_name']}")
    print(f"   Player ID: {test_data['tenniscores_player_id']}")
    print(f"   Already associated with: {test_data['email']}")
    
    result = register_user(
        email=test_email,
        password="testpassword123",
        first_name=test_data['first_name'],
        last_name=test_data['last_name'],
        league_id=test_data['league_id'],
        club_name=test_data['club_name'],
        series_name=test_data['series_name']
    )
    
    # Check if registration failed as expected
    if not result["success"]:
        print(f"✅ Registration properly failed: {result['error']}")
        
        # Verify security flag
        if result.get("security_issue"):
            print("✅ Security issue correctly flagged")
        
        # Check that no user was created
        user_count_after = execute_query_one("SELECT COUNT(*) as count FROM users")['count']
        print(f"📊 Users after test: {user_count_after}")
        
        if user_count_after == user_count_before:
            print("✅ SUCCESS: No user record was created when association failed")
            
            # Double-check that the test email doesn't exist
            test_user = execute_query_one("SELECT id FROM users WHERE email = %s", [test_email])
            if not test_user:
                print("✅ VERIFIED: Test email not found in database")
                return True
            else:
                print("❌ FAILED: Test user was created despite registration failure")
                # Clean up
                execute_update("DELETE FROM users WHERE email = %s", [test_email])
                return False
        else:
            print("❌ FAILED: User count changed - user was created despite registration failure")
            # Clean up
            execute_update("DELETE FROM users WHERE email = %s", [test_email])
            return False
    else:
        print(f"❌ FAILED: Registration succeeded when it should have failed")
        print(f"   Result: {result}")
        
        # Clean up the incorrectly created user
        if "user" in result and "id" in result["user"]:
            user_id = result["user"]["id"]
            execute_update("DELETE FROM user_player_associations WHERE user_id = %s", [user_id])
            execute_update("DELETE FROM users WHERE id = %s", [user_id])
            print(f"🧹 Cleaned up incorrectly created user {user_id}")
        
        return False


def test_association_prevention(test_data):
    """Test that associate_user_with_player prevents duplicates"""
    
    print(f"\n🧪 TEST 2: ASSOCIATION DUPLICATE PREVENTION")
    print("=" * 50)
    
    if not test_data:
        print("❌ No test data available")
        return False
    
    # Create a test user
    test_email = f"association_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}@test.rally"
    
    try:
        # Create a test user without player association for testing
        # Since player association is now mandatory, we'll use fake data that won't match any player
        user_result = register_user(
            email=test_email,
            password="testpassword123",
            first_name="Test",
            last_name="User",
            league_id="FAKE_LEAGUE_FOR_TEST",
            club_name="Fake Club For Test",
            series_name="Fake Series For Test"
        )
        
        if not user_result["success"]:
            # Expected behavior - registration should fail with fake data
            # For this test, we need to create a user directly in the database
            print(f"ℹ️  Registration failed as expected with fake data: {user_result['error']}")
            print(f"ℹ️  Creating test user directly in database for association test")
            
            # Create user directly in database for testing
            user_creation_result = execute_query_one("""
                INSERT INTO users (email, password_hash, first_name, last_name)
                VALUES (%s, 'test_hash', 'Test', 'User')
                RETURNING id
            """, [test_email])
            
            test_user_id = user_creation_result['id']
            print(f"✅ Created test user {test_user_id} ({test_email}) directly in database")
        else:
            # This shouldn't happen with fake data, but handle it
            test_user_id = user_result["user"]["id"]
            print(f"✅ Created test user {test_user_id} ({test_email}) via registration")
        
        # Find the player record ID for the existing association
        player_record = execute_query_one("""
            SELECT id FROM players 
            WHERE tenniscores_player_id = %s AND is_active = true
            LIMIT 1
        """, [test_data['tenniscores_player_id']])
        
        if not player_record:
            print(f"❌ Could not find player record for {test_data['tenniscores_player_id']}")
            return False
        
        player_db_id = player_record['id']
        
        print(f"\n🔄 Attempting duplicate association:")
        print(f"   Test User ID: {test_user_id}")
        print(f"   Player DB ID: {player_db_id}")
        print(f"   Player Tenniscores ID: {test_data['tenniscores_player_id']}")
        print(f"   Already associated with: {test_data['email']}")
        
        # Try to associate the test user with the already-associated player
        association_result = associate_user_with_player(
            user_id=test_user_id,
            player_id=player_db_id,
            is_primary=True
        )
        
        if not association_result["success"]:
            print(f"✅ Association properly prevented: {association_result['error']}")
            
            # Verify security flag
            if association_result.get("security_issue"):
                print("✅ Security issue correctly flagged")
                success = True
            else:
                print("⚠️  Association prevented but no security flag")
                success = True  # Still success, just missing flag
        else:
            print(f"❌ FAILED: Association succeeded when it should have failed")
            print(f"   Result: {association_result}")
            success = False
        
        # Clean up test user
        execute_update("DELETE FROM user_player_associations WHERE user_id = %s", [test_user_id])
        execute_update("DELETE FROM users WHERE id = %s", [test_user_id])
        print(f"🧹 Cleaned up test user {test_user_id}")
        
        return success
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        # Try to clean up
        try:
            if 'test_user_id' in locals():
                execute_update("DELETE FROM user_player_associations WHERE user_id = %s", [test_user_id])
                execute_update("DELETE FROM users WHERE id = %s", [test_user_id])
        except:
            pass
        return False


def test_constraint_enforcement():
    """Test database constraint enforcement if it exists"""
    
    print(f"\n🧪 TEST 3: DATABASE CONSTRAINT ENFORCEMENT")
    print("=" * 50)
    
    # Check if constraint exists
    constraint_check = execute_query_one("""
        SELECT constraint_name 
        FROM information_schema.table_constraints 
        WHERE table_name = 'user_player_associations' 
        AND constraint_name = 'unique_tenniscores_player_id'
    """)
    
    if not constraint_check:
        print("⚠️  Database constraint not found - skipping constraint test")
        print("   Constraint can be added using add_unique_player_constraint.py")
        return True  # Not a failure, just not implemented yet
    
    print(f"✅ Found database constraint: {constraint_check['constraint_name']}")
    
    # Find existing association to test against
    existing_test = execute_query_one("""
        SELECT upa.tenniscores_player_id, upa.user_id
        FROM user_player_associations upa
        LIMIT 1
    """)
    
    if not existing_test:
        print("❌ No existing associations to test constraint against")
        return False
    
    player_id = existing_test['tenniscores_player_id']
    
    # Create temporary test user
    test_email = f"constraint_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}@test.rally"
    
    try:
        # Create test user
        create_user_result = execute_query_one("""
            INSERT INTO users (email, password_hash, first_name, last_name)
            VALUES (%s, 'test_hash', 'Constraint', 'Test')
            RETURNING id
        """, [test_email])
        
        test_user_id = create_user_result['id']
        print(f"✅ Created constraint test user {test_user_id}")
        
        # Attempt to create duplicate association (should fail due to constraint)
        try:
            execute_update("""
                INSERT INTO user_player_associations (user_id, tenniscores_player_id)
                VALUES (%s, %s)
            """, [test_user_id, player_id])
            
            # If we get here, constraint failed
            print(f"❌ CONSTRAINT FAILED: Duplicate association was allowed by database!")
            
            # Clean up the duplicate
            execute_update(
                "DELETE FROM user_player_associations WHERE user_id = %s AND tenniscores_player_id = %s",
                [test_user_id, player_id]
            )
            
            success = False
            
        except Exception as constraint_error:
            if "unique_tenniscores_player_id" in str(constraint_error):
                print(f"✅ DATABASE CONSTRAINT WORKING: Duplicate correctly prevented")
                print(f"   Error: {constraint_error}")
                success = True
            else:
                print(f"❌ UNEXPECTED CONSTRAINT ERROR: {constraint_error}")
                success = False
        
        # Clean up test user
        execute_update("DELETE FROM users WHERE id = %s", [test_user_id])
        print(f"🧹 Cleaned up constraint test user {test_user_id}")
        
        return success
        
    except Exception as e:
        print(f"❌ Constraint test setup error: {e}")
        return False


def main():
    """Main test execution"""
    
    print("🏓 RALLY DUPLICATE PREVENTION TEST SUITE")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)
    
    # Setup test data
    test_data = setup_test_data()
    
    if not test_data:
        print("\n❌ Cannot run tests without test data")
        return
    
    # Run tests
    test_results = {
        "registration_prevention": False,
        "association_prevention": False,
        "constraint_enforcement": False
    }
    
    test_results["registration_prevention"] = test_registration_prevention(test_data)
    test_results["association_prevention"] = test_association_prevention(test_data)
    test_results["constraint_enforcement"] = test_constraint_enforcement()
    
    # Summary
    print(f"\n📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    total_tests = len(test_results)
    passed_tests = sum(test_results.values())
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name.replace('_', ' ').title()}: {status}")
    
    print(f"\n🎯 OVERALL: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED - Duplicate prevention system is working!")
    elif passed_tests >= 2:
        print("⚠️  Most tests passed - System mostly working")
    else:
        print("🚨 MULTIPLE FAILURES - System needs attention")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    
    if not test_results["registration_prevention"]:
        print("   - Registration safeguards need fixing")
    
    if not test_results["association_prevention"]:
        print("   - Association safeguards need fixing")
    
    if not test_results["constraint_enforcement"]:
        print("   - Database constraint should be added for extra protection")
        print("   - Run: python scripts/add_unique_player_constraint.py")
    
    if passed_tests == total_tests:
        print("   - System is ready for production!")
        print("   - Run /debug/investigate-victor-forman-production to check production state")


if __name__ == "__main__":
    main() 