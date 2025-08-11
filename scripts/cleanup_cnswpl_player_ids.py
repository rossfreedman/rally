#!/usr/bin/env python3
"""
Cleanup CNSWPL Player IDs
=========================

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

def cleanup_cnswpl_player_ids():
    """Remove all CNSWPL players with 'nndz' player IDs"""
    
    print("🔍 Cleaning up CNSWPL player IDs...")
    print("❌ Removing all CNSWPL players with 'nndz' IDs")
    print("✅ Keeping only CNSWPL players with 'cnswpl_' IDs")
    print()
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # First, find all CNSWPL players with nndz IDs
            cursor.execute('''
                SELECT p.tenniscores_player_id, p.first_name, p.last_name,
                       c.name as club_name, s.name as series_name, l.league_id
                FROM players p
                LEFT JOIN clubs c ON p.club_id = c.id
                LEFT JOIN series s ON p.series_id = s.id
                LEFT JOIN leagues l ON p.league_id = l.id
                WHERE l.league_id = 'CNSWPL' 
                AND p.tenniscores_player_id LIKE 'nndz%'
                ORDER BY p.last_name, p.first_name
            ''')
            
            incorrect_records = cursor.fetchall()
            
            if not incorrect_records:
                print("✅ No incorrect CNSWPL player IDs found (nndz prefix)")
                return True
            
            print(f"📋 Found {len(incorrect_records)} CNSWPL players with incorrect 'nndz' IDs:")
            for record in incorrect_records:
                print(f"  ❌ {record['tenniscores_player_id']}: {record['first_name']} {record['last_name']} ({record['club_name']}, {record['series_name']})")
            print()
            
            # Also show how many correct CNSWPL players exist
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM players p
                LEFT JOIN leagues l ON p.league_id = l.id
                WHERE l.league_id = 'CNSWPL' 
                AND p.tenniscores_player_id LIKE 'cnswpl_%'
            ''')
            
            correct_count = cursor.fetchone()['count']
            print(f"✅ Current correct CNSWPL players (cnswpl_ prefix): {correct_count}")
            print()
            
            # Confirm deletion
            response = input(f"🗑️  Delete {len(incorrect_records)} incorrect CNSWPL records? (y/N): ")
            if response.lower() != 'y':
                print("❌ Aborted by user")
                return False
            
            # Delete all CNSWPL players with nndz IDs
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
                    SELECT COUNT(*) as count
                    FROM players p
                    LEFT JOIN leagues l ON p.league_id = l.id
                    WHERE l.league_id = 'CNSWPL' 
                    AND p.tenniscores_player_id LIKE 'nndz%'
                ''')
                
                remaining_incorrect = cursor.fetchone()['count']
                
                cursor.execute('''
                    SELECT COUNT(*) as count
                    FROM players p
                    LEFT JOIN leagues l ON p.league_id = l.id
                    WHERE l.league_id = 'CNSWPL' 
                    AND p.tenniscores_player_id LIKE 'cnswpl_%'
                ''')
                
                remaining_correct = cursor.fetchone()['count']
                
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
        return False

def preview_cleanup():
    """Preview what would be cleaned up without making changes"""
    
    print("👀 PREVIEW: CNSWPL Player ID Cleanup")
    print("=====================================")
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Count incorrect records
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM players p
                LEFT JOIN leagues l ON p.league_id = l.id
                WHERE l.league_id = 'CNSWPL' 
                AND p.tenniscores_player_id LIKE 'nndz%'
            ''')
            
            incorrect_count = cursor.fetchone()['count']
            
            # Count correct records
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM players p
                LEFT JOIN leagues l ON p.league_id = l.id
                WHERE l.league_id = 'CNSWPL' 
                AND p.tenniscores_player_id LIKE 'cnswpl_%'
            ''')
            
            correct_count = cursor.fetchone()['count']
            
            print(f"❌ CNSWPL players with incorrect 'nndz' IDs: {incorrect_count}")
            print(f"✅ CNSWPL players with correct 'cnswpl_' IDs: {correct_count}")
            print()
            
            if incorrect_count > 0:
                print("📋 Sample incorrect records to be removed:")
                cursor.execute('''
                    SELECT p.tenniscores_player_id, p.first_name, p.last_name,
                           c.name as club_name, s.name as series_name
                    FROM players p
                    LEFT JOIN clubs c ON p.club_id = c.id
                    LEFT JOIN series s ON p.series_id = s.id
                    LEFT JOIN leagues l ON p.league_id = l.id
                    WHERE l.league_id = 'CNSWPL' 
                    AND p.tenniscores_player_id LIKE 'nndz%'
                    ORDER BY p.last_name, p.first_name
                    LIMIT 10
                ''')
                
                sample_records = cursor.fetchall()
                for record in sample_records:
                    print(f"  ❌ {record['tenniscores_player_id']}: {record['first_name']} {record['last_name']} ({record['club_name']}, {record['series_name']})")
                
                if incorrect_count > 10:
                    print(f"  ... and {incorrect_count - 10} more")
            
            return incorrect_count, correct_count
            
    except Exception as e:
        print(f"❌ Error previewing cleanup: {e}")
        return 0, 0

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Cleanup CNSWPL player IDs")
    parser.add_argument("--preview", action="store_true", help="Preview cleanup without making changes")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")
    
    args = parser.parse_args()
    
    if args.preview:
        preview_cleanup()
    else:
        if args.force:
            # Override input function for automated execution
            def mock_input(prompt):
                print(f"{prompt}y (forced)")
                return "y"
            __builtins__['input'] = mock_input
        
        success = cleanup_cnswpl_player_ids()
        if success:
            print("\n🎉 CNSWPL player ID cleanup completed successfully!")
            print("🔄 All CNSWPL players now have correct 'cnswpl_' prefix IDs")
        else:
            print("\n❌ Failed to cleanup CNSWPL player IDs")
            sys.exit(1)
