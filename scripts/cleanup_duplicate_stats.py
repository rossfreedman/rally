#!/usr/bin/env python3

"""
Cleanup script to remove duplicate series stats records.
Keeps the first record (lowest ID) and removes duplicates.
"""

import os
import sys
sys.path.append('.')

from app.models.database_models import Base, SeriesStats, SessionLocal
from sqlalchemy import text

def cleanup_duplicate_stats():
    """Remove duplicate series stats records, keeping the first one (lowest ID)"""
    
    session = SessionLocal()
    
    try:
        print("🧹 Cleaning up duplicate CNSWPL stats records...")
        print()
        
        # Find duplicate records
        duplicates_query = text('''
        SELECT team_id, series, COUNT(*) as count
        FROM series_stats 
        WHERE league_id = (SELECT id FROM leagues WHERE league_id = 'CNSWPL')
        GROUP BY team_id, series
        HAVING COUNT(*) > 1
        ORDER BY team_id, series
        ''')
        
        result = session.execute(duplicates_query)
        duplicates = result.fetchall()
        
        if not duplicates:
            print("✅ No duplicate records found!")
            return
        
        print(f"Found {len(duplicates)} team-series combinations with duplicates:")
        print()
        
        total_removed = 0
        
        for team_id, series, count in duplicates:
            print(f"Team ID {team_id}, Series '{series}': {count} records")
            
            # Get all duplicate records, ordered by ID (keep the first one)
            duplicate_records = session.query(SeriesStats).filter(
                SeriesStats.team_id == team_id,
                SeriesStats.series == series
            ).order_by(SeriesStats.id).all()
            
            # Keep the first record, remove the rest
            to_keep = duplicate_records[0]
            to_remove = duplicate_records[1:]
            
            print(f"  ✅ Keeping: ID={to_keep.id}, Points={to_keep.points}")
            
            for record in to_remove:
                print(f"  🗑️  Removing: ID={record.id}, Points={record.points}")
                session.delete(record)
                total_removed += 1
            
            print()
        
        # Commit the changes
        session.commit()
        
        print(f"🎉 Cleanup complete! Removed {total_removed} duplicate records.")
        
        # Verify no duplicates remain
        result = session.execute(duplicates_query)
        remaining_duplicates = result.fetchall()
        
        if remaining_duplicates:
            print(f"⚠️  Warning: {len(remaining_duplicates)} duplicates still remain!")
        else:
            print("✅ Verification: No duplicate records remaining!")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    cleanup_duplicate_stats()
