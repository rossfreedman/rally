#!/usr/bin/env python3
"""
Test script to create missing teams from schedule data
"""

import sys
import os
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data.etl.database_import.import_all_jsons_to_database import ComprehensiveETL
from database_config import get_db

def test_missing_teams_creation():
    """Test the missing teams creation function"""
    print("🔧 Testing Missing Teams Creation")
    print(f"📅 {datetime.now()}")
    print("=" * 60)
    
    try:
        # Create ETL instance
        etl = ComprehensiveETL()
        
        # Get database connection
        with get_db() as conn:
            # Run the missing teams creation
            missing_teams = etl.create_missing_teams_from_schedule(conn)
            
            print(f"\n✅ Test complete!")
            print(f"📊 Created {missing_teams} missing teams from schedule data")
            
            # Check the results
            from database_utils import execute_query
            
            # Check schedule entries with NULL team_ids
            null_count_query = """
                SELECT COUNT(*) as null_count
                FROM schedule 
                WHERE (home_team_id IS NULL OR away_team_id IS NULL)
            """
            null_result = execute_query(null_count_query)
            remaining_null = null_result[0]["null_count"]
            
            print(f"📊 Remaining schedule entries with NULL team_ids: {remaining_null}")
            
            if remaining_null == 0:
                print("🎉 All schedule entries now have valid team mappings!")
            else:
                print(f"⚠️  {remaining_null} schedule entries still have NULL team_ids")
            
            return missing_teams
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0

if __name__ == "__main__":
    test_missing_teams_creation() 