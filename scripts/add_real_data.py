#!/usr/bin/env python3
"""
Script to populate the rally database with real clubs and series data
extracted from the actual match data files.
"""

import json
from database_utils import execute_query, execute_query_one

def get_real_series():
    """Extract real series names from series_stats.json"""
    with open('data/leagues/apta/series_stats.json', 'r') as f:
        data = json.load(f)
    
    series_names = set()
    for entry in data:
        series_names.add(entry['series'])
    
    return sorted(list(series_names))

def get_real_clubs():
    """Extract real club names from series_stats.json"""
    with open('data/leagues/apta/series_stats.json', 'r') as f:
        data = json.load(f)
    
    club_names = set()
    for entry in data:
        team_name = entry['team']
        # Remove the series number suffix (e.g., " - 6")
        club_name = team_name.rsplit(' - ', 1)[0]
        if club_name != 'BYE':  # Skip BYE entries
            club_names.add(club_name)
    
    return sorted(list(club_names))

def clear_test_data():
    """Remove the test data from clubs and series tables"""
    print("Clearing test data...")
    
    # Delete test clubs
    execute_query("DELETE FROM clubs WHERE name IN %s", (tuple([
        'Germantown Cricket Club', 'Philadelphia Cricket Club', 'Merion Cricket Club',
        'Waynesborough Country Club', 'Aronimink Golf Club', 'Overbrook Golf Club',
        'Radnor Valley Country Club', 'White Manor Country Club'
    ]),))
    
    # Delete test series
    execute_query("DELETE FROM series WHERE name IN %s", (tuple([
        'Series 1', 'Series 2', 'Series 3', 'Series 4',
        'Series 5', 'Series 6', 'Series 7', 'Series 8'
    ]),))
    
    print("Test data cleared!")

def add_real_data():
    """Add the real clubs and series to the database"""
    
    # Get real data
    real_series = get_real_series()
    real_clubs = get_real_clubs()
    
    print(f"Found {len(real_series)} real series:")
    for series in real_series:
        print(f"  - {series}")
    
    print(f"\nFound {len(real_clubs)} real clubs:")
    for club in real_clubs:
        print(f"  - {club}")
    
    # Add real series
    print("\nAdding real series...")
    for series_name in real_series:
        execute_query(
            "INSERT INTO series (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
            (series_name,)
        )
    
    # Add real clubs
    print("Adding real clubs...")
    for club_name in real_clubs:
        execute_query(
            "INSERT INTO clubs (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
            (club_name,)
        )
    
    print("\nReal data added successfully!")
    
    # Show final counts
    series_count = execute_query_one("SELECT COUNT(*) as count FROM series")['count']
    clubs_count = execute_query_one("SELECT COUNT(*) as count FROM clubs")['count']
    
    print(f"\nFinal counts:")
    print(f"  Series: {series_count}")
    print(f"  Clubs: {clubs_count}")

if __name__ == '__main__':
    print("=== Adding Real Clubs and Series ===")
    
    # Clear test data
    clear_test_data()
    
    # Add real data
    add_real_data()
    
    print("\nDone!") 