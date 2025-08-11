#!/usr/bin/env python3
"""
Simple CNSWPL Player ID Cleanup
===============================

Remove all CNSWPL players that have 'nndz' player IDs.
All CNSWPL players should have 'cnswpl_' prefix player IDs only.
"""

import os
import sys
from pathlib import Path

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = Path(script_dir).parent
sys.path.insert(0, str(project_root))

from database_config import get_db

def cleanup_cnswpl_nndz_players():
    """Remove all CNSWPL players with 'nndz' player IDs"""
    
    print("🔍 Cleaning up CNSWPL player IDs...")
    print("❌ Removing all CNSWPL players with 'nndz' IDs")
    print()
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Find and count CNSWPL players with nndz IDs
            print("📋 Finding CNSWPL players with incorrect 'nndz' IDs...")
            cursor.execute('''
                SELECT p.tenniscores_player_id, p.first_name, p.last_name
                FROM players p
                JOIN leagues l ON p.league_id = l.id
                WHERE l.league_id = 'CNSWPL' 
                AND p.tenniscores_player_id LIKE 'nndz%'
                ORDER BY p.last_name, p.first_name
            ''')
            
            incorrect_records = cursor.fetchall()
            
            if not incorrect_records:
                print("✅ No incorrect CNSWPL player IDs found (nndz prefix)")
                return True
            
            print(f"Found {len(incorrect_records)} CNSWPL players with incorrect 'nndz' IDs:")
            for i, record in enumerate(incorrect_records):
                player_id = record[0]
                first_name = record[1] 
                last_name = record[2]
                print(f"  {i+1}. ❌ {player_id}: {first_name} {last_name}")
                if i >= 9:  # Show max 10, then truncate
                    remaining = len(incorrect_records) - 10
                    if remaining > 0:
                        print(f"  ... and {remaining} more")
                    break
            print()
            
            # Count correct CNSWPL players
            cursor.execute('''
                SELECT COUNT(*)
                FROM players p
                JOIN leagues l ON p.league_id = l.id
                WHERE l.league_id = 'CNSWPL' 
                AND p.tenniscores_player_id LIKE 'cnswpl_%'
            ''')
            
            correct_count = cursor.fetchone()[0]
            print(f"✅ Current correct CNSWPL players (cnswpl_ prefix): {correct_count}")
            print()
            
            # Delete all CNSWPL players with nndz IDs
            print(f"🗑️  Deleting {len(incorrect_records)} incorrect CNSWPL records...")
            cursor.execute('''
                DELETE FROM players 
                WHERE league_id IN (
                    SELECT id FROM leagues WHERE league_id = 'CNSWPL'
                )
                AND tenniscores_player_id LIKE 'nndz%'
            ''')
            
            deleted_count = cursor.rowcount
            print(f"🗑️  Deleted {deleted_count} incorrect CNSWPL records")
            
            if deleted_count > 0:
                conn.commit()
                print("✅ Successfully removed all incorrect CNSWPL player IDs")
                
                # Verify cleanup
                cursor.execute('''
                    SELECT COUNT(*)
                    FROM players p
                    JOIN leagues l ON p.league_id = l.id
                    WHERE l.league_id = 'CNSWPL' 
                    AND p.tenniscores_player_id LIKE 'nndz%'
                ''')
                
                remaining_incorrect = cursor.fetchone()[0]
                
                cursor.execute('''
                    SELECT COUNT(*)
                    FROM players p
                    JOIN leagues l ON p.league_id = l.id
                    WHERE l.league_id = 'CNSWPL' 
                    AND p.tenniscores_player_id LIKE 'cnswpl_%'
                ''')
                
                remaining_correct = cursor.fetchone()[0]
                
                print(f"✅ Cleanup verification:")
                print(f"  ❌ Remaining incorrect (nndz): {remaining_incorrect}")
                print(f"  ✅ Remaining correct (cnswpl_): {remaining_correct}")
                
                if remaining_incorrect == 0:
                    print("🎉 All incorrect CNSWPL player IDs successfully removed!")
                    return True
                else:
                    print(f"⚠️  Warning: {remaining_incorrect} incorrect records still remain")
                    return False
            else:
                print("⚠️  No records were deleted")
                return False
                
    except Exception as e:
        print(f"❌ Error cleaning up CNSWPL player IDs: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = cleanup_cnswpl_nndz_players()
    if success:
        print("\n🎉 CNSWPL player ID cleanup completed successfully!")
        print("🔄 All CNSWPL players now have correct 'cnswpl_' prefix IDs")
    else:
        print("\n❌ Failed to cleanup CNSWPL player IDs")
        sys.exit(1)
