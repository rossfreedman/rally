#!/usr/bin/env python3
"""
Validate player data for duplicates that should not be duplicates.
This script checks for various types of problematic duplicates in the players table.
"""

import psycopg2
import sys
from collections import defaultdict

def connect_to_database():
    """Connect to the local database."""
    try:
        conn = psycopg2.connect('postgresql://rossfreedman@localhost:5432/rally')
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

def validate_duplicates(conn):
    """Validate the players table for various types of duplicates."""
    cur = conn.cursor()
    
    print("🔍 VALIDATING PLAYER DATA FOR PROBLEMATIC DUPLICATES")
    print("=" * 60)
    
    # 1. Check for duplicate tenniscores_player_id with different names
    print("\n1. Checking for same tenniscores_player_id with different names...")
    cur.execute("""
        SELECT tenniscores_player_id, 
               COUNT(DISTINCT first_name || ' ' || last_name) as name_count,
               STRING_AGG(DISTINCT first_name || ' ' || last_name, ', ') as names
        FROM players 
        WHERE tenniscores_player_id IS NOT NULL 
        AND tenniscores_player_id != ''
        GROUP BY tenniscores_player_id 
        HAVING COUNT(DISTINCT first_name || ' ' || last_name) > 1
        ORDER BY name_count DESC
    """)
    
    results = cur.fetchall()
    if results:
        print(f"❌ Found {len(results)} tenniscores_player_ids with different names:")
        for player_id, count, names in results[:10]:  # Show first 10
            print(f"   Player ID: {player_id} -> Names: {names}")
        if len(results) > 10:
            print(f"   ... and {len(results) - 10} more")
    else:
        print("✅ No tenniscores_player_ids with different names found")
    
    # 2. Check for same name with different tenniscores_player_ids
    print("\n2. Checking for same name with different tenniscores_player_ids...")
    cur.execute("""
        SELECT first_name || ' ' || last_name as full_name,
               COUNT(DISTINCT tenniscores_player_id) as id_count,
               STRING_AGG(DISTINCT tenniscores_player_id, ', ') as player_ids
        FROM players 
        WHERE first_name IS NOT NULL AND last_name IS NOT NULL
        GROUP BY first_name, last_name 
        HAVING COUNT(DISTINCT tenniscores_player_id) > 1
        ORDER BY id_count DESC
    """)
    
    results = cur.fetchall()
    if results:
        print(f"❌ Found {len(results)} names with different tenniscores_player_ids:")
        for name, count, ids in results[:10]:  # Show first 10
            print(f"   Name: {name} -> Player IDs: {ids}")
        if len(results) > 10:
            print(f"   ... and {len(results) - 10} more")
    else:
        print("✅ No names with different tenniscores_player_ids found")
    
    # 3. Check for same player in same league/club/series with different tenniscores_player_ids
    print("\n3. Checking for same player in same league/club/series with different tenniscores_player_ids...")
    cur.execute("""
        SELECT first_name, last_name, league_id, club_id, series_id,
               COUNT(DISTINCT tenniscores_player_id) as id_count,
               STRING_AGG(DISTINCT tenniscores_player_id, ', ') as player_ids
        FROM players 
        WHERE first_name IS NOT NULL AND last_name IS NOT NULL
        GROUP BY first_name, last_name, league_id, club_id, series_id
        HAVING COUNT(DISTINCT tenniscores_player_id) > 1
        ORDER BY id_count DESC
    """)
    
    results = cur.fetchall()
    if results:
        print(f"❌ Found {len(results)} same league/club/series combinations with different tenniscores_player_ids:")
        for first_name, last_name, league_id, club_id, series_id, count, ids in results[:10]:
            print(f"   {first_name} {last_name} (League: {league_id}, Club: {club_id}, Series: {series_id}) -> Player IDs: {ids}")
        if len(results) > 10:
            print(f"   ... and {len(results) - 10} more")
    else:
        print("✅ No same league/club/series combinations with different tenniscores_player_ids found")
    
    # 4. Check for exact duplicates (same everything)
    print("\n4. Checking for exact duplicates (same everything)...")
    cur.execute("""
        SELECT first_name, last_name, league_id, club_id, series_id, tenniscores_player_id,
               COUNT(*) as duplicate_count
        FROM players 
        GROUP BY first_name, last_name, league_id, club_id, series_id, tenniscores_player_id
        HAVING COUNT(*) > 1
        ORDER BY duplicate_count DESC
    """)
    
    results = cur.fetchall()
    if results:
        print(f"❌ Found {len(results)} exact duplicates:")
        for first_name, last_name, league_id, club_id, series_id, player_id, count in results[:10]:
            print(f"   {first_name} {last_name} (League: {league_id}, Club: {club_id}, Series: {series_id}, Player ID: {player_id}) -> {count} copies")
        if len(results) > 10:
            print(f"   ... and {len(results) - 10} more")
    else:
        print("✅ No exact duplicates found")
    
    # 5. Check for players with same name in different series (this might be legitimate)
    print("\n5. Checking for same name in different series (might be legitimate)...")
    cur.execute("""
        SELECT first_name || ' ' || last_name as full_name,
               COUNT(DISTINCT series_id) as series_count,
               STRING_AGG(DISTINCT series_id::text, ', ') as series_ids
        FROM players 
        WHERE first_name IS NOT NULL AND last_name IS NOT NULL
        GROUP BY first_name, last_name
        HAVING COUNT(DISTINCT series_id) > 1
        ORDER BY series_count DESC
    """)
    
    results = cur.fetchall()
    if results:
        print(f"ℹ️  Found {len(results)} names in multiple series (this might be legitimate):")
        for name, count, series in results[:10]:  # Show first 10
            print(f"   {name} -> Series: {series}")
        if len(results) > 10:
            print(f"   ... and {len(results) - 10} more")
    else:
        print("✅ No names in multiple series found")
    
    # 6. Check for players with same tenniscores_player_id in different series (this might be legitimate)
    print("\n6. Checking for same tenniscores_player_id in different series (might be legitimate)...")
    cur.execute("""
        SELECT tenniscores_player_id,
               COUNT(DISTINCT series_id) as series_count,
               STRING_AGG(DISTINCT series_id::text, ', ') as series_ids
        FROM players 
        WHERE tenniscores_player_id IS NOT NULL 
        AND tenniscores_player_id != ''
        GROUP BY tenniscores_player_id
        HAVING COUNT(DISTINCT series_id) > 1
        ORDER BY series_count DESC
    """)
    
    results = cur.fetchall()
    if results:
        print(f"ℹ️  Found {len(results)} tenniscores_player_ids in multiple series (this might be legitimate):")
        for player_id, count, series in results[:10]:  # Show first 10
            print(f"   Player ID: {player_id} -> Series: {series}")
        if len(results) > 10:
            print(f"   ... and {len(results) - 10} more")
    else:
        print("✅ No tenniscores_player_ids in multiple series found")
    
    # 7. Check for players with missing tenniscores_player_id but same name/league/club/series
    print("\n7. Checking for players with missing tenniscores_player_id but same name/league/club/series...")
    cur.execute("""
        SELECT first_name, last_name, league_id, club_id, series_id,
               COUNT(*) as duplicate_count
        FROM players 
        WHERE (tenniscores_player_id IS NULL OR tenniscores_player_id = '')
        GROUP BY first_name, last_name, league_id, club_id, series_id
        HAVING COUNT(*) > 1
        ORDER BY duplicate_count DESC
    """)
    
    results = cur.fetchall()
    if results:
        print(f"❌ Found {len(results)} players with missing tenniscores_player_id but same name/league/club/series:")
        for first_name, last_name, league_id, club_id, series_id, count in results[:10]:
            print(f"   {first_name} {last_name} (League: {league_id}, Club: {club_id}, Series: {series_id}) -> {count} copies")
        if len(results) > 10:
            print(f"   ... and {len(results) - 10} more")
    else:
        print("✅ No players with missing tenniscores_player_id but same name/league/club/series found")
    
    # 8. Summary statistics
    print("\n8. Summary Statistics...")
    cur.execute("SELECT COUNT(*) FROM players")
    total_players = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(DISTINCT tenniscores_player_id) FROM players WHERE tenniscores_player_id IS NOT NULL AND tenniscores_player_id != ''")
    unique_player_ids = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(DISTINCT first_name || ' ' || last_name) FROM players WHERE first_name IS NOT NULL AND last_name IS NOT NULL")
    unique_names = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(DISTINCT first_name || ' ' || last_name || '|' || league_id || '|' || club_id || '|' || series_id) FROM players")
    unique_combinations = cur.fetchone()[0]
    
    print(f"   Total players: {total_players:,}")
    print(f"   Unique tenniscores_player_ids: {unique_player_ids:,}")
    print(f"   Unique names: {unique_names:,}")
    print(f"   Unique name+league+club+series combinations: {unique_combinations:,}")
    
    cur.close()

def main():
    """Main function."""
    conn = connect_to_database()
    try:
        validate_duplicates(conn)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
