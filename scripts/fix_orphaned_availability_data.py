#!/usr/bin/env python3
"""
Fix Orphaned Availability Data
===============================

This script fixes player_availability records that have orphaned player_id values
after ETL imports that recreate the players table with new auto-increment IDs.

The script:
1. Identifies availability records with player_id values that don't exist in players table
2. Attempts to match them to current players by name and series
3. Updates the player_id values to the correct current IDs
4. Reports on successful matches and unresolved orphans
"""

import sys
import os

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from database_utils import execute_query
from datetime import datetime

def fix_orphaned_availability_data():
    """Fix orphaned player_availability records by matching names to current player IDs"""
    
    print("🔧 Fixing Orphaned Player Availability Data")
    print("=" * 50)
    
    # Step 1: Identify orphaned records (both player_id and series_id can be orphaned)
    print("📊 Step 1: Identifying orphaned availability records...")
    
    orphaned_records = execute_query("""
        SELECT pa.id, pa.player_name, pa.player_id, pa.series_id, pa.match_date, pa.availability_status, pa.notes,
               s.name as series_name, p.id as current_player_id
        FROM player_availability pa
        LEFT JOIN series s ON pa.series_id = s.id
        LEFT JOIN players p ON pa.player_id = p.id
        WHERE p.id IS NULL OR s.id IS NULL
        ORDER BY pa.player_name, pa.match_date
    """)
    
    print(f"Found {len(orphaned_records):,} orphaned availability records")
    
    if not orphaned_records:
        print("✅ No orphaned records found!")
        return
    
    # Step 2: Attempt to match orphaned records to current players and series
    print("\n🔍 Step 2: Matching orphaned records to current players and series...")
    
    matched_count = 0
    unmatched_count = 0
    series_mismatches = 0
    
    for record in orphaned_records:
        player_name = record['player_name']
        old_player_id = record['player_id']
        old_series_id = record['series_id']
        series_name = record['series_name']  # May be None if series is orphaned too
        availability_id = record['id']
        match_date = record['match_date']
        
        # Try to find current player by name across all series (since series might be orphaned too)
        current_players = execute_query("""
            SELECT p.id, p.tenniscores_player_id, p.first_name, p.last_name, p.series_id, s.name as series_name
            FROM players p
            JOIN series s ON p.series_id = s.id
            WHERE CONCAT(p.first_name, ' ', p.last_name) = %s
            AND p.is_active = true
            ORDER BY p.id
        """, [player_name.strip()])
        
        if current_players:
            # Use the first match (could be improved with better matching logic)
            best_match = current_players[0]
            new_player_id = best_match['id']
            new_series_id = best_match['series_id']
            tenniscores_id = best_match['tenniscores_player_id']
            current_series_name = best_match['series_name']
            
            # Check if updating would create a duplicate (player_name, match_date, series_id)
            duplicate_check = execute_query("""
                SELECT id FROM player_availability 
                WHERE player_name = %s 
                AND DATE(match_date AT TIME ZONE 'UTC') = DATE(%s AT TIME ZONE 'UTC')
                AND series_id = %s
                AND id != %s
            """, [player_name.strip(), match_date, new_series_id, availability_id])
            
            if duplicate_check:
                # A non-orphaned record already exists - delete this orphaned duplicate
                execute_query("DELETE FROM player_availability WHERE id = %s", [availability_id])
                matched_count += 1
                if matched_count <= 10:
                    print(f"   🗑️  {player_name} ({series_name or 'Unknown'} → {current_series_name}): Deleted orphaned duplicate (ID: {availability_id})")
            else:
                # Safe to update - no duplicate will be created
                execute_query("""
                    UPDATE player_availability 
                    SET player_id = %s, series_id = %s
                    WHERE id = %s
                """, [new_player_id, new_series_id, availability_id])
                
                matched_count += 1
                if matched_count <= 10:  # Log first 10 matches
                    series_info = f"({series_name or 'Unknown'} → {current_series_name})" if series_name != current_series_name else f"({current_series_name})"
                    print(f"   ✅ {player_name} {series_info}: P{old_player_id}→{new_player_id}, S{old_series_id}→{new_series_id}")
                
        else:
            unmatched_count += 1
            if unmatched_count <= 5:  # Log first 5 unmatched
                print(f"   ❌ {player_name} (S{old_series_id}): No current player found")
    
    # Step 3: Report results
    print(f"\n📊 Step 3: Results Summary")
    print(f"   ✅ Successfully matched: {matched_count:,} records")
    print(f"   ❌ Unmatched: {unmatched_count:,} records")
    
    # Step 4: Verify fix
    print(f"\n🔍 Step 4: Verification...")
    remaining_orphans = execute_query("""
        SELECT COUNT(*) as count
        FROM player_availability pa
        LEFT JOIN players p ON pa.player_id = p.id
        LEFT JOIN series s ON pa.series_id = s.id
        WHERE p.id IS NULL OR s.id IS NULL
    """)
    
    remaining_count = remaining_orphans[0]['count'] if remaining_orphans else 0
    print(f"   Remaining orphaned records: {remaining_count:,}")
    
    if remaining_count == 0:
        print("   🎉 All orphaned availability records have been fixed!")
    elif remaining_count < len(orphaned_records):
        fixed_count = len(orphaned_records) - remaining_count
        print(f"   ✅ Fixed {fixed_count:,} out of {len(orphaned_records):,} orphaned records")
        print(f"   ⚠️  {remaining_count:,} records still orphaned (likely players no longer exist)")
    
    print(f"\n✅ Orphaned availability data fix completed!")

def preview_orphaned_data():
    """Preview orphaned availability data without making changes"""
    
    print("👀 Preview of Orphaned Availability Data")
    print("=" * 45)
    
    # Show sample of orphaned records (handle both player and series orphans)
    orphaned_sample = execute_query("""
        SELECT pa.player_name, pa.player_id, pa.series_id, pa.match_date, pa.availability_status,
               s.name as series_name, p.id as current_player_id
        FROM player_availability pa
        LEFT JOIN series s ON pa.series_id = s.id
        LEFT JOIN players p ON pa.player_id = p.id
        WHERE p.id IS NULL OR s.id IS NULL
        ORDER BY pa.match_date DESC, pa.player_name
        LIMIT 10
    """)
    
    if orphaned_sample:
        print(f"Sample of orphaned records:")
        print(f"{'Player':<20} {'Date':<12} {'P.ID':<8} {'S.ID':<8} {'Series':<15} {'Status'}")
        print("-" * 75)
        for record in orphaned_sample:
            date_str = record['match_date'].strftime('%Y-%m-%d') if record['match_date'] else 'N/A'
            series_name = record['series_name'] or 'MISSING'
            player_exists = '✓' if record['current_player_id'] else '✗'
            print(f"{record['player_name']:<20} {date_str:<12} {record['player_id']:<8} {record['series_id']:<8} {series_name:<15} {record['availability_status']}")
    else:
        print("✅ No orphaned records found!")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--preview":
        preview_orphaned_data()
    else:
        fix_orphaned_availability_data() 