#!/usr/bin/env python3
"""
Import Missing Schedule Data to Railway Production
================================================

Targeted script to import only the missing tables (match_scores, series_stats, schedule)
to Railway production database. This avoids the 5+ hour full ETL import.
"""

import sys
import os
import logging
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data.etl.database_import.OLD.import_all_jsons_to_database import ComprehensiveETL
from core.database import get_db

def main():
    print("🎯 Targeted Import: Missing Schedule Data to Railway")
    print(f"📅 {datetime.now()}")
    print("=" * 60)
    
    # Verify we're connecting to Railway
    db_url = os.getenv('DATABASE_URL', '')
    if 'railway' not in db_url.lower():
        print("❌ ERROR: Not connected to Railway database!")
        print(f"Current DATABASE_URL: {db_url[:50]}...")
        print("Please set DATABASE_URL to Railway production database")
        return 1
    
    print("✅ Connected to Railway production database")
    
    try:
        # Initialize ETL processor
        etl = ComprehensiveETL()
        
        # Load the JSON data files
        print("\n📂 Loading JSON data files...")
        match_history_data = etl.load_json_file("leagues/all/match_history.json")
        series_stats_data = etl.load_json_file("leagues/all/series_stats.json") 
        schedules_data = etl.load_json_file("leagues/all/schedules.json")
        
        print(f"   📊 Match history records: {len(match_history_data):,}")
        print(f"   📊 Series stats records: {len(series_stats_data):,}")
        print(f"   📊 Schedule records: {len(schedules_data):,}")
        
        # Connect to database
        with get_db() as conn:
            # Check current state
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM match_scores")
            current_matches = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM series_stats") 
            current_series = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM schedule")
            current_schedules = cursor.fetchone()[0]
            
            print(f"\n📊 Current database state:")
            print(f"   Match scores: {current_matches}")
            print(f"   Series stats: {current_series}")
            print(f"   Schedules: {current_schedules}")
            
            if current_matches > 0 or current_series > 0 or current_schedules > 0:
                response = input("\n⚠️  Target tables contain data. Continue? (y/n): ")
                if response.lower() != 'y':
                    print("Import cancelled")
                    return 0
            
            print("\n🚀 Starting targeted import...")
            
            # Import missing data in order
            print("\n1️⃣ Importing match history...")
            etl.import_match_history(conn, match_history_data)
            
            print("\n2️⃣ Importing series stats...")
            etl.import_series_stats(conn, series_stats_data)
            
            print("\n3️⃣ Importing schedules...")
            etl.import_schedules(conn, schedules_data)
            
            # Final verification
            cursor.execute("SELECT COUNT(*) FROM match_scores")
            final_matches = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM series_stats")
            final_series = cursor.fetchone()[0] 
            cursor.execute("SELECT COUNT(*) FROM schedule")
            final_schedules = cursor.fetchone()[0]
            
            print(f"\n✅ Import complete!")
            print(f"📊 Final database state:")
            print(f"   Match scores: {final_matches} (+{final_matches - current_matches})")
            print(f"   Series stats: {final_series} (+{final_series - current_series})")
            print(f"   Schedules: {final_schedules} (+{final_schedules - current_schedules})")
            
            # Check for Glenbrook RC Series 8 specifically
            cursor.execute("""
                SELECT COUNT(*) 
                FROM schedule s
                WHERE s.home_team LIKE '%Glenbrook%' OR s.away_team LIKE '%Glenbrook%'
            """)
            glenbrook_schedules = cursor.fetchone()[0]
            print(f"🎯 Glenbrook RC schedule records: {glenbrook_schedules}")
            
            cursor.close()
        
        print("\n🎉 SUCCESS: Schedule data imported to Railway production!")
        return 0
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 