#!/usr/bin/env python3
"""
Player Activity Analysis Script
==============================

Analyzes player data to understand:
1. What causes "Unknown" series classification
2. Active players (last 3 years)
3. Active series (last 3 years)
"""

from database_config import get_db
from datetime import datetime, timedelta

def main():
    # Calculate 3 years ago
    three_years_ago = datetime.now() - timedelta(days=3*365)
    print(f'🔍 Analyzing activity since: {three_years_ago.strftime("%Y-%m-%d")}')

    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Understand 'Unknown' players - check what series values exist
        print('\n📊 SERIES ANALYSIS:')
        cursor.execute('''
            SELECT 
                COALESCE(s.name, 'NO_SERIES') as series_name,
                COUNT(*) as player_count,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM players), 1) as percentage
            FROM players p
            LEFT JOIN series s ON p.series_id = s.id
            GROUP BY s.name
            ORDER BY player_count DESC
            LIMIT 15
        ''')
        
        series_results = cursor.fetchall()
        
        for series, count, pct in series_results:
            print(f'  {series}: {count:,} players ({pct}%)')
        
        # Check for NULL or empty series
        cursor.execute('SELECT COUNT(*) FROM players WHERE series_id IS NULL')
        null_series = cursor.fetchone()[0]
        print(f'\n🔍 Players with NULL series_id: {null_series:,}')
        
        # Check actual series values in database
        cursor.execute('SELECT COUNT(*) FROM series')
        total_series = cursor.fetchone()[0]
        print(f'🔍 Total series in database: {total_series:,}')
        
        # 2. Active players analysis (last 3 years)
        print(f'\n🎯 ACTIVE PLAYERS (since {three_years_ago.strftime("%Y-%m-%d")}):')
        cursor.execute('''
            SELECT COUNT(DISTINCT p.id) 
            FROM players p
            JOIN player_history ph ON p.id = ph.player_id
            WHERE ph.date >= %s
        ''', (three_years_ago.date(),))
        
        active_players = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM players')
        total_players = cursor.fetchone()[0]
        
        active_percentage = (active_players / total_players) * 100
        print(f'  Active players: {active_players:,} out of {total_players:,} ({active_percentage:.1f}%)')
        
        # 3. Active series analysis
        print(f'\n🎯 ACTIVE SERIES (since {three_years_ago.strftime("%Y-%m-%d")}):')
        cursor.execute('''
            SELECT 
                COALESCE(s.name, 'NO_SERIES') as series_name,
                COUNT(DISTINCT p.id) as active_players,
                MAX(ph.date) as latest_activity
            FROM players p
            LEFT JOIN series s ON p.series_id = s.id
            JOIN player_history ph ON p.id = ph.player_id
            WHERE ph.date >= %s
            GROUP BY s.name
            ORDER BY active_players DESC
        ''', (three_years_ago.date(),))
        
        active_series = cursor.fetchall()
        total_active_series = len(active_series)
        
        print(f'  Total active series: {total_active_series}')
        print(f'  Top active series:')
        for series, players, latest in active_series[:15]:
            print(f'    {series}: {players:,} active players (latest: {latest})')
        
        # 4. Player history date range analysis
        print('\n📅 PLAYER HISTORY DATE RANGE:')
        cursor.execute('''
            SELECT 
                MIN(date) as earliest_date,
                MAX(date) as latest_date,
                COUNT(*) as total_records
            FROM player_history
        ''')
        
        date_range = cursor.fetchone()
        print(f'  Date range: {date_range[0]} to {date_range[1]}')
        print(f'  Total history records: {date_range[2]:,}')
        
        # 5. Recent activity breakdown by year
        print('\n📈 ACTIVITY BY RECENT YEARS:')
        cursor.execute('''
            SELECT 
                EXTRACT(YEAR FROM ph.date) as year,
                COUNT(DISTINCT p.id) as unique_players,
                COUNT(*) as total_records
            FROM players p
            JOIN player_history ph ON p.id = ph.player_id
            WHERE ph.date >= %s
            GROUP BY EXTRACT(YEAR FROM ph.date)
            ORDER BY year DESC
        ''', (three_years_ago.date(),))
        
        yearly_activity = cursor.fetchall()
        for year, players, records in yearly_activity:
            print(f'  {int(year)}: {players:,} players, {records:,} records')
            
        # 6. Sample of "Unknown" classification investigation
        print('\n🔍 INVESTIGATING "UNKNOWN" PLAYERS:')
        cursor.execute('''
            SELECT 
                p.first_name,
                p.last_name,
                COALESCE(s.name, 'NULL') as series_name,
                l.league_id,
                c.name as club_name
            FROM players p
            LEFT JOIN series s ON p.series_id = s.id
            LEFT JOIN leagues l ON p.league_id = l.id  
            LEFT JOIN clubs c ON p.club_id = c.id
            WHERE s.name IS NULL
            ORDER BY p.id
            LIMIT 10
        ''')
        
        unknown_samples = cursor.fetchall()
        print(f'  Sample players with NULL series:')
        for fname, lname, series, league, club in unknown_samples:
            print(f'    {fname} {lname} | Series: {series} | League: {league} | Club: {club}')

if __name__ == '__main__':
    main() 