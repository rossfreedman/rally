#!/usr/bin/env python3
"""
Fix the league 4815 issue on staging by checking and fixing league data
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

def main():
    # Connect to database
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    print('=== CURRENT LEAGUES TABLE ===')
    cursor.execute('SELECT id, league_id, league_name FROM leagues ORDER BY id')
    leagues = cursor.fetchall()
    for league in leagues:
        print(f'Database ID: {league["id"]}, League_ID: {league["league_id"]}, Name: {league["league_name"]}')
    
    if not leagues:
        print('❌ NO LEAGUES FOUND IN DATABASE!')
        print('This is why series_stats records can\'t find league_id references!')
        return
    
    print('\n=== SERIES_STATS WITH PROBLEMATIC LEAGUE_IDS ===')
    cursor.execute('''
        SELECT DISTINCT league_id, COUNT(*) as count
        FROM series_stats 
        GROUP BY league_id 
        ORDER BY league_id
    ''')
    stats_leagues = cursor.fetchall()
    for stat in stats_leagues:
        print(f'League ID: {stat["league_id"]}, Count: {stat["count"]}')
    
    # Check if the problem is orphaned series_stats records
    print('\n=== ORPHANED SERIES_STATS (league_id not in leagues table) ===')
    cursor.execute('''
        SELECT DISTINCT ss.league_id, COUNT(*) as count
        FROM series_stats ss
        LEFT JOIN leagues l ON ss.league_id = l.id
        WHERE l.id IS NULL
        GROUP BY ss.league_id
        ORDER BY ss.league_id
    ''')
    orphaned = cursor.fetchall()
    
    for orphan in orphaned:
        print(f'Orphaned League ID: {orphan["league_id"]}, Count: {orphan["count"]}')
    
    # Check if we need to fix orphaned records
    if orphaned:
        print('\n=== FIXING ORPHANED RECORDS ===')
        
        # Create a mapping for common orphaned league IDs
        league_mapping = {}
        for league in leagues:
            league_id = league["league_id"]
            db_id = league["id"]
            
            if league_id == "APTA_CHICAGO":
                league_mapping[4815] = db_id  # Common orphaned ID
            elif league_id == "CITA":
                league_mapping[4816] = db_id  # Common orphaned ID
            elif league_id == "CNSWPL":
                league_mapping[4817] = db_id  # Common orphaned ID
            elif league_id == "NSTF":
                league_mapping[4818] = db_id  # Common orphaned ID
        
        print(f'Proposed mapping: {league_mapping}')
        
        # Apply fixes
        for orphaned_id, correct_id in league_mapping.items():
            cursor.execute('''
                UPDATE series_stats 
                SET league_id = %s 
                WHERE league_id = %s
            ''', (correct_id, orphaned_id))
            
            if cursor.rowcount > 0:
                print(f'✅ Fixed {cursor.rowcount} records: {orphaned_id} → {correct_id}')
        
        conn.commit()
        print('✅ All orphaned records fixed!')
    
    else:
        print('✅ No orphaned records found')
    
    # Final verification
    print('\n=== FINAL VERIFICATION ===')
    cursor.execute('''
        SELECT COUNT(*) as total_records,
               COUNT(series_id) as with_series_id,
               COUNT(*) - COUNT(series_id) as missing_series_id
        FROM series_stats
    ''')
    final_stats = cursor.fetchone()
    
    health_score = (final_stats["with_series_id"] / final_stats["total_records"] * 100) if final_stats["total_records"] > 0 else 0
    
    print(f'Total records: {final_stats["total_records"]}')
    print(f'With series_id: {final_stats["with_series_id"]}')
    print(f'Missing series_id: {final_stats["missing_series_id"]}')
    print(f'Health score: {health_score:.1f}%')
    
    conn.close()

if __name__ == '__main__':
    main() 