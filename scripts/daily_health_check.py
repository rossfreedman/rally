#!/usr/bin/env python3
"""
Daily health check for multiple active records
Run this daily to catch issues early
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.monitor_multiple_active_records import find_users_with_multiple_records, check_user_context_mismatches

def daily_health_check():
    print("🏥 DAILY HEALTH CHECK - Multiple Active Records")
    print("=" * 60)
    print(f"Check Time: {datetime.now()}")
    print()
    
    # Check for multiple records
    multiple_records = find_users_with_multiple_records()
    
    # Check for context mismatches  
    context_mismatches = check_user_context_mismatches()
    
    if multiple_records or context_mismatches:
        print("🚨 ISSUES DETECTED!")
        print("Manual intervention required.")
        return False
    else:
        print("✅ ALL CHECKS PASSED!")
        print("No multiple active record issues detected.")
        return True

if __name__ == "__main__":
    daily_health_check()
