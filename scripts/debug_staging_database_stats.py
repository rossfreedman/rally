#!/usr/bin/env python3
"""
Comprehensive Staging Database Statistics

This script provides detailed statistics about the Rally staging database,
including record counts, data distribution, date ranges, and data quality metrics.
"""

import os
import sys
from datetime import datetime

# Add the parent directory to the path to import database utilities
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one

def get_table_statistics():
    """Get basic record counts for all major tables"""
    tables = [
        'users', 'players', 'teams', 'leagues', 'clubs', 'series',
        'match_scores', 'schedule', 'series_stats', 'player_availability',
        'user_player_associations'
    ]
    
    stats = {}
    for table in tables:
        try:
            result = execute_query_one(f"SELECT COUNT(*) as count FROM {table}")
            stats[table] = result['count'] if result else 0
        except Exception as e:
            stats[table] = f"Error: {str(e)}"
    
    return stats

def get_league_distribution():
    """Get data distribution by league"""
    try:
        league_stats = execute_query("""
            SELECT 
                l.id,
                l.league_name as name,
                l.league_id as abbreviation,
                COUNT(DISTINCT p.id) as player_count,
                COUNT(DISTINCT t.id) as team_count,
                COUNT(DISTINCT ms.id) as match_count
            FROM leagues l
            LEFT JOIN players p ON l.id = p.league_id
            LEFT JOIN teams t ON l.id = t.league_id
            LEFT JOIN match_scores ms ON l.id = ms.league_id
            GROUP BY l.id, l.league_name, l.league_id
            ORDER BY l.league_name
        """)
        return league_stats
    except Exception as e:
        return [{"error": str(e)}]

def get_date_ranges():
    """Get date ranges for time-sensitive data"""
    try:
        # Match scores date range
        match_dates = execute_query_one("""
            SELECT 
                MIN(match_date) as earliest_match,
                MAX(match_date) as latest_match,
                COUNT(DISTINCT match_date) as unique_match_dates
            FROM match_scores
            WHERE match_date IS NOT NULL
        """)
        
        # Schedule date range
        schedule_dates = execute_query_one("""
            SELECT 
                MIN(match_date) as earliest_schedule,
                MAX(match_date) as latest_schedule,
                COUNT(DISTINCT match_date) as unique_schedule_dates
            FROM schedule
            WHERE match_date IS NOT NULL
        """)
        
        # Availability date range
        availability_dates = execute_query_one("""
            SELECT 
                MIN(match_date) as earliest_availability,
                MAX(match_date) as latest_availability,
                COUNT(DISTINCT match_date) as unique_availability_dates
            FROM player_availability
            WHERE match_date IS NOT NULL
        """)
        
        return {
            "matches": match_dates,
            "schedules": schedule_dates,
            "availability": availability_dates
        }
    except Exception as e:
        return {"error": str(e)}

def get_user_statistics():
    """Get user and authentication statistics"""
    try:
        user_stats = execute_query_one("""
            SELECT 
                COUNT(*) as total_users,
                COUNT(CASE WHEN tenniscores_player_id IS NOT NULL THEN 1 END) as users_with_player_id,
                COUNT(CASE WHEN league_context IS NOT NULL THEN 1 END) as users_with_league_context,
                COUNT(DISTINCT league_context) as unique_league_contexts
            FROM users
        """)
        
        # User-player associations
        association_stats = execute_query_one("""
            SELECT 
                COUNT(*) as total_associations,
                COUNT(DISTINCT user_id) as users_with_associations,
                COUNT(DISTINCT tenniscores_player_id) as players_with_associations
            FROM user_player_associations
        """)
        
        # League distribution of users
        user_league_dist = execute_query("""
            SELECT 
                league_context,
                COUNT(*) as user_count
            FROM users
            WHERE league_context IS NOT NULL
            GROUP BY league_context
            ORDER BY user_count DESC
        """)
        
        return {
            "user_stats": user_stats,
            "associations": association_stats,
            "league_distribution": user_league_dist
        }
    except Exception as e:
        return {"error": str(e)}

