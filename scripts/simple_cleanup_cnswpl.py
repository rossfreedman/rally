#!/usr/bin/env python3
"""
Simple CNSWPL Duplicate Data Cleanup Script
"""

import sys
import os
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database_config import get_db

def main():
    print("🧹 CNSWPL Duplicate Data Cleanup")
    print("=" * 50)
    
    with get_db() as db:
        cursor = db.cursor()
        
        # Use league ID directly (we know it's 4785)
        league_id = 4785
        print(f"📊 CNSWPL League ID: {league_id}")
        
        # Check current bad data
        print("\n🔍 Checking current bad data...")
        
        # Series 16 should not have Series 12 teams
        cursor.execute("""
            SELECT COUNT(*) FROM series_stats 
            WHERE league_id = %s AND series = 'Series 16' 
            AND team LIKE '%12'
        """, (league_id,))
        result = cursor.fetchone()
        series16_bad_count = result[0] if result else 0
        
        # Series 17 should not have Series 13 teams  
        cursor.execute("""
            SELECT COUNT(*) FROM series_stats 
            WHERE league_id = %s AND series = 'Series 17' 
            AND team LIKE '%13'
        """, (league_id,))
        result = cursor.fetchone()
        series17_bad_count = result[0] if result else 0
        
        print(f"📊 Series 16 bad records (Series 12 teams): {series16_bad_count}")
        print(f"📊 Series 17 bad records (Series 13 teams): {series17_bad_count}")
        
        if series16_bad_count == 0 and series17_bad_count == 0:
            print("✅ No bad data found - cleanup not needed!")
            return True
            
        # Delete bad Series 16 data (Series 12 teams)
        if series16_bad_count > 0:
            print(f"\n🗑️ Deleting {series16_bad_count} bad Series 16 records...")
            cursor.execute("""
                DELETE FROM series_stats 
                WHERE league_id = %s AND series = 'Series 16' 
                AND team LIKE '%12'
            """, (league_id,))
            deleted_16 = cursor.rowcount
            print(f"✅ Deleted {deleted_16} Series 16 bad records")
        
        # Delete bad Series 17 data (Series 13 teams)
        if series17_bad_count > 0:
            print(f"\n🗑️ Deleting {series17_bad_count} bad Series 17 records...")
            cursor.execute("""
                DELETE FROM series_stats 
                WHERE league_id = %s AND series = 'Series 17' 
                AND team LIKE '%13'
            """, (league_id,))
            deleted_17 = cursor.rowcount
            print(f"✅ Deleted {deleted_17} Series 17 bad records")
        
        # Commit changes
        db.commit()
        
        print("✅ Cleanup completed successfully!")
        print("💡 Next CNSWPL scraper run will import correct data for Series 16 and 17")
        return True

if __name__ == "__main__":
    main()
