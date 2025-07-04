#!/usr/bin/env python3
"""
Populate series_id in series_stats table
========================================

This script populates the new series_id foreign key column in series_stats
by matching existing series names to the series table.

Usage: python scripts/populate_series_id_in_series_stats.py
"""

import sys
import os
from datetime import datetime

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from database_utils import execute_query, execute_query_one, execute_update


def log(message, level="INFO"):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")


def get_series_stats_without_series_id():
    """Get all series_stats records that don't have series_id populated"""
    query = """
        SELECT id, series, team, league_id 
        FROM series_stats 
        WHERE series_id IS NULL
        ORDER BY league_id, series, team
    """
    return execute_query(query)


def find_series_id_by_name(series_name, league_id):
    """Find series ID by name, trying multiple matching strategies"""
    
    # Strategy 1: Exact match
    query = """
        SELECT s.id, s.name
        FROM series s
        JOIN series_leagues sl ON s.id = sl.series_id
        WHERE s.name = %s AND sl.league_id = %s
    """
    result = execute_query_one(query, [series_name, league_id])
    if result:
        return result["id"], "exact_match"
    
    # Strategy 2: Case-insensitive match
    query = """
        SELECT s.id, s.name
        FROM series s
        JOIN series_leagues sl ON s.id = sl.series_id
        WHERE LOWER(s.name) = LOWER(%s) AND sl.league_id = %s
    """
    result = execute_query_one(query, [series_name, league_id])
    if result:
        return result["id"], "case_insensitive_match"
    
    # Strategy 3: Try common format conversions
    conversions = [
        ("Division ", "Series "),  # Division 3 -> Series 3
        ("Series ", "Division "),  # Series 3 -> Division 3
        ("Chicago ", "Series "),   # Chicago 8 -> Series 8
        ("Series ", "Chicago "),   # Series 8 -> Chicago 8
    ]
    
    for old_prefix, new_prefix in conversions:
        if series_name.startswith(old_prefix):
            converted_name = series_name.replace(old_prefix, new_prefix, 1)
            query = """
                SELECT s.id, s.name
                FROM series s
                JOIN series_leagues sl ON s.id = sl.series_id
                WHERE s.name = %s AND sl.league_id = %s
            """
            result = execute_query_one(query, [converted_name, league_id])
            if result:
                return result["id"], f"converted_match ({old_prefix} -> {new_prefix})"
    
    # Strategy 4: Extract number and try different formats
    import re
    number_match = re.search(r'(\d+)', series_name)
    if number_match:
        series_number = number_match.group(1)
        possible_formats = [
            f"Series {series_number}",
            f"Division {series_number}",
            f"Chicago {series_number}",
            f"S{series_number}",
            f"D{series_number}",
        ]
        
        for format_name in possible_formats:
            query = """
                SELECT s.id, s.name
                FROM series s
                JOIN series_leagues sl ON s.id = sl.series_id
                WHERE s.name = %s AND sl.league_id = %s
            """
            result = execute_query_one(query, [format_name, league_id])
            if result:
                return result["id"], f"number_format_match ({format_name})"
    
    return None, "no_match"


def populate_series_id():
    """Populate series_id for all series_stats records"""
    log("🔄 Starting series_id population in series_stats table...")
    
    # Get all records without series_id
    records = get_series_stats_without_series_id()
    log(f"📊 Found {len(records)} records without series_id")
    
    if not records:
        log("✅ All records already have series_id populated!")
        return
    
    updated_count = 0
    failed_count = 0
    match_strategies = {}
    
    for record in records:
        series_stats_id = record["id"]
        series_name = record["series"]
        team_name = record["team"]
        league_id = record["league_id"]
        
        # Find the series ID
        series_id, match_strategy = find_series_id_by_name(series_name, league_id)
        
        if series_id:
            # Update the record
            update_query = """
                UPDATE series_stats 
                SET series_id = %s 
                WHERE id = %s
            """
            execute_update(update_query, [series_id, series_stats_id])
            updated_count += 1
            
            # Track match strategies
            if match_strategy not in match_strategies:
                match_strategies[match_strategy] = 0
            match_strategies[match_strategy] += 1
            
            log(f"✅ Updated {team_name} ({series_name}) -> series_id {series_id} via {match_strategy}")
        else:
            failed_count += 1
            log(f"❌ Failed to find series_id for {team_name} ({series_name}) in league {league_id}", "ERROR")
    
    # Summary
    log(f"\n📊 SUMMARY:")
    log(f"   Updated: {updated_count} records")
    log(f"   Failed: {failed_count} records")
    log(f"\n🎯 Match strategies used:")
    for strategy, count in match_strategies.items():
        log(f"   {strategy}: {count} records")
    
    if failed_count > 0:
        log(f"\n⚠️  {failed_count} records failed to match. Manual review may be needed.", "WARNING")
    else:
        log(f"\n🎉 All records successfully populated with series_id!")


def verify_population():
    """Verify that all records now have series_id populated"""
    log("\n🔍 Verifying series_id population...")
    
    # Check for any remaining NULL series_id values
    query = """
        SELECT COUNT(*) as null_count
        FROM series_stats 
        WHERE series_id IS NULL
    """
    result = execute_query_one(query)
    null_count = result["null_count"]
    
    if null_count == 0:
        log("✅ All series_stats records now have series_id populated!")
    else:
        log(f"❌ {null_count} records still have NULL series_id", "ERROR")
    
    # Show sample of populated records
    query = """
        SELECT ss.series, ss.team, s.name as series_name, ss.series_id
        FROM series_stats ss
        JOIN series s ON ss.series_id = s.id
        LIMIT 5
    """
    samples = execute_query(query)
    log(f"\n📋 Sample of populated records:")
    for sample in samples:
        log(f"   {sample['team']} ({sample['series']}) -> {sample['series_name']} (ID: {sample['series_id']})")


if __name__ == "__main__":
    try:
        populate_series_id()
        verify_population()
    except Exception as e:
        log(f"❌ Error during series_id population: {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()
        sys.exit(1) 