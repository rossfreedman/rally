#!/usr/bin/env python3
"""
Clean up duplicate player records in staging database
"""

import psycopg2
import sys

# Staging database configuration
STAGING_DB_URL = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"
APTA_LEAGUE_ID = 4783

def execute_query(query, params=None):
    """Execute query and return results."""
    try:
        conn = psycopg2.connect(STAGING_DB_URL)
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()
    except Exception as e:
        print(f"❌ Query error: {e}")
        return []

def execute_update(query, params=None):
    """Execute update and return affected rows."""
    try:
        conn = psycopg2.connect(STAGING_DB_URL)
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
            return cur.rowcount
    except Exception as e:
        print(f"❌ Update error: {e}")
        return 0

def find_duplicates():
    """Find all duplicate player records."""
    print("🔍 FINDING DUPLICATE PLAYER RECORDS")
    print("=" * 40)
    
    query = """
    SELECT 
        p.tenniscores_player_id, 
        p.league_id, 
        p.club_id, 
        p.series_id,
        COUNT(*) as duplicate_count,
        array_agg(p.id ORDER BY p.id) as player_ids,
        array_agg(p.first_name || ' ' || p.last_name ORDER BY p.id) as names,
        array_agg(p.wins ORDER BY p.id) as wins,
        array_agg(p.losses ORDER BY p.id) as losses
    FROM players p
    JOIN teams t ON p.team_id = t.id
    WHERE t.league_id = %s
    GROUP BY p.tenniscores_player_id, p.league_id, p.club_id, p.series_id
    HAVING COUNT(*) > 1
    ORDER BY COUNT(*) DESC
    """
    
    duplicates = execute_query(query, (APTA_LEAGUE_ID,))
    
    print(f"Found {len(duplicates)} duplicate combinations:")
    for dup in duplicates:
        print(f"\\nTenniscores ID: {dup[0]}")
        print(f"  - League: {dup[1]}, Club: {dup[2]}, Series: {dup[3]}")
        print(f"  - Duplicate count: {dup[4]}")
        print(f"  - Player IDs: {dup[5]}")
        print(f"  - Names: {dup[6]}")
        print(f"  - Wins: {dup[7]}")
        print(f"  - Losses: {dup[8]}")
    
    return duplicates

def cleanup_duplicates(duplicates):
    """Clean up duplicate player records."""
    print("\\n🧹 CLEANING UP DUPLICATE RECORDS")
    print("=" * 40)
    
    total_deleted = 0
    
    for dup in duplicates:
        tenniscores_id = dup[0]
        player_ids = dup[5]
        names = dup[6]
        wins = dup[7]
        losses = dup[8]
        
        print(f"\\nProcessing {tenniscores_id} ({names[0]}):")
        
        # Keep the record with the most activity (wins + losses)
        best_record_idx = 0
        best_activity = (wins[0] or 0) + (losses[0] or 0)
        
        for i in range(1, len(player_ids)):
            activity = (wins[i] or 0) + (losses[i] or 0)
            if activity > best_activity:
                best_record_idx = i
                best_activity = activity
        
        keep_id = player_ids[best_record_idx]
        delete_ids = [pid for i, pid in enumerate(player_ids) if i != best_record_idx]
        
        print(f"  - Keeping record {keep_id} (activity: {best_activity})")
        print(f"  - Deleting records: {delete_ids}")
        
        # Delete the duplicate records
        for delete_id in delete_ids:
            result = execute_update("DELETE FROM players WHERE id = %s", (delete_id,))
            total_deleted += result
            print(f"    - Deleted record {delete_id}")
    
    print(f"\\n✅ Total records deleted: {total_deleted}")
    return total_deleted

def add_unique_constraint():
    """Add the unique constraint back."""
    print("\\n🔒 ADDING UNIQUE CONSTRAINT")
    print("=" * 30)
    
    try:
        result = execute_update("""
        ALTER TABLE players 
        ADD CONSTRAINT unique_player_in_league_club_series 
        UNIQUE (tenniscores_player_id, league_id, club_id, series_id)
        """)
        print("✅ Successfully added unique_player_in_league_club_series constraint")
        return True
    except Exception as e:
        print(f"❌ Failed to add constraint: {e}")
        return False

def verify_cleanup():
    """Verify that duplicates are cleaned up."""
    print("\\n🔍 VERIFYING CLEANUP")
    print("=" * 25)
    
    # Check for remaining duplicates
    duplicates = find_duplicates()
    
    if len(duplicates) == 0:
        print("✅ No duplicate records found")
        
        # Check Chris Tag specifically
        chris_query = """
        SELECT 
            p.id as player_id,
            p.first_name, p.last_name, p.tenniscores_player_id, 
            t.team_name, c.name as club_name, s.name as series_name,
            p.pti, p.wins, p.losses
        FROM players p
        JOIN teams t ON p.team_id = t.id
        JOIN clubs c ON t.club_id = c.id
        JOIN series s ON t.series_id = s.id
        WHERE t.league_id = %s
            AND p.first_name = 'Chris' AND p.last_name = 'Tag'
        ORDER BY p.id
        """
        
        chris_tag = execute_query(chris_query, (APTA_LEAGUE_ID,))
        
        print(f"\\nChris Tag records: {len(chris_tag)}")
        for player in chris_tag:
            print(f"  - ID {player[0]}: {player[1]} {player[2]} on {player[4]} ({player[5]}) in {player[6]}")
            print(f"    PTI: {player[7]}, Record: {player[8]}W-{player[9]}L")
        
        return True
    else:
        print(f"❌ Still have {len(duplicates)} duplicate combinations")
        return False

def main():
    """Main function."""
    print("🚀 CLEANING UP STAGING DATABASE DUPLICATES")
    print("=" * 50)
    print(f"Database: {STAGING_DB_URL}")
    print(f"League ID: {APTA_LEAGUE_ID}")
    print()
    
    # Find duplicates
    duplicates = find_duplicates()
    
    if len(duplicates) == 0:
        print("✅ No duplicates found!")
        return True
    
    # Clean up duplicates
    deleted_count = cleanup_duplicates(duplicates)
    
    # Add unique constraint
    constraint_added = add_unique_constraint()
    
    # Verify cleanup
    cleanup_successful = verify_cleanup()
    
    if cleanup_successful and constraint_added:
        print("\\n🎉 STAGING DATABASE CLEANUP COMPLETE!")
        print("=" * 40)
        print("✅ All duplicate records removed")
        print("✅ Unique constraint added")
        print("✅ Chris Tag has only one record")
        print("✅ Database integrity maintained")
        return True
    else:
        print("\\n❌ Cleanup incomplete")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
