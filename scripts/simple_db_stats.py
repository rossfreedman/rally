#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one

def main():
    print('=' * 60)
    print('RALLY STAGING DATABASE STATISTICS')
    print('=' * 60)
    print()

    # Basic table counts
    tables = ['users', 'players', 'teams', 'leagues', 'clubs', 'series', 
              'match_scores', 'schedule', 'series_stats', 'player_availability', 
              'user_player_associations']
    
    print('📊 RECORD COUNTS:')
    total_records = 0
    for table in tables:
        try:
            count = execute_query_one(f'SELECT COUNT(*) as count FROM {table}')['count']
            print(f'  {table:25} {count:>8,}')
            total_records += count
        except Exception as e:
            print(f'  {table:25} Error: {str(e)[:30]}...')
    
    print(f'  {"TOTAL RECORDS":25} {total_records:>8,}')
    print()

    # League info
    print('🏆 LEAGUES:')
    try:
        leagues = execute_query('SELECT id, league_name, league_id FROM leagues ORDER BY league_name')
        for league in leagues:
            # Get player and team counts for each league
            try:
                player_count = execute_query_one('SELECT COUNT(*) as count FROM players WHERE league_id = %s', [league['id']])['count']
                team_count = execute_query_one('SELECT COUNT(*) as count FROM teams WHERE league_id = %s', [league['id']])['count']
                print(f'  {league["league_name"]:20} | {player_count:>4} players | {team_count:>3} teams')
            except:
                print(f'  {league["league_name"]:20} | Error getting counts')
    except Exception as e:
        print(f'  Error: {e}')
    print()

    # Match date range
    print('📅 MATCH DATA:')
    try:
        match_range = execute_query_one('''
            SELECT 
                MIN(match_date) as earliest, 
                MAX(match_date) as latest, 
                COUNT(DISTINCT match_date) as unique_dates,
                COUNT(*) as total_matches
            FROM match_scores 
            WHERE match_date IS NOT NULL
        ''')
        print(f'  Date Range:     {match_range["earliest"]} to {match_range["latest"]}')
        print(f'  Total Matches:  {match_range["total_matches"]:,}')
        print(f'  Unique Dates:   {match_range["unique_dates"]:,}')
        
        # Matches by year
        matches_by_year = execute_query('''
            SELECT 
                EXTRACT(YEAR FROM match_date) as year,
                COUNT(*) as count
            FROM match_scores 
            WHERE match_date IS NOT NULL
            GROUP BY EXTRACT(YEAR FROM match_date)
            ORDER BY year DESC
        ''')
        print('  By Year:')
        for year_data in matches_by_year:
            print(f'    {int(year_data["year"])}: {year_data["count"]:,} matches')
            
    except Exception as e:
        print(f'  Error: {e}')
    print()

    # User statistics
    print('👥 USERS:')
    try:
        user_stats = execute_query_one('''
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN tenniscores_player_id IS NOT NULL THEN 1 END) as with_player_id,
                COUNT(CASE WHEN league_context IS NOT NULL THEN 1 END) as with_league_context
            FROM users
        ''')
        print(f'  Total Users:        {user_stats["total"]:,}')
        print(f'  With Player ID:     {user_stats["with_player_id"]:,}')
        print(f'  With League Context: {user_stats["with_league_context"]:,}')
        
        # League distribution
        league_dist = execute_query('''
            SELECT league_context, COUNT(*) as count 
            FROM users 
            WHERE league_context IS NOT NULL 
            GROUP BY league_context 
            ORDER BY count DESC
        ''')
        print('  League Distribution:')
        for dist in league_dist:
            print(f'    {dist["league_context"]:10}: {dist["count"]:2} users')
            
    except Exception as e:
        print(f'  Error: {e}')
    print()

    # Data completeness
    print('📈 DATA COMPLETENESS:')
    try:
        # Match completeness
        match_completeness = execute_query_one('''
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN winner IS NOT NULL THEN 1 END) as with_winner,
                COUNT(CASE WHEN scores IS NOT NULL AND scores != '' THEN 1 END) as with_scores,
                COUNT(CASE WHEN home_player_1_id IS NOT NULL THEN 1 END) as with_home_p1,
                COUNT(CASE WHEN away_player_1_id IS NOT NULL THEN 1 END) as with_away_p1
            FROM match_scores
        ''')
        total = match_completeness["total"]
        print(f'  Matches with Winner:    {match_completeness["with_winner"]:,} ({100*match_completeness["with_winner"]/total:.1f}%)')
        print(f'  Matches with Scores:    {match_completeness["with_scores"]:,} ({100*match_completeness["with_scores"]/total:.1f}%)')
        print(f'  Matches with Home P1:   {match_completeness["with_home_p1"]:,} ({100*match_completeness["with_home_p1"]/total:.1f}%)')
        print(f'  Matches with Away P1:   {match_completeness["with_away_p1"]:,} ({100*match_completeness["with_away_p1"]/total:.1f}%)')
        
    except Exception as e:
        print(f'  Error: {e}')
    print()

    print('✅ Statistics Complete!')

if __name__ == "__main__":
    main() 