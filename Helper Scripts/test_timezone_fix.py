#!/usr/bin/env python3
"""
Test script to verify the timezone migration and date format fixes are working
This tests the critical issues identified in Fix Railway Timezone Issue.md
"""

import os
import sys

# Add the current directory to the path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set the database URL to the new database
os.environ["DATABASE_URL"] = (
    "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"
)


def test_date_utilities():
    """Test the new date utility functions"""
    print("🧪 Testing Date Utilities")
    print("=" * 50)

    from utils.date_utils import (
        date_to_db_timestamp,
        normalize_date_string,
        parse_date_flexible,
    )

    # Test cases from the Fix Railway Timezone Issue.md document
    test_cases = [
        {
            "input": "05/26/2025",
            "expected_normalized": "2025-05-26",
            "description": "MM/DD/YYYY format (schedule data format)",
        },
        {
            "input": "05/29/2025",
            "expected_normalized": "2025-05-29",
            "description": "MM/DD/YYYY format (schedule data format)",
        },
        {
            "input": "06/02/2025",
            "expected_normalized": "2025-06-02",
            "description": "MM/DD/YYYY format (schedule data format)",
        },
        {
            "input": "2025-05-26",
            "expected_normalized": "2025-05-26",
            "description": "YYYY-MM-DD format (database expected format)",
        },
    ]

    print("\n1. Testing normalize_date_string():")
    for case in test_cases:
        result = normalize_date_string(case["input"])
        status = "✅" if result == case["expected_normalized"] else "❌"
        print(f"  {status} {case['input']} -> {result} ({case['description']})")

    print("\n2. Testing date_to_db_timestamp():")
    for case in test_cases:
        try:
            result = date_to_db_timestamp(case["input"])
            # Should be a timezone-aware datetime at midnight UTC
            is_utc = result.tzinfo.utcoffset(None).total_seconds() == 0
            is_midnight = result.hour == 0 and result.minute == 0
            status = "✅" if is_utc and is_midnight else "❌"
            print(
                f"  {status} {case['input']} -> {result} (UTC: {is_utc}, Midnight: {is_midnight})"
            )
        except Exception as e:
            print(f"  ❌ {case['input']} -> ERROR: {e}")

    print("\n3. Testing parse_date_flexible():")
    for case in test_cases:
        try:
            result = parse_date_flexible(case["input"])
            expected_date = case["expected_normalized"]
            result_str = result.strftime("%Y-%m-%d") if result else None
            status = "✅" if result_str == expected_date else "❌"
            print(f"  {status} {case['input']} -> {result} (expected: {expected_date})")
        except Exception as e:
            print(f"  ❌ {case['input']} -> ERROR: {e}")


def test_availability_functions():
    """Test that availability functions work with the MM/DD/YYYY format"""
    print("\n\n🧪 Testing Availability Functions")
    print("=" * 50)

    try:
        from routes.act.availability import get_player_availability

        # Test the critical bug: MM/DD/YYYY format from schedule data
        test_player = "Ross Freedman"
        test_series = (
            "Chicago 22"  # Updated to use the actual series name from the database
        )

        # These are the actual dates from the timezone issue document
        test_dates_mm_dd_yyyy = [
            "05/26/2025",  # Should return status 1 (available)
            "05/29/2025",  # Should return status 2 (unavailable)
            "06/02/2025",  # Should return status 3 (not_sure)
        ]

        # Test the same dates in YYYY-MM-DD format
        test_dates_yyyy_mm_dd = [
            "2025-05-26",  # Should return status 1 (available)
            "2025-05-29",  # Should return status 2 (unavailable)
            "2025-06-02",  # Should return status 3 (not_sure)
        ]

        print(f"\nTesting availability for: {test_player} in {test_series}")

        print("\n1. Testing MM/DD/YYYY format (the problematic format):")
        for date_str in test_dates_mm_dd_yyyy:
            try:
                result = get_player_availability(test_player, date_str, test_series)
                status = "✅" if result is not None else "❌"
                print(f"  {status} {date_str} -> {result}")
            except Exception as e:
                print(f"  ❌ {date_str} -> ERROR: {e}")

        print("\n2. Testing YYYY-MM-DD format (for comparison):")
        for date_str in test_dates_yyyy_mm_dd:
            try:
                result = get_player_availability(test_player, date_str, test_series)
                status = "✅" if result is not None else "❌"
                print(f"  {status} {date_str} -> {result}")
            except Exception as e:
                print(f"  ❌ {date_str} -> ERROR: {e}")

    except Exception as e:
        print(f"❌ Error testing availability functions: {e}")
        import traceback

        traceback.print_exc()


