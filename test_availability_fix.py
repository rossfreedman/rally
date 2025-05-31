#!/usr/bin/env python3
"""
Quick test to verify the availability update fix is working
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.date_utils import date_to_db_timestamp
from utils.date_verification import check_railway_date_correction
from datetime import date

def test_date_conversion():
    print("=== Testing Date Conversion ===")
    
    test_dates = [
        "2024-09-24",
        "09/24/2024", 
        "9/24/2024"
    ]
    
    for test_date in test_dates:
        try:
            result = date_to_db_timestamp(test_date)
            print(f"✅ {test_date} -> {result}")
        except Exception as e:
            print(f"❌ {test_date} -> ERROR: {e}")
    
def test_railway_correction():
    print("\n=== Testing Railway Correction ===")
    
    test_date = date(2024, 9, 24)
    
    try:
        corrected = check_railway_date_correction(test_date)
        print(f"✅ Railway correction: {test_date} -> {corrected}")
        
        if corrected == test_date:
            print("✅ No correction applied (correct behavior)")
        else:
            print("⚠️ Correction applied - check if this is expected")
            
    except Exception as e:
        print(f"❌ Railway correction error: {e}")

def test_environment_vars():
    print("\n=== Testing Environment Variables ===")
    
    tz_env = os.getenv('TZ')
    pgtz_env = os.getenv('PGTZ')
    railway_vars = ['RAILWAY_ENVIRONMENT', 'DATABASE_URL', 'POSTGRES_DB', 'PGDATABASE']
    
    print(f"TZ: {tz_env}")
    print(f"PGTZ: {pgtz_env}")
    
    for var in railway_vars:
        value = os.getenv(var)
        if value:
            print(f"{var}: {value[:50]}{'...' if len(str(value)) > 50 else ''}")

if __name__ == "__main__":
    test_date_conversion()
    test_railway_correction()
    test_environment_vars() 