#!/usr/bin/env python3
"""
Debug series_id health issue on staging
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
    
    print('=== LEAGUES IN DATABASE ===')
    cursor.execute('SELECT id, name, league_id FROM leagues ORDER BY id')
    leagues = cursor.fetchall()
    for league in leagues:
        print(f'ID: {league["id"]}, Name: {league["name"]}, League_ID: {league["league_id"]}')
    
    print('\n=== SERIES STATS WITH MISSING SERIES_ID ===')  
    cursor.execute('SELECT DISTINCT league_id, series_name FROM series_stats WHERE series_id IS NULL ORDER BY league_id, series_name LIMIT 10')
    missing = cursor.fetchall()
    for record in missing:
        print(f'League: {record["league_id"]}, Series: {record["series_name"]}')
    
    print('\n=== SERIES TABLE ===')
    cursor.execute('SELECT id, name, league_id FROM series ORDER BY league_id, name LIMIT 10')
    series = cursor.fetchall()
    for s in series:
        print(f'ID: {s["id"]}, Name: {s["name"]}, League_ID: {s["league_id"]}')
    
    print('\n=== SERIES_STATS COUNT BY LEAGUE ===')
    cursor.execute('''
        SELECT league_id, 
               COUNT(*) as total_records,
               COUNT(series_id) as with_series_id,
               COUNT(*) - COUNT(series_id) as missing_series_id
        FROM series_stats 
        GROUP BY league_id 
        ORDER BY league_id
    ''')
    stats = cursor.fetchall()
    for stat in stats:
        print(f'League {stat["league_id"]}: {stat["total_records"]} total, {stat["with_series_id"]} with series_id, {stat["missing_series_id"]} missing')
    
    conn.close()

if __name__ == '__main__':
    main() 