#!/usr/bin/env python3
"""
Data Fix Script: Populate missing player_id values in player_availability table

This script fixes the root cause issue where availability records have NULL player_id
values by matching player_name to the players table and updating the player_id.
"""

import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one, execute_update

def fix_availability_player_ids():
    """Fix missing player_id values in player_availability table"""
    
    print("🔧 FIXING AVAILABILITY DATA: Populating missing player_id values")
    print("="*70)
    
    # Step 1: Find availability records with NULL player_id
    print("1. Finding availability records with missing player_id...")
    
    null_player_id_query = """
        SELECT id, player_name, series_id, match_date, availability_status
        FROM player_availability 
        WHERE player_id IS NULL
        ORDER BY player_name, match_date
    """
    
    null_records = execute_query(null_player_id_query)
    print(f"   Found {len(null_records)} availability records with NULL player_id")
    
    if len(null_records) == 0:
        print("   ✅ No records need fixing!")
        return
    
    print("\n   Records to fix:")
    for record in null_records:
        print(f"     ID {record['id']}: {record['player_name']} (series {record['series_id']}) - {record['match_date']}")
    
    # Step 2: For each record, find the matching player_id
    print(f"\n2. Looking up correct player_id values...")
    
    fixes = []
    not_found = []
    
    for record in null_records:
        player_name = record['player_name']
        series_id = record['series_id']
        
        # Find matching player by name and series
        player_lookup_query = """
            SELECT p.id, p.first_name, p.last_name, s.name as series_name
            FROM players p
            JOIN series s ON p.series_id = s.id
            WHERE CONCAT(p.first_name, ' ', p.last_name) = %s
            AND p.series_id = %s
            AND p.is_active = true
        """
        
        matching_player = execute_query_one(player_lookup_query, (player_name, series_id))
        
        if matching_player:
            fixes.append({
                'availability_id': record['id'],
                'player_id': matching_player['id'],
                'player_name': player_name,
                'series_name': matching_player['series_name']
            })
            print(f"   ✅ {player_name} -> player_id {matching_player['id']} ({matching_player['series_name']})")
        else:
            not_found.append({
                'availability_id': record['id'],
                'player_name': player_name,
                'series_id': series_id
            })
            print(f"   ❌ {player_name} -> No matching player found in series {series_id}")
    
    print(f"\n   Summary: {len(fixes)} fixes found, {len(not_found)} players not found")
    
    # Step 3: Apply the fixes
    if len(fixes) > 0:
        print(f"\n3. Applying fixes to {len(fixes)} records...")
        
        update_query = """
            UPDATE player_availability 
            SET player_id = %s
            WHERE id = %s
        """
        
        fixes_applied = 0
        for fix in fixes:
            try:
                rows_affected = execute_update(
                    update_query, 
                    (fix['player_id'], fix['availability_id'])
                )
                if rows_affected > 0:
                    fixes_applied += 1
                    print(f"   ✅ Fixed: {fix['player_name']} -> player_id {fix['player_id']}")
                else:
                    print(f"   ❌ Failed to update: {fix['player_name']}")
            except Exception as e:
                print(f"   ❌ Error updating {fix['player_name']}: {e}")
        
        print(f"\n   Applied {fixes_applied}/{len(fixes)} fixes successfully")
    
    # Step 4: Handle records that couldn't be matched
    if len(not_found) > 0:
        print(f"\n4. Records that couldn't be matched:")
        for record in not_found:
            print(f"   ❌ {record['player_name']} (series {record['series_id']})")
            
            # Try to find similar names
            similar_query = """
                SELECT p.id, p.first_name, p.last_name, s.name as series_name
                FROM players p
                JOIN series s ON p.series_id = s.id
                WHERE p.series_id = %s
                AND p.is_active = true
                AND (
                    LOWER(p.first_name) LIKE LOWER(%s) OR
                    LOWER(p.last_name) LIKE LOWER(%s) OR
                    LOWER(CONCAT(p.first_name, ' ', p.last_name)) LIKE LOWER(%s)
                )
                LIMIT 3
            """
            
            name_parts = record['player_name'].split()
            first_name = name_parts[0] if len(name_parts) > 0 else ""
            last_name = name_parts[-1] if len(name_parts) > 1 else ""
            full_name_pattern = f"%{record['player_name']}%"
            
            similar_players = execute_query(similar_query, (
                record['series_id'], 
                f"%{first_name}%",
                f"%{last_name}%", 
                full_name_pattern
            ))
            
            if similar_players:
                print(f"     Possible matches in same series:")
                for similar in similar_players:
                    similar_full_name = f"{similar['first_name']} {similar['last_name']}"
                    print(f"       - {similar_full_name} (ID: {similar['id']})")
    
    # Step 5: Verify the fix
    print(f"\n5. Verifying fix...")
    remaining_null = execute_query(null_player_id_query)
    print(f"   Remaining NULL player_id records: {len(remaining_null)}")
    
    if len(remaining_null) == 0:
        print("   🎉 SUCCESS: All availability records now have player_id values!")
    else:
        print(f"   ⚠️  {len(remaining_null)} records still need manual attention")
    
    return len(fixes), fixes_applied, len(not_found)

def test_steve_fretzin_fix():
    """Test that Steve Fretzin's availability is now working"""
    
    print(f"\n" + "="*70)
    print("🧪 TESTING STEVE FRETZIN FIX")
    print("="*70)
    
    # Check Steve Fretzin's availability record
    steve_query = """
        SELECT pa.id, pa.player_id, pa.player_name, pa.availability_status, pa.series_id,
               p.first_name, p.last_name, p.id as expected_player_id
        FROM player_availability pa
        LEFT JOIN players p ON CONCAT(p.first_name, ' ', p.last_name) = pa.player_name 
                              AND p.series_id = pa.series_id
        WHERE pa.player_name = 'Steve Fretzin'
        AND DATE(pa.match_date AT TIME ZONE 'UTC') = DATE('2024-09-25' AT TIME ZONE 'UTC')
    """
    
    steve_record = execute_query_one(steve_query)
    
    if steve_record:
        print(f"Steve Fretzin availability record:")
        print(f"   Availability ID: {steve_record['id']}")
        print(f"   Player ID in availability: {steve_record['player_id']}")
        print(f"   Expected Player ID: {steve_record['expected_player_id']}")
        print(f"   Status: {steve_record['availability_status']} (1=Available)")
        print(f"   Series ID: {steve_record['series_id']}")
        
        if steve_record['player_id'] == steve_record['expected_player_id']:
            print("   ✅ Player ID correctly populated!")
        else:
            print("   ❌ Player ID still doesn't match!")
    else:
        print("   ❌ Steve Fretzin availability record not found!")

if __name__ == '__main__':
    print("Starting availability data fix...")
    
    try:
        fixes_found, fixes_applied, not_found_count = fix_availability_player_ids()
        test_steve_fretzin_fix()
        
        print(f"\n" + "="*70)
        print("📊 FINAL SUMMARY")
        print("="*70)
        print(f"✅ Fixes identified: {fixes_found}")
        print(f"✅ Fixes applied: {fixes_applied}")  
        print(f"❌ Records not matched: {not_found_count}")
        
        if fixes_applied > 0:
            print(f"\n🎉 SUCCESS: Fixed {fixes_applied} availability records!")
            print("   The all-team-availability route should now work correctly")
            print("   with proper player_id matching instead of risky name matching.")
        
    except Exception as e:
        print(f"❌ Error during fix: {e}")
        import traceback
        print(traceback.format_exc()) 