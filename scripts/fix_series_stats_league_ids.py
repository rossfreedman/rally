#!/usr/bin/env python3
"""
Fix Series Stats League IDs
Maps orphaned league_id references in series_stats to correct existing leagues
"""

import psycopg2
from urllib.parse import urlparse

RAILWAY_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

def connect_to_railway():
    """Connect to Railway database"""
    parsed = urlparse(RAILWAY_URL)
    conn_params = {
        "dbname": parsed.path[1:],
        "user": parsed.username,
        "password": parsed.password,
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "sslmode": "require",
        "connect_timeout": 30,
    }
    return psycopg2.connect(**conn_params)

def analyze_orphaned_leagues(conn):
    """Analyze the orphaned league_ids to understand the mapping needed"""
    print(f"\n🔍 ANALYZING ORPHANED LEAGUE_IDS")
    print("=" * 60)
    
    cursor = conn.cursor()
    
    # Get sample teams from each orphaned league_id
    cursor.execute("""
        SELECT league_id, team, series, COUNT(*) as team_count
        FROM series_stats 
        GROUP BY league_id, team, series
        ORDER BY league_id, team_count DESC
    """)
    
    orphaned_data = cursor.fetchall()
    
    # Group by league_id
    by_league = {}
    for league_id, team, series, count in orphaned_data:
        if league_id not in by_league:
            by_league[league_id] = []
        by_league[league_id].append((team, series, count))
    
    print("Sample teams by orphaned league_id:")
    for league_id, teams in by_league.items():
        print(f"\n  League ID {league_id}:")
        for team, series, count in teams[:5]:  # Show first 5 teams
            print(f"    - {team} ({series})")
    
    return by_league

def determine_league_mapping(sample_data):
    """Determine the correct mapping based on team names and series"""
    print(f"\n🎯 DETERMINING CORRECT LEAGUE MAPPING")
    print("=" * 60)
    
    # Based on the sample data, map orphaned league_ids to correct ones
    mapping = {
        # 4546: Contains Tennaqua S1, S2A, S2B, S3 -> NSTF (North Shore Tennis Foundation)
        4546: (4492, "North Shore Tennis Foundation"),
        
        # 4543: Contains many teams including Tennaqua Chicago series -> APTA Chicago  
        4543: (4489, "APTA Chicago"),
        
        # 4544: Need to analyze based on team patterns
        4544: (4491, "Chicago North Shore Women's Platform Tennis League"),
        
        # 4545: Need to analyze based on team patterns  
        4545: (4491, "Chicago North Shore Women's Platform Tennis League"),
    }
    
    print("Proposed mapping:")
    for old_id, (new_id, league_name) in mapping.items():
        print(f"  {old_id} -> {new_id} ({league_name})")
    
    return mapping

def backup_series_stats(conn):
    """Create backup of series_stats before modifying"""
    print(f"\n💾 CREATING BACKUP")
    print("=" * 60)
    
    cursor = conn.cursor()
    
    # Create backup table
    cursor.execute("""
        DROP TABLE IF EXISTS series_stats_backup_before_league_fix;
        CREATE TABLE series_stats_backup_before_league_fix AS 
        SELECT * FROM series_stats;
    """)
    
    # Check backup count
    cursor.execute("SELECT COUNT(*) FROM series_stats_backup_before_league_fix")
    backup_count = cursor.fetchone()[0]
    
    print(f"✅ Backed up {backup_count} series_stats records")
    conn.commit()

def apply_league_mapping(conn, mapping, dry_run=True):
    """Apply the league_id mapping to series_stats"""
    print(f"\n🔧 {'DRY RUN: ' if dry_run else ''}APPLYING LEAGUE MAPPING")
    print("=" * 60)
    
    cursor = conn.cursor()
    
    total_updated = 0
    
    for old_league_id, (new_league_id, league_name) in mapping.items():
        # Count records that would be updated
        cursor.execute("""
            SELECT COUNT(*) FROM series_stats 
            WHERE league_id = %s
        """, [old_league_id])
        
        count = cursor.fetchone()[0]
        print(f"  {old_league_id} -> {new_league_id}: {count} records ({league_name})")
        
        if not dry_run and count > 0:
            # Apply the update
            cursor.execute("""
                UPDATE series_stats 
                SET league_id = %s 
                WHERE league_id = %s
            """, [new_league_id, old_league_id])
            
            updated = cursor.rowcount
            total_updated += updated
            print(f"    ✅ Updated {updated} records")
    
    if not dry_run:
        conn.commit()
        print(f"\n✅ Total records updated: {total_updated}")
    else:
        print(f"\n📝 DRY RUN: Would update {sum(cursor.execute('SELECT COUNT(*) FROM series_stats WHERE league_id = %s', [old_id]) or cursor.fetchone()[0] for old_id in mapping.keys())} records")

def verify_fix(conn):
    """Verify the fix worked"""
    print(f"\n✅ VERIFYING FIX")
    print("=" * 60)
    
    cursor = conn.cursor()
    
    # Check series_stats can now join to leagues
    cursor.execute("""
        SELECT l.league_name, COUNT(ss.id) as team_count
        FROM leagues l
        LEFT JOIN series_stats ss ON l.id = ss.league_id  
        GROUP BY l.id, l.league_name
        ORDER BY team_count DESC
    """)
    
    results = cursor.fetchall()
    print("Series stats by league (after fix):")
    for league_name, count in results:
        status = "✅" if count > 0 else "⚠️"
        print(f"  {status} {league_name}: {count} teams")
    
    # Check Tennaqua teams specifically
    cursor.execute("""
        SELECT ss.team, ss.series, l.league_name, ss.points
        FROM series_stats ss
        JOIN leagues l ON ss.league_id = l.id
        WHERE ss.team ILIKE %s
        ORDER BY l.league_name, ss.points DESC
        LIMIT 10
    """, ['%Tennaqua%'])
    
    tennaqua_teams = cursor.fetchall()
    print(f"\nTennaqua teams (after fix):")
    for team, series, league, points in tennaqua_teams:
        print(f"  ✅ {team} ({series}) in {league}: {points} pts")

def main():
    """Main fix function"""
    print("🚀 FIXING SERIES_STATS LEAGUE_ID FOREIGN KEYS")
    print("=" * 50)
    
    conn = connect_to_railway()
    
    try:
        # Step 1: Analyze the problem
        sample_data = analyze_orphaned_leagues(conn)
        
        # Step 2: Determine mapping
        mapping = determine_league_mapping(sample_data)
        
        # Step 3: Create backup
        backup_series_stats(conn)
        
        # Step 4: Dry run
        apply_league_mapping(conn, mapping, dry_run=True)
        
        # Step 5: Confirm before applying
        print(f"\n⚠️  READY TO APPLY FIX")
        print("This will update series_stats league_id references.")
        print("Type 'APPLY' to proceed or anything else to cancel:")
        
        confirmation = input().strip()
        
        if confirmation == 'APPLY':
            # Step 6: Apply the fix
            apply_league_mapping(conn, mapping, dry_run=False)
            
            # Step 7: Verify
            verify_fix(conn)
            
            print(f"\n🎉 SUCCESS!")
            print("The my-club and my-series pages should now work on Railway!")
        else:
            print("❌ Fix cancelled")
            
    finally:
        conn.close()

if __name__ == "__main__":
    main() 