#!/usr/bin/env python3
"""
Test script for password change flow
"""

from app.services.password_reset_service import send_password_via_sms
from app.services.auth_service_refactored import authenticate_user
from database_utils import execute_query_one

def test_password_change_flow():
    """Test the complete password change flow"""
    
    print("Testing password change flow...")
    
    # Test 1: Send password reset to get temporary password
    print("\n1. Testing password reset to get temporary password...")
    result1 = send_password_via_sms("7732138911", "rossfreedman@gmail.com")
    print(f"   Result: {result1}")
    
    if result1["success"]:
        print("   ✅ Password reset successful - temporary password sent")
        
        # Test 2: Try to authenticate with temporary password
        print("\n2. Testing authentication with temporary password...")
        print("   Note: You'll need to check the SMS for the actual temporary password")
        print("   For this test, we'll assume the temporary password was received")
        
        # Test 3: Check if user has temporary password flag
        print("\n3. Checking temporary password flag in database...")
        user_check = execute_query_one(
            "SELECT has_temporary_password, temporary_password_set_at FROM users WHERE email = %s",
            ["rossfreedman@gmail.com"]
        )
        
        if user_check:
            has_temp = user_check["has_temporary_password"]
            temp_set_at = user_check["temporary_password_set_at"]
            print(f"   User has temporary password: {has_temp}")
            print(f"   Temporary password set at: {temp_set_at}")
            
            if has_temp:
                print("   ✅ Temporary password flag is set correctly")
            else:
                print("   ❌ Temporary password flag is not set")
        else:
            print("   ❌ User not found")
        
        # Test 4: Test the change password API endpoint (simulation)
        print("\n4. Testing change password API endpoint...")
        print("   This would normally be tested via the web interface")
        print("   The endpoint should:")
        print("   - Accept new password and confirmation")
        print("   - Validate password requirements")
        print("   - Update password in database")
        print("   - Clear temporary password flag")
        print("   - Redirect to /welcome")
        
    else:
        print("   ❌ Password reset failed")
        print(f"   Error: {result1.get('error', 'Unknown error')}")

def test_database_schema():
    """Test that the database schema has the required columns"""
    
    print("\nTesting database schema...")
    
    # Check if temporary password columns exist
    schema_check = execute_query_one("""
        SELECT column_name, data_type, is_nullable 
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name IN ('has_temporary_password', 'temporary_password_set_at')
        ORDER BY column_name
    """)
    
    if schema_check:
        print("   ✅ Temporary password columns found:")
        print(f"   - {schema_check['column_name']}: {schema_check['data_type']} (nullable: {schema_check['is_nullable']})")
    else:
        print("   ❌ Temporary password columns not found")
        
        # Check what columns do exist
        all_columns = execute_query_one("""
            SELECT string_agg(column_name, ', ') as columns
            FROM information_schema.columns 
            WHERE table_name = 'users'
        """)
        
        if all_columns:
            print(f"   Available columns: {all_columns['columns']}")

if __name__ == "__main__":
    test_database_schema()
    test_password_change_flow() 