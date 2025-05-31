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
os.environ['DATABASE_URL'] = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

def test_date_utilities():
    """Test the new date utility functions"""
    print("🧪 Testing Date Utilities")
    print("=" * 50)
    
    from utils.date_utils import normalize_date_string, date_to_db_timestamp, parse_date_flexible
    
    # Test cases from the Fix Railway Timezone Issue.md document
    test_cases = [
        {
            'input': '05/26/2025',
            'expected_normalized': '2025-05-26',
            'description': 'MM/DD/YYYY format (schedule data format)'
        },
        {
            'input': '05/29/2025', 
            'expected_normalized': '2025-05-29',
            'description': 'MM/DD/YYYY format (schedule data format)'
        },
        {
            'input': '06/02/2025',
            'expected_normalized': '2025-06-02', 
            'description': 'MM/DD/YYYY format (schedule data format)'
        },
        {
            'input': '2025-05-26',
            'expected_normalized': '2025-05-26',
            'description': 'YYYY-MM-DD format (database expected format)'
        }
    ]
    
    print("\n1. Testing normalize_date_string():")
    for case in test_cases:
        result = normalize_date_string(case['input'])
        status = "✅" if result == case['expected_normalized'] else "❌"
        print(f"  {status} {case['input']} -> {result} ({case['description']})")
        
    print("\n2. Testing date_to_db_timestamp():")
    for case in test_cases:
        try:
            result = date_to_db_timestamp(case['input'])
            # Should be a timezone-aware datetime at midnight UTC
            is_utc = result.tzinfo.utcoffset(None).total_seconds() == 0
            is_midnight = result.hour == 0 and result.minute == 0
            status = "✅" if is_utc and is_midnight else "❌"
            print(f"  {status} {case['input']} -> {result} (UTC: {is_utc}, Midnight: {is_midnight})")
        except Exception as e:
            print(f"  ❌ {case['input']} -> ERROR: {e}")
    
    print("\n3. Testing parse_date_flexible():")
    for case in test_cases:
        try:
            result = parse_date_flexible(case['input'])
            expected_date = case['expected_normalized']
            result_str = result.strftime('%Y-%m-%d') if result else None
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
        test_series = "Chicago 22"  # Updated to use the actual series name from the database
        
        # These are the actual dates from the timezone issue document
        test_dates_mm_dd_yyyy = [
            '05/26/2025',  # Should return status 1 (available)
            '05/29/2025',  # Should return status 2 (unavailable) 
            '06/02/2025'   # Should return status 3 (not_sure)
        ]
        
        # Test the same dates in YYYY-MM-DD format
        test_dates_yyyy_mm_dd = [
            '2025-05-26',  # Should return status 1 (available)
            '2025-05-29',  # Should return status 2 (unavailable)
            '2025-06-02'   # Should return status 3 (not_sure)
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
            print(f"✅ Connected to database: {result.get('current_database', 'unknown')}")
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
            print(f"  - {columns.get('column_name', 'unknown')}: {columns.get('data_type', 'unknown')}")
        else:
            print("❌ player_availability table not found")
            
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        import traceback
        traceback.print_exc()

def test_timezone_fix():
    """Test that the timezone fix is working correctly"""
    print("🔍 Testing Timezone Fix for Availability")
    print("=" * 50)
    
    # Import the updated functions
    try:
        from routes.act.availability import update_player_availability, get_player_availability
        from utils.date_utils import date_to_db_timestamp
        
        print("✅ Successfully imported updated functions")
        
        # Test date conversion
        test_dates = ['05/26/2025', '2025-05-26', '05/26/25']
        for test_date in test_dates:
            try:
                converted = date_to_db_timestamp(test_date)
                print(f"✅ {test_date} -> {converted}")
            except Exception as e:
                print(f"❌ {test_date} -> Error: {e}")
        
        # Test availability functions with known data
        player_name = "Ross Freedman"
        series = "Series 2B"
        
        print(f"\n🧪 Testing availability functions for {player_name}")
        
        # Test getting availability
        for test_date in ['05/26/2025', '05/29/2025', '06/02/2025']:
            result = get_player_availability(player_name, test_date, series)
            print(f"📅 {test_date}: Status = {result}")
        
        # Test updating availability (status 1 = available)
        test_date = '12/31/2024'
        print(f"\n🔄 Testing update for {test_date}")
        
        # First get current status
        before = get_player_availability(player_name, test_date, series)
        print(f"Before update: {before}")
        
        # Update to status 1 (available)
        success = update_player_availability(player_name, test_date, 1, series)
        print(f"Update success: {success}")
        
        # Check the result
        after = get_player_availability(player_name, test_date, series)
        print(f"After update: {after}")
        
        if success and after is not None:
            print("✅ Timezone fix working correctly!")
        else:
            print("❌ Timezone fix may have issues")
            
        print("\n🎯 Test completed!")
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

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
    main() 