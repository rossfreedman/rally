#!/usr/bin/env python3
"""
Remove Lisa Wagner Duplicate Record
===================================

Remove the incorrect Lisa Wagner Division 12 record that's causing registration conflicts.
Keep the correct Series 12 record.
"""

import os
import sys
from pathlib import Path

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = Path(script_dir).parent
sys.path.insert(0, str(project_root))

from database_config import get_db

def remove_lisa_wagner_duplicate():
    """Remove the incorrect Lisa Wagner Division 12 record"""
    
    incorrect_player_id = 'nndz-WkM2eHhybi9qUT09'  # Division 12 - INCORRECT
    correct_player_id = 'cnswpl_2070e1ed22049df7'   # Series 12 - CORRECT
    
    print("🔍 Removing Lisa Wagner duplicate record...")
    print(f"❌ Removing INCORRECT: {incorrect_player_id} (Division 12)")
    print(f"✅ Keeping CORRECT: {correct_player_id} (Series 12)")
    print()
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # First, verify both records exist
            cursor.execute('''
                SELECT tenniscores_player_id, first_name, last_name, 
                       c.name as club_name, s.name as series_name
                FROM players p
                LEFT JOIN clubs c ON p.club_id = c.id
                LEFT JOIN series s ON p.series_id = s.id
                WHERE tenniscores_player_id IN (%s, %s)
                ORDER BY tenniscores_player_id
            ''', (incorrect_player_id, correct_player_id))
            
            records = cursor.fetchall()
            print("📋 Current Lisa Wagner records:")
            for record in records:
                print(f"  • {record['tenniscores_player_id']}: {record['first_name']} {record['last_name']} ({record['club_name']}, {record['series_name']})")
            print()
            
            if len(records) != 2:
                print(f"⚠️  Expected 2 records, found {len(records)}. Aborting for safety.")
                return False
            
            # Check if incorrect record exists
            cursor.execute('''
                SELECT tenniscores_player_id, first_name, last_name, club_id, series_id, team_id
                FROM players 
                WHERE tenniscores_player_id = %s
            ''', (incorrect_player_id,))
            
            record_to_delete = cursor.fetchone()
            if record_to_delete:
                print(f"🗑️  Found record to delete: {record_to_delete}")
                
                # Delete the incorrect record
                cursor.execute('''
                    DELETE FROM players 
                    WHERE tenniscores_player_id = %s
                ''', (incorrect_player_id,))
                
                deleted_count = cursor.rowcount
                print(f"🗑️  Deleted {deleted_count} record(s)")
                
                if deleted_count > 0:
                    conn.commit()
                    print("✅ Successfully removed incorrect Lisa Wagner Division 12 record")
                    
                    # Verify the correct record still exists
                    cursor.execute('''
                        SELECT tenniscores_player_id, first_name, last_name,
                               c.name as club_name, s.name as series_name
                        FROM players p
                        LEFT JOIN clubs c ON p.club_id = c.id
                        LEFT JOIN series s ON p.series_id = s.id
                        WHERE tenniscores_player_id = %s
                    ''', (correct_player_id,))
                    
                    remaining_record = cursor.fetchone()
                    if remaining_record:
                        print(f"✅ Confirmed correct record still exists: {remaining_record['tenniscores_player_id']} - {remaining_record['first_name']} {remaining_record['last_name']} ({remaining_record['club_name']}, {remaining_record['series_name']})")
                        return True
                    else:
                        print("❌ ERROR: Correct record not found after deletion!")
                        return False
                else:
                    print("⚠️  No records were deleted")
                    return False
            else:
                print("❌ Incorrect record not found - may have already been removed")
                return True
                
    except Exception as e:
        print(f"❌ Error removing duplicate record: {e}")
        return False

if __name__ == "__main__":
    success = remove_lisa_wagner_duplicate()
    if success:
        print("\n🎉 Lisa Wagner duplicate removal completed successfully!")
        print("🔄 Registration should now work correctly for Lisa Wagner")
    else:
        print("\n❌ Failed to remove duplicate record")
        sys.exit(1)
