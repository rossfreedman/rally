#!/usr/bin/env python3
"""
Test script for registration activity logging enhancements

This script tests the new activity logging features for registration success/failure
and player ID linking status.
"""

import sys
import os
import json
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logging import log_user_activity


def test_registration_success_logging():
    """Test logging for successful registration with player ID linking"""
    print("🧪 Testing successful registration logging...")
    
    # Simulate successful registration
    log_user_activity(
        "testuser@example.com",
        "registration_successful",
        action="player_id_linking_successful",
        details={
            "player_id": "nndz-test123456789",
            "player_data": {
                "first_name": "John",
                "last_name": "Doe",
                "club_name": "Tennaqua",
                "series_name": "Chicago 7",
                "league_id": "APTA_CHICAGO"
            },
            "team_assigned": True,
            "registration_data": {
                "first_name": "John",
                "last_name": "Doe",
                "league_id": "APTA_CHICAGO",
                "club_name": "Tennaqua",
                "series_name": "Chicago 7",
                "phone_number_provided": True
            }
        }
    )
    
    print("✅ Success registration logging test completed")


def test_registration_failure_logging():
    """Test logging for failed registration scenarios"""
    print("🧪 Testing failed registration logging...")
    
    # Test 1: Player ID linking failed
    log_user_activity(
        "testuser2@example.com",
        "registration_failed",
        action="player_id_linking_failed",
        details={
            "reason": "No player found with provided details",
            "lookup_attempt": {
                "first_name": "Jane",
                "last_name": "Smith",
                "league_id": "APTA_CHICAGO",
                "club_name": "Tennaqua",
                "series_name": "Chicago 7"
            },
            "player_lookup_result": None
        }
    )
    
    # Test 2: Security issue - player ID already claimed
    log_user_activity(
        "testuser3@example.com",
        "registration_failed",
        action="security_issue_player_id_claimed",
        details={
            "reason": "Player ID already associated with another account",
            "player_id": "nndz-alreadyclaimed123",
            "existing_user_email": "existinguser@example.com",
            "lookup_attempt": {
                "first_name": "Bob",
                "last_name": "Johnson",
                "league_id": "APTA_CHICAGO",
                "club_name": "Tennaqua",
                "series_name": "Chicago 7"
            }
        }
    )
    
    # Test 3: Missing required fields
    log_user_activity(
        "testuser4@example.com",
        "registration_failed",
        action="missing_required_fields",
        details={
            "reason": "Missing required league/club/series information",
            "provided_data": {
                "league_id": "",
                "club_name": "Tennaqua",
                "series_name": ""
            },
            "registration_data": {
                "first_name": "Alice",
                "last_name": "Brown"
            }
        }
    )
    
    # Test 4: Duplicate email
    log_user_activity(
        "testuser5@example.com",
        "registration_failed",
        action="duplicate_email",
        details={
            "reason": "User with this email already exists",
            "registration_data": {
                "first_name": "Charlie",
                "last_name": "Wilson",
                "league_id": "APTA_CHICAGO",
                "club_name": "Tennaqua",
                "series_name": "Chicago 7"
            }
        }
    )
    
    print("✅ Failed registration logging tests completed")


def test_sms_formatting():
    """Test SMS message formatting for registration activities"""
    print("🧪 Testing SMS formatting...")
    
    from utils.logging import _format_activity_for_sms
    
    # Test successful registration SMS
    success_sms = _format_activity_for_sms(
        "testuser@example.com",
        "registration_successful",
        None,
        "player_id_linking_successful",
        {
            "player_id": "nndz-test123456789",
            "player_data": {
                "first_name": "John",
                "last_name": "Doe",
                "club_name": "Tennaqua",
                "series_name": "Chicago 7"
            },
            "team_assigned": True
        },
        False
    )
    
    print("📱 Success Registration SMS:")
    print(success_sms)
    print()
    
    # Test failed registration SMS
    failure_sms = _format_activity_for_sms(
        "testuser2@example.com",
        "registration_failed",
        None,
        "player_id_linking_failed",
        {
            "reason": "No player found with provided details",
            "lookup_attempt": {
                "first_name": "Jane",
                "last_name": "Smith",
                "club_name": "Tennaqua",
                "series_name": "Chicago 7"
            }
        },
        False
    )
    
    print("📱 Failed Registration SMS:")
    print(failure_sms)
    print()
    
    # Test security issue SMS
    security_sms = _format_activity_for_sms(
        "testuser3@example.com",
        "registration_failed",
        None,
        "security_issue_player_id_claimed",
        {
            "player_id": "nndz-alreadyclaimed123",
            "existing_user_email": "existinguser@example.com"
        },
        False
    )
    
    print("📱 Security Issue SMS:")
    print(security_sms)
    print()
    
    print("✅ SMS formatting tests completed")


def main():
    """Run all tests"""
    print("🚀 Starting Registration Activity Logging Tests")
    print("=" * 50)
    
    try:
        test_registration_success_logging()
        print()
        
        test_registration_failure_logging()
        print()
        
        test_sms_formatting()
        print()
        
        print("🎉 All tests completed successfully!")
        print()
        print("📋 Summary:")
        print("- ✅ Success registration logging")
        print("- ✅ Failed registration logging (multiple scenarios)")
        print("- ✅ SMS message formatting")
        print()
        print("🔍 Check the database and SMS notifications to verify the logging worked correctly.")
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 