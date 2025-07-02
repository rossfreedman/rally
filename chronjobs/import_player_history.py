#!/usr/bin/env python3
"""
Railway Background Job: Import Player History Data
Runs directly on Railway server for optimal performance
"""

import json
import os
import sys
import time
from datetime import datetime

# Add project root to Python path for Railway
sys.path.append('/opt/render/project/src')

from data.etl.database_import.import_all_jsons_to_database import ComprehensiveETL
from database_utils import execute_query_one

def main():
    print(f"🚂 Railway Player History Import Job Started at {datetime.now()}")
    print("=" * 60)
    
    # Initialize ETL instance
    etl = ComprehensiveETL()
    
    try:
        print("\n1. Loading player history data from server filesystem...")
        start_time = time.time()
        
        # Load data directly from server filesystem
        player_history_data = etl.load_json_file('player_history.json')
        
        load_time = time.time() - start_time
        print(f"   ✅ Loaded {len(player_history_data):,} records in {load_time:.1f} seconds")
        
        print("\n2. Connecting to Railway database...")
        with etl.get_railway_optimized_db_connection() as conn:
            print("   ✅ Connected to production database")
            
            # Check current state
            current_count = execute_query_one('SELECT COUNT(*) as count FROM player_history')
            print(f"   Current player_history records: {current_count['count']:,}")
            
            # Import player history
            print("\n3. Importing player history data...")
            import_start = time.time()
            
            etl.import_player_history(conn, player_history_data)
            
            import_time = time.time() - import_start
            
            # Verify import
            print("\n4. Verifying import...")
            total_history = execute_query_one('SELECT COUNT(*) as count FROM player_history')
            imported_count = total_history['count'] - current_count['count']
            
            print(f"   ✅ Import completed in {import_time:.1f} seconds")
            print(f"   📊 Total records: {total_history['count']:,}")
            print(f"   📈 New records imported: {imported_count:,}")
            
            # Check for specific player (Ross Freedman)
            ross_history = execute_query_one('''
                SELECT COUNT(*) as count FROM player_history 
                WHERE player_id = %s
            ''', ('nndz-WkMrK3didjlnUT09',))
            
            print(f"   🎯 Ross Freedman history records: {ross_history['count']:,}")
            
            if ross_history['count'] > 0:
                # Show latest season data
                latest_season = execute_query_one('''
                    SELECT season, wins, losses, matches_played, pti_rating 
                    FROM player_history 
                    WHERE player_id = %s 
                    ORDER BY season DESC 
                    LIMIT 1
                ''', ('nndz-WkMrK3didjlnUT09',))
                
                if latest_season:
                    print(f"   📅 Latest season: {latest_season['season']}")
                    print(f"   🏆 Record: {latest_season['wins']}-{latest_season['losses']} ({latest_season['matches_played']} matches)")
                    if latest_season['pti_rating']:
                        print(f"   📊 PTI Rating: {latest_season['pti_rating']}")
            
            total_time = time.time() - start_time
            print(f"\n🎉 Complete import finished in {total_time:.1f} seconds")
            print("🚀 Player history data is now available for Previous Season History pages!")
            
    except Exception as e:
        print(f"❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print(f"\n🏁 Railway Player History Import Job Completed at {datetime.now()}")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 