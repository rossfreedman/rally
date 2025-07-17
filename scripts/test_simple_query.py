#!/usr/bin/env python3
"""
Simple test of database query
"""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query

def test_simple_query():
    """Test a simple database query"""
    
    print("🔍 Testing Simple Database Query")
    print("=" * 40)
    
    team_id = 57314
    current_date = datetime.now().date()
    
    print(f"Team ID: {team_id}")
    print(f"Current date: {current_date}")
    
    # Simple query
    query = """
        SELECT COUNT(*) as count
        FROM schedule 
        WHERE (home_team_id = %s OR away_team_id = %s)
        AND match_date >= %s
    """
    
    try:
        result = execute_query(query, [team_id, team_id, current_date])
        print(f"✅ Query successful: {result}")
        
        if result:
            count = result[0]['count']
            print(f"✅ Found {count} upcoming schedule entries")
        else:
            print("❌ No results returned")
            
    except Exception as e:
        print(f"❌ Query failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_query() 