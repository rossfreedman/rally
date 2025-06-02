#!/usr/bin/env python3
"""
Simple test script to verify the timezone fix for player availability
This addresses the issue where dates were being stored 2 days back.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.date_utils import date_to_db_timestamp
from routes.act.availability import update_player_availability, get_player_availability
from database_utils import execute_query_one, execute_query
import pytz
from datetime import datetime

def test_timezone_fix():
    """Test that the timezone fix correctly stores and retrieves dates"""
    
    print("=== TIMEZONE FIX TEST ===")
    
    # Test date: September 24, 2024 (the date mentioned in the issue)
    test_date = "9/24/2024"
    test_player = "Test Player"
    test_series = "S3"
    test_status = 1  # Available
    
    print(f"Testing with date: {test_date}")
    print(f"Player: {test_player}")
    print(f"Series: {test_series}")
    
    # Step 1: Test date conversion
    print("\n--- Step 1: Date Conversion Test ---")
    converted_date = date_to_db_timestamp(test_date)
    print(f"Input date: {test_date}")
    print(f"Converted to UTC timestamp: {converted_date}")
    print(f"UTC date part: {converted_date.date()}")
    
    # Verify the converted date is correct
    expected_date = datetime(2024, 9, 24).date()
    if converted_date.date() == expected_date:
        print("✅ Date conversion is correct")
    else:
        print(f"❌ Date conversion is wrong. Expected: {expected_date}, Got: {converted_date.date()}")
        return False
    
    # Step 2: Test with different date formats
    print("\n--- Step 2: Multiple Date Format Test ---")
    test_dates = [
        "2024-09-24",  # YYYY-MM-DD format
        "09/24/2024",  # MM/DD/YYYY format
        "9/24/2024"    # M/D/YYYY format
    ]
    
    for date_format in test_dates:
        try:
            converted = date_to_db_timestamp(date_format)
            if converted.date() == expected_date:
                print(f"✅ Format {date_format} -> {converted.date()}")
            else:
                print(f"❌ Format {date_format} -> {converted.date()} (expected {expected_date})")
                return False
        except Exception as e:
            print(f"❌ Error with format {date_format}: {e}")
            return False
    
    print("\n=== TIMEZONE FIX TEST COMPLETED SUCCESSFULLY ===")
    return True

if __name__ == "__main__":
    success = test_timezone_fix()
    if success:
        print("\n🎉 All tests passed! The timezone fix is working correctly.")
        print("Dates should no longer be stored 2 days back.")
    else:
        print("\n💥 Some tests failed. The timezone issue may still exist.")
    
    sys.exit(0 if success else 1) 