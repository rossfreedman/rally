#!/usr/bin/env python3
"""
Test script to verify SMS notifications show first and last name instead of email username
"""

import sys
import os
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logging import log_user_activity, _format_activity_for_sms

def test_sms_name_display():
    """Test that SMS notifications show first and last name instead of email username"""
    print("🧪 Testing SMS name display...")
    
    # Test 1: With first and last name
    print("\n📱 Test 1: With first and last name")
    sms_message = _format_activity_for_sms(
        user_email="testuser@example.com",
        activity_type="page_visit",
        page="availability",
        action=None,
        details=None,
        is_impersonating=False,
        first_name="Nathan",
        last_name="Cizek"
    )
    print(f"SMS Message:\n{sms_message}")
    
    # Test 2: With only first name
    print("\n📱 Test 2: With only first name")
    sms_message = _format_activity_for_sms(
        user_email="testuser@example.com",
        activity_type="page_visit",
        page="availability",
        action=None,
        details=None,
        is_impersonating=False,
        first_name="Nathan",
        last_name=None
    )
    print(f"SMS Message:\n{sms_message}")
    
    # Test 3: With only last name
    print("\n📱 Test 3: With only last name")
    sms_message = _format_activity_for_sms(
        user_email="testuser@example.com",
        activity_type="page_visit",
        page="availability",
        action=None,
        details=None,
        is_impersonating=False,
        first_name=None,
        last_name="Cizek"
    )
    print(f"SMS Message:\n{sms_message}")
    
    # Test 4: With no names (fallback to email)
    print("\n📱 Test 4: With no names (fallback to email)")
    sms_message = _format_activity_for_sms(
        user_email="testuser@example.com",
        activity_type="page_visit",
        page="availability",
        action=None,
        details=None,
        is_impersonating=False,
        first_name=None,
        last_name=None
    )
    print(f"SMS Message:\n{sms_message}")
    
    # Test 5: Registration success with names
    print("\n📱 Test 5: Registration success with names")
    sms_message = _format_activity_for_sms(
        user_email="brian@example.com",
        activity_type="registration_successful",
        page=None,
        action="player_id_linking_successful",
        details={
            "player_id": "nndz-test123456789",
            "player_data": {
                "first_name": "Bryan",
                "last_name": "Benavides",
                "club_name": "Tennaqua",
                "series_name": "Chicago 9",
                "league_id": "APTA_CHICAGO"
            },
            "team_assigned": True
        },
        is_impersonating=False,
        first_name="Brian",
        last_name="Benavides"
    )
    print(f"SMS Message:\n{sms_message}")
    
    print("\n✅ SMS name display tests completed!")

if __name__ == "__main__":
    test_sms_name_display() 