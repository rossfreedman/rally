#!/usr/bin/env python3
"""
Fix Series Stats References

This script fixes the series_stats table to properly reference the canonical
series names and IDs from the series table.

Issues fixed:
1. series_stats has "Series 2B" but series table has "S2B"
2. series_stats.series_id is NULL for most records
3. API lookups failing because of name/ID mismatches

Usage: python scripts/fix_series_stats_references.py [--dry-run]
"""

import os
import sys
import argparse

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from database_config import get_db


def log(message: str):
    print(f"[{__name__}] {message}")


def fix_series_stats_references(dry_run=False):
    """Fix series_stats table references to match canonical series names"""
    
    log("🔧 Fixing series_stats references...")
    
    # Common series name mappings for NSTF
    nstf_mappings = {
        "Series 1": "S1",
        "Series 2A": "S2A", 
        "Series 2B": "S2B",
        "Series 3": "S3",
        "Series A": "SA"  # This one might already be correct
    }
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get all series_stats records that need fixing
        cursor.execute("""
            SELECT ss.id, ss.series, ss.series_id, ss.league_id, l.league_name
            FROM series_stats ss
            JOIN leagues l ON ss.league_id = l.id
            WHERE ss.series_id IS NULL OR ss.series != (
                SELECT s.name FROM series s WHERE s.id = ss.series_id
            )
            ORDER BY l.league_name, ss.series
        """)
        
        records_to_fix = cursor.fetchall()
        log(f"Found {len(records_to_fix)} series_stats records to fix")
        
        fixed_count = 0
        
        for record in records_to_fix:
            record_id = record[0]
            current_series = record[1]
            current_series_id = record[2]
            league_id = record[3]
            league_name = record[4]
            
            # Determine correct series name
            correct_series_name = current_series
            if league_name == "North Shore Tennis Foundation" and current_series in nstf_mappings:
                correct_series_name = nstf_mappings[current_series]
            
            # Look up the correct series_id
            cursor.execute("""
                SELECT s.id, s.name
                FROM series s
                JOIN series_leagues sl ON s.id = sl.series_id
                WHERE s.name = %s AND sl.league_id = %s
            """, (correct_series_name, league_id))
            
            series_match = cursor.fetchone()
            
            if series_match:
                correct_series_id = series_match[0]
                correct_series_name = series_match[1]
                
                log(f"  Fixing: '{current_series}' → '{correct_series_name}' (ID: {correct_series_id})")
                
                if not dry_run:
                    cursor.execute("""
                        UPDATE series_stats 
                        SET series = %s, series_id = %s
                        WHERE id = %s
                    """, (correct_series_name, correct_series_id, record_id))
                    
                fixed_count += 1
            else:
                log(f"  ⚠️  No match found for '{current_series}' → '{correct_series_name}' in league {league_name}")
        
        if not dry_run:
            conn.commit()
            log(f"✅ Fixed {fixed_count} series_stats records")
        else:
            log(f"🔍 Would fix {fixed_count} series_stats records")
    
    return fixed_count


def verify_fix():
    """Verify that the fix worked"""
    log("🔍 Verifying series_stats references...")
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check for records with NULL series_id
        cursor.execute("SELECT COUNT(*) FROM series_stats WHERE series_id IS NULL")
        null_count = cursor.fetchone()[0]
        log(f"Records with NULL series_id: {null_count}")
        
        # Check for mismatched series names
        cursor.execute("""
            SELECT COUNT(*) FROM series_stats ss
            JOIN series s ON ss.series_id = s.id
            WHERE ss.series != s.name
        """)
        mismatch_count = cursor.fetchone()[0]
        log(f"Records with mismatched series names: {mismatch_count}")
        
        # Check Ross's specific case
        cursor.execute("""
            SELECT COUNT(*) FROM series_stats ss
            WHERE ss.series_id = 11854  -- Ross's series_id (S2B)
        """)
        ross_series_count = cursor.fetchone()[0]
        log(f"Series stats for Ross's series (S2B, ID 11854): {ross_series_count}")
        
        if null_count == 0 and mismatch_count == 0 and ross_series_count > 0:
            log("✅ All series_stats references are properly fixed!")
            return True
        else:
            log("❌ Some issues remain")
            return False


def main():
    parser = argparse.ArgumentParser(description="Fix series_stats table references")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without making changes")
    args = parser.parse_args()
    
    log("🚀 Starting series_stats reference fix...")
    
    if args.dry_run:
        log("🔍 DRY RUN MODE - No changes will be made")
    
    fixed_count = fix_series_stats_references(args.dry_run)
    
    if not args.dry_run:
        verify_fix()
    
    log(f"✅ Complete! {'Would fix' if args.dry_run else 'Fixed'} {fixed_count} records")


if __name__ == "__main__":
    main() 