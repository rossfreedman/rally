#!/usr/bin/env python3
"""
Cleanup CNSWPL Duplicate Data Script

This script removes the bad data that was imported due to the duplicate URL issue
in the CNSWPL stats scraper. Series 16 and 17 were using the same URLs as Series 12 and 13,
causing wrong data to be imported.

Issues to fix:
- Series 16 contains Series 12 teams (should be Series 16 teams)
- Series 17 contains Series 13 teams (should be Series 17 teams)
- Remove duplicate records and let the next scraper run import correct data
"""

import sys
import os
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database_config import get_db

def cleanup_cnswpl_duplicate_data():
    """Remove bad data from Series 16 and 17 that was caused by duplicate URLs."""
    
    print("🧹 CNSWPL Duplicate Data Cleanup")
    print("=" * 50)
    print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    with get_db() as db:
        cursor = db.cursor()
        
        # Get CNSWPL league ID
        cursor.execute("SELECT id FROM leagues WHERE league_name = %s", ("Chicago North Shore Women's Platform Tennis League",))
        league_result = cursor.fetchone()
        if not league_result:
            print("❌ CNSWPL league not found!")
            return False
            
        league_id = league_result[0]
        print(f"📊 CNSWPL League ID: {league_id}")
        
        # Check current bad data
        print("\n🔍 Checking current bad data...")
        
        # Series 16 should not have Series 12 teams
        cursor.execute("""
            SELECT COUNT(*) FROM series_stats 
            WHERE league_id = %s AND series = 'Series 16' 
            AND team LIKE '%12'
        """, (league_id,))
        series16_bad_count = cursor.fetchone()[0]
        
        # Series 17 should not have Series 13 teams  
        cursor.execute("""
            SELECT COUNT(*) FROM series_stats 
            WHERE league_id = %s AND series = 'Series 17' 
            AND team LIKE '%13'
        """, (league_id,))
        series17_bad_count = cursor.fetchone()[0]
        
        print(f"📊 Series 16 bad records (Series 12 teams): {series16_bad_count}")
        print(f"📊 Series 17 bad records (Series 13 teams): {series17_bad_count}")
        
        if series16_bad_count == 0 and series17_bad_count == 0:
            print("✅ No bad data found - cleanup not needed!")
            return True
            
        # Show what will be deleted
        print(f"\n🗑️ Will delete {series16_bad_count + series17_bad_count} bad records")
        
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
        
        # Verify cleanup
        print(f"\n🔍 Verifying cleanup...")
        
        cursor.execute("""
            SELECT COUNT(*) FROM series_stats 
            WHERE league_id = %s AND series = 'Series 16' 
            AND team LIKE '%12'
        """, (league_id,))
        remaining_16 = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM series_stats 
            WHERE league_id = %s AND series = 'Series 17' 
            AND team LIKE '%13'
        """, (league_id,))
        remaining_17 = cursor.fetchone()[0]
        
        print(f"📊 Remaining Series 16 bad records: {remaining_16}")
        print(f"📊 Remaining Series 17 bad records: {remaining_17}")
        
        if remaining_16 == 0 and remaining_17 == 0:
            print("✅ Cleanup completed successfully!")
            print("💡 Next CNSWPL scraper run will import correct data for Series 16 and 17")
            return True
        else:
            print("❌ Cleanup incomplete - some bad data remains")
            return False

def main():
    """Main cleanup function."""
    try:
        success = cleanup_cnswpl_duplicate_data()
        
        print(f"\n{'='*50}")
        if success:
            print("🎉 CNSWPL duplicate data cleanup completed successfully!")
            print("💡 The next CNSWPL scraper run will import correct data")
        else:
            print("❌ CNSWPL duplicate data cleanup failed!")
            
        print(f"🕐 Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()