def get_match_statistics():
    """Get detailed match statistics"""
    try:
        # Basic match stats
        match_stats = execute_query_one("""
            SELECT 
                COUNT(*) as total_matches,
                COUNT(CASE WHEN winner IS NOT NULL THEN 1 END) as matches_with_winner,
                COUNT(CASE WHEN scores IS NOT NULL AND scores != '' THEN 1 END) as matches_with_scores,
                COUNT(CASE WHEN home_player_1_id IS NOT NULL THEN 1 END) as matches_with_home_p1,
                COUNT(CASE WHEN home_player_2_id IS NOT NULL THEN 1 END) as matches_with_home_p2,
                COUNT(CASE WHEN away_player_1_id IS NOT NULL THEN 1 END) as matches_with_away_p1,
                COUNT(CASE WHEN away_player_2_id IS NOT NULL THEN 1 END) as matches_with_away_p2
            FROM match_scores
        """)
        
        # Matches by season (estimated)
        matches_by_year = execute_query("""
            SELECT 
                EXTRACT(YEAR FROM match_date) as year,
                COUNT(*) as match_count
            FROM match_scores
            WHERE match_date IS NOT NULL
            GROUP BY EXTRACT(YEAR FROM match_date)
            ORDER BY year DESC
        """)
        
        # Recent matches sample
        recent_matches = execute_query("""
            SELECT 
                TO_CHAR(match_date, 'YYYY-MM-DD') as date,
                home_team,
                away_team,
                league_id,
                CASE WHEN winner IS NOT NULL THEN 'Yes' ELSE 'No' END as has_winner
            FROM match_scores
            ORDER BY match_date DESC
            LIMIT 5
        """)
        
        return {
            "match_stats": match_stats,
            "by_year": matches_by_year,
            "recent_sample": recent_matches
        }
    except Exception as e:
        return {"error": str(e)}

def get_team_statistics():
    """Get team and club statistics"""
    try:
        team_stats = execute_query("""
            SELECT 
                l.league_name as league_name,
                COUNT(DISTINCT t.id) as team_count,
                COUNT(DISTINCT s.id) as series_count
            FROM leagues l
            LEFT JOIN teams t ON l.id = t.league_id
            LEFT JOIN series s ON l.id = s.league_id
            GROUP BY l.id, l.league_name
            ORDER BY l.league_name
        """)
        
        # Top clubs by team count
        top_clubs = execute_query("""
            SELECT 
                c.name as club_name,
                COUNT(t.id) as team_count
            FROM clubs c
            LEFT JOIN teams t ON c.id = t.club_id
            GROUP BY c.id, c.name
            HAVING COUNT(t.id) > 0
            ORDER BY team_count DESC
            LIMIT 10
        """)
        
        return {
            "by_league": team_stats,
            "top_clubs": top_clubs
        }
    except Exception as e:
        return {"error": str(e)}

def get_data_quality_metrics():
    """Check for data quality issues"""
    try:
        # Orphaned records check
        orphaned_checks = {}
        
        # Check for orphaned match_scores
        try:
            orphaned_matches = execute_query_one("""
                SELECT COUNT(*) as count
                FROM match_scores ms
                LEFT JOIN teams ht ON ms.home_team_id = ht.id
                LEFT JOIN teams at ON ms.away_team_id = at.id
                WHERE ht.id IS NULL OR at.id IS NULL
            """)
            orphaned_checks['orphaned_match_team_refs'] = orphaned_matches['count'] if orphaned_matches else 0
        except Exception as e:
            orphaned_checks['orphaned_match_team_refs'] = f"Error: {str(e)}"
        
        # Check for null player IDs in matches
        try:
            null_player_ids = execute_query_one("""
                SELECT 
                    COUNT(CASE WHEN home_player_1_id IS NULL THEN 1 END) as null_home_p1,
                    COUNT(CASE WHEN home_player_2_id IS NULL THEN 1 END) as null_home_p2,
                    COUNT(CASE WHEN away_player_1_id IS NULL THEN 1 END) as null_away_p1,
                    COUNT(CASE WHEN away_player_2_id IS NULL THEN 1 END) as null_away_p2
                FROM match_scores
            """)
        except Exception as e:
            null_player_ids = {"error": str(e)}
        
        # Check for duplicate players
        try:
            duplicate_players = execute_query_one("""
                SELECT COUNT(*) as potential_duplicates
                FROM (
                    SELECT first_name, last_name, league_id, COUNT(*) as count
                    FROM players
                    GROUP BY first_name, last_name, league_id
                    HAVING COUNT(*) > 1
                ) dups
            """)
        except Exception as e:
            duplicate_players = {"error": str(e)}
        
        return {
            "orphaned_checks": orphaned_checks,
            "null_player_ids": null_player_ids,
            "potential_duplicate_players": duplicate_players.get('count', 0) if isinstance(duplicate_players, dict) and 'error' not in duplicate_players else f"Error: {duplicate_players.get('error', 'Unknown')}"
        }
    except Exception as e:
        return {"error": str(e)}

