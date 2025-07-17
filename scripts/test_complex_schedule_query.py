#!/usr/bin/env python3
"""
Test the exact complex query from the schedule notification function
"""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query

def test_complex_query():
    """Test the exact query from the schedule notification function"""
    
    print("🔍 Testing Complex Schedule Query")
    print("=" * 50)
    
    team_id = 57314
    current_date = datetime.now().date()
    
    print(f"Team ID: {team_id}")
    print(f"Current date: {current_date}")
    
    # The exact query from the function
    schedule_query = """
        SELECT 
            s.id,
            s.match_date,
            s.match_time,
            s.home_team_id,
            s.away_team_id,
            s.home_team,
            s.away_team,
            s.location,
            c.club_address,
            CASE 
                WHEN s.home_team_id = %s THEN 'practice'
                ELSE 'match'
            END as type
        FROM schedule s
        LEFT JOIN teams t ON (s.home_team_id = t.id OR s.away_team_id = t.id)
        LEFT JOIN clubs c ON t.club_id = c.id
        WHERE (s.home_team_id = %s OR s.away_team_id = %s)
        AND s.match_date >= %s
        ORDER BY s.match_date ASC, s.match_time ASC
        LIMIT 10
    """
    
    try:
        result = execute_query(schedule_query, [team_id, team_id, team_id, current_date])
        print(f"✅ Query successful: {len(result)} results")
        
        if result:
            print(f"   Sample entries:")
            for i, entry in enumerate(result[:3]):
                print(f"     Entry {i+1}: {entry['match_date']} {entry['match_time']} - {entry['home_team']} vs {entry['away_team']} ({entry['club_address']}) - {entry['type']}")
        else:
            print("❌ No results returned")
            
    except Exception as e:
        print(f"❌ Query failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_complex_query() 