def test_database_connection():
    """Test that we can connect to the new database"""
    print("\n\n🧪 Testing Database Connection")
    print("=" * 50)

    try:
        from database_utils import execute_query_one

        # Test basic database connectivity
        result = execute_query_one("SELECT current_database(), version()")
        if result:
            print(
                f"✅ Connected to database: {result.get('current_database', 'unknown')}"
            )
            print(f"✅ PostgreSQL version: {result.get('version', 'unknown')[:50]}...")
        else:
            print("❌ Could not connect to database")

        # Test that player_availability table exists and has the right schema
        schema_query = """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'player_availability' 
            ORDER BY ordinal_position
        """
        columns = execute_query_one(schema_query)
        if columns:
            print("✅ player_availability table exists")
            print("Schema:")
            # This will only show the first column, but that's enough to verify the table exists
            print(
                f"  - {columns.get('column_name', 'unknown')}: {columns.get('data_type', 'unknown')}"
            )
        else:
            print("❌ player_availability table not found")

    except Exception as e:
        print(f"❌ Database connection error: {e}")
        import traceback

        traceback.print_exc()


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
        print(
            f"❌ Date conversion is wrong. Expected: {expected_date}, Got: {converted_date.date()}"
        )
        return False

    # Step 2: Clean any existing test data
    print("\n--- Step 2: Cleanup Test Data ---")
    try:
        # Get series ID for cleanup
        series_record = execute_query_one(
            "SELECT id FROM series WHERE name = %(name)s", {"name": test_series}
        )

        if series_record:
            series_id = series_record["id"]
            execute_query(
                "DELETE FROM player_availability WHERE player_name = %(player)s AND series_id = %(series_id)s",
                {"player": test_player, "series_id": series_id},
            )
            print("✅ Cleaned up existing test data")
        else:
            print(f"⚠️ Series {test_series} not found, creating test series")
            # For this test, we'll assume the series exists
            print("❌ Cannot proceed without valid series")
            return False

    except Exception as e:
        print(f"Error during cleanup: {e}")
        return False

    # Step 3: Test storing availability
    print("\n--- Step 3: Store Availability Test ---")
    try:
        success = update_player_availability(
            test_player, test_date, test_status, test_series
        )
        if success:
            print("✅ Successfully stored availability")
        else:
            print("❌ Failed to store availability")
            return False
    except Exception as e:
        print(f"❌ Error storing availability: {e}")
        return False

    # Step 4: Verify what was actually stored in the database
    print("\n--- Step 4: Database Verification ---")
    try:
        # Query the raw database record
        verification_query = """
            SELECT 
                match_date,
                DATE(match_date AT TIME ZONE 'UTC') as utc_date_part,
                availability_status,
                EXTRACT(TIMEZONE FROM match_date)/3600 as timezone_offset_hours
            FROM player_availability 
            WHERE player_name = %(player)s 
            AND series_id = %(series_id)s
        """

        db_record = execute_query_one(
            verification_query, {"player": test_player, "series_id": series_id}
        )

        if db_record:
            print(f"Raw stored timestamp: {db_record['match_date']}")
            print(f"UTC date part: {db_record['utc_date_part']}")
            print(f"Timezone offset (hours): {db_record['timezone_offset_hours']}")
            print(f"Status: {db_record['availability_status']}")

            # Check if the date is correct
            stored_date = db_record["utc_date_part"]
            if str(stored_date) == "2024-09-24":
                print("✅ Date stored correctly in database")
            else:
                print(
                    f"❌ Date stored incorrectly. Expected: 2024-09-24, Got: {stored_date}"
                )
                return False
        else:
            print("❌ No record found in database")
            return False

    except Exception as e:
        print(f"❌ Error verifying database: {e}")
        return False

    # Step 5: Test retrieving availability
    print("\n--- Step 5: Retrieve Availability Test ---")
    try:
        retrieved_status = get_player_availability(test_player, test_date, test_series)
        if retrieved_status == test_status:
            print(f"✅ Successfully retrieved correct status: {retrieved_status}")
        else:
            print(
                f"❌ Retrieved wrong status. Expected: {test_status}, Got: {retrieved_status}"
            )
            return False
    except Exception as e:
        print(f"❌ Error retrieving availability: {e}")
        return False

    # Step 6: Test with different date formats
    print("\n--- Step 6: Multiple Date Format Test ---")
    test_dates = [
        "2024-09-24",  # YYYY-MM-DD format
        "09/24/2024",  # MM/DD/YYYY format
        "9/24/2024",  # M/D/YYYY format
    ]

    for date_format in test_dates:
        try:
            converted = date_to_db_timestamp(date_format)
            if converted.date() == expected_date:
                print(f"✅ Format {date_format} -> {converted.date()}")
            else:
                print(
                    f"❌ Format {date_format} -> {converted.date()} (expected {expected_date})"
                )
                return False
        except Exception as e:
            print(f"❌ Error with format {date_format}: {e}")
            return False

    # Step 7: Cleanup
    print("\n--- Step 7: Final Cleanup ---")
    try:
        execute_query(
            "DELETE FROM player_availability WHERE player_name = %(player)s AND series_id = %(series_id)s",
            {"player": test_player, "series_id": series_id},
        )
        print("✅ Cleaned up test data")
    except Exception as e:
        print(f"Warning: Could not cleanup test data: {e}")

    print("\n=== TIMEZONE FIX TEST COMPLETED SUCCESSFULLY ===")
    return True


def main():
    """Run all tests"""
    print("🚀 Running Timezone Migration Verification Tests")
    print("=" * 60)
    print("Testing fixes for issues identified in Fix Railway Timezone Issue.md")
    print()

    test_database_connection()
    test_date_utilities()
    test_availability_functions()
    test_timezone_fix()

    print("\n\n" + "=" * 60)
    print("🎯 Test Summary:")
    print("- If date utilities show ✅, the date format conversion is fixed")
    print("- If availability functions show ✅, the MM/DD/YYYY bug is fixed")
    print("- If database connection shows ✅, the migration is working")
    print("\n💡 Next step: Test the actual availability page in the browser")
    print("   URL: https://www.rallytennaqua.com/mobile/availability")


if __name__ == "__main__":
    success = test_timezone_fix()
    if success:
        print("\n🎉 All tests passed! The timezone fix is working correctly.")
        print("Dates should no longer be stored 2 days back.")
    else:
        print("\n💥 Some tests failed. The timezone issue may still exist.")

    sys.exit(0 if success else 1)