def print_statistics():
    """Print comprehensive database statistics"""
    print("=" * 80)
    print("RALLY STAGING DATABASE COMPREHENSIVE STATISTICS")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Table record counts
    print("📊 TABLE RECORD COUNTS")
    print("-" * 40)
    table_stats = get_table_statistics()
    for table, count in table_stats.items():
        print(f"{table:25} {count:>10}")
    print()
    
    # League distribution
    print("🏆 LEAGUE DISTRIBUTION")
    print("-" * 40)
    league_dist = get_league_distribution()
    if isinstance(league_dist, list) and len(league_dist) > 0 and 'error' not in league_dist[0]:
        for league in league_dist:
            print(f"{league['name']:15} | Players: {league['player_count']:4} | Teams: {league['team_count']:3} | Matches: {league['match_count']:5}")
    else:
        print(f"Error getting league distribution: {league_dist}")
    print()
    
    # Date ranges
    print("📅 DATE RANGES")
    print("-" * 40)
    date_ranges = get_date_ranges()
    if 'error' not in date_ranges:
        for data_type, dates in date_ranges.items():
            if dates and isinstance(dates, dict):
                earliest = dates.get('earliest_match', dates.get('earliest_schedule', dates.get('earliest_availability')))
                latest = dates.get('latest_match', dates.get('latest_schedule', dates.get('latest_availability')))
                unique_dates = dates.get('unique_match_dates', dates.get('unique_schedule_dates', dates.get('unique_availability_dates')))
                print(f"{data_type.title():12} | {earliest} to {latest} | {unique_dates} unique dates")
    else:
        print(f"Error getting date ranges: {date_ranges}")
    print()
    
    # User statistics
    print("👥 USER STATISTICS")
    print("-" * 40)
    user_stats = get_user_statistics()
    if 'error' not in user_stats:
        us = user_stats.get('user_stats', {})
        assoc = user_stats.get('associations', {})
        print(f"Total Users:              {us.get('total_users', 'N/A')}")
        print(f"With Player ID:           {us.get('users_with_player_id', 'N/A')}")
        print(f"With League Context:      {us.get('users_with_league_context', 'N/A')}")
        print(f"Total Associations:       {assoc.get('total_associations', 'N/A')}")
        print(f"Users with Associations:  {assoc.get('users_with_associations', 'N/A')}")
        print()
        print("League Distribution of Users:")
        for league in user_stats.get('league_distribution', []):
            print(f"  {league['league_context']:10} {league['user_count']:3} users")
    else:
        print(f"Error getting user statistics: {user_stats}")
    print()
    
    # Match statistics
    print("⚾ MATCH STATISTICS")
    print("-" * 40)
    match_stats = get_match_statistics()
    if 'error' not in match_stats:
        ms = match_stats.get('match_stats', {})
        print(f"Total Matches:            {ms.get('total_matches', 'N/A')}")
        print(f"With Winner:              {ms.get('matches_with_winner', 'N/A')}")
        print(f"With Scores:              {ms.get('matches_with_scores', 'N/A')}")
        print(f"With Home Player 1:       {ms.get('matches_with_home_p1', 'N/A')}")
        print(f"With Home Player 2:       {ms.get('matches_with_home_p2', 'N/A')}")
        print(f"With Away Player 1:       {ms.get('matches_with_away_p1', 'N/A')}")
        print(f"With Away Player 2:       {ms.get('matches_with_away_p2', 'N/A')}")
        print()
        print("Matches by Year:")
        for year_data in match_stats.get('by_year', []):
            print(f"  {year_data['year']}:  {year_data['match_count']:5} matches")
        print()
        print("Recent Matches Sample:")
        for match in match_stats.get('recent_sample', []):
            print(f"  {match['date']} | {match['home_team']} vs {match['away_team']} | League {match['league_id']} | Winner: {match['has_winner']}")
    else:
        print(f"Error getting match statistics: {match_stats}")
    print()
    
    # Team statistics
    print("🏓 TEAM & CLUB STATISTICS")
    print("-" * 40)
    team_stats = get_team_statistics()
    if 'error' not in team_stats:
        print("By League:")
        for league in team_stats.get('by_league', []):
            print(f"  {league['league_name']:15} | Teams: {league['team_count']:3} | Series: {league['series_count']:3}")
        print()
        print("Top Clubs by Team Count:")
        for club in team_stats.get('top_clubs', []):
            print(f"  {club['club_name']:20} | {club['team_count']:2} teams")
    else:
        print(f"Error getting team statistics: {team_stats}")
    print()
    
    # Data quality
    print("🔍 DATA QUALITY METRICS")
    print("-" * 40)
    quality_stats = get_data_quality_metrics()
    if 'error' not in quality_stats:
        print(f"Orphaned Match Team Refs: {quality_stats.get('orphaned_checks', {}).get('orphaned_match_team_refs', 'N/A')}")
        print(f"Potential Duplicate Players: {quality_stats.get('potential_duplicate_players', 'N/A')}")
        null_ids = quality_stats.get('null_player_ids', {})
        print(f"Null Player IDs in Matches:")
        print(f"  Home Player 1: {null_ids.get('null_home_p1', 'N/A')}")
        print(f"  Home Player 2: {null_ids.get('null_home_p2', 'N/A')}")
        print(f"  Away Player 1: {null_ids.get('null_away_p1', 'N/A')}")
        print(f"  Away Player 2: {null_ids.get('null_away_p2', 'N/A')}")
    else:
        print(f"Error getting data quality metrics: {quality_stats}")
    
    print("=" * 80)

if __name__ == "__main__":
    print_statistics() 