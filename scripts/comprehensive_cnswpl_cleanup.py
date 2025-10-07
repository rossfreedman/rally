#!/usr/bin/env python3
"""
Comprehensive CNSWPL Data Cleanup Script

This script fixes all data quality issues found in the CNSWPL stats data:
1. Removes duplicate records
2. Fixes Series 17 showing Series 10 teams (wrong URL issue)
3. Ensures data integrity
"""

import sys
import os
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database_config import get_db

def cleanup_cnswpl_data():
    """Clean up all CNSWPL data quality issues."""
    
    print("🧹 CNSWPL Comprehensive Data Cleanup")
    print("=" * 60)
    print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    with get_db() as db:
        cursor = db.cursor()
        league_id = 4785
        
        print(f"📊 CNSWPL League ID: {league_id}")
        
        # 1. Remove duplicate records
        print(f"\n🗑️ Removing duplicate records...")
        cursor.execute("""
            DELETE FROM series_stats 
            WHERE id IN (
                SELECT id FROM (
                    SELECT id, ROW_NUMBER() OVER (
                        PARTITION BY team_id, series 
                        ORDER BY created_at DESC
                    ) as rn
                    FROM series_stats 
                    WHERE league_id = %s
                ) t WHERE rn > 1
            )
        """, (league_id,))
        duplicates_deleted = cursor.rowcount
        print(f"✅ Deleted {duplicates_deleted} duplicate records")
        
        # 2. Fix Series 17 wrong teams (Series 10 teams in Series 17)
        print(f"\n🔧 Fixing Series 17 wrong teams...")
        cursor.execute("""
            DELETE FROM series_stats 
            WHERE league_id = %s 
            AND series = 'Series 17'
            AND team_id IN (
                SELECT t.id FROM teams t
                WHERE t.league_id = %s
                AND t.team_name LIKE '%10%'
            )
        """, (league_id, league_id))
        series_17_fixed = cursor.rowcount
        print(f"✅ Deleted {series_17_fixed} wrong Series 17 records")
        
        # 3. Commit changes
        db.commit()
        
        # 4. Verify cleanup
        print(f"\n🔍 Verifying cleanup...")
        
        # Check duplicates
        cursor.execute("""
            SELECT COUNT(*) FROM (
                SELECT team_id, series, COUNT(*) as count
                FROM series_stats 
                WHERE league_id = %s
                GROUP BY team_id, series
                HAVING COUNT(*) > 1
            ) duplicates
        """, (league_id,))
        remaining_duplicates = cursor.fetchone()[0]
        
        # Check Series 17 wrong teams
        cursor.execute("""
            SELECT COUNT(*) FROM series_stats ss
            JOIN teams t ON ss.team_id = t.id
            WHERE ss.league_id = %s 
            AND ss.series = 'Series 17'
            AND t.team_name LIKE '%10%'
        """, (league_id,))
        remaining_wrong_17 = cursor.fetchone()[0]
        
        # Check Series 16
        cursor.execute("""
            SELECT COUNT(*) FROM series_stats 
            WHERE league_id = %s AND series = 'Series 16'
        """, (league_id,))
        series_16_count = cursor.fetchone()[0]
        
        # Check total records
        cursor.execute("""
            SELECT COUNT(*) FROM series_stats 
            WHERE league_id = %s
        """, (league_id,))
        total_records = cursor.fetchone()[0]
        
        print(f"📊 Remaining duplicates: {remaining_duplicates}")
        print(f"📊 Remaining Series 17 wrong teams: {remaining_wrong_17}")
        print(f"📊 Series 16 records: {series_16_count}")
        print(f"📊 Total records: {total_records}")
        
        if remaining_duplicates == 0 and remaining_wrong_17 == 0:
            print("✅ Cleanup completed successfully!")
            print("💡 Next CNSWPL scraper run will import correct data")
            return True
        else:
            print("❌ Cleanup incomplete - some issues remain")
            return False

def main():
    """Main cleanup function."""
    try:
        success = cleanup_cnswpl_data()
        
        print(f"\n{'='*60}")
        if success:
            print("🎉 CNSWPL comprehensive data cleanup completed successfully!")
            print("💡 The next CNSWPL scraper run will import correct data")
        else:
            print("❌ CNSWPL comprehensive data cleanup failed!")
            
        print(f"🕐 Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()
