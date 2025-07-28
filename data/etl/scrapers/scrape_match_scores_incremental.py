#!/usr/bin/env python3
"""
Incremental TennisScores Match Scraper

This enhanced scraper implements incremental scraping by:
1. Loading existing match data from data/leagues/all/match_history.json
2. Finding the most recent match date in the existing data
3. Scraping only new matches that are more recent than the existing data
4. Appending new matches to the existing data

This significantly improves efficiency by avoiding re-scraping of existing data.
"""

import json
import os
import re
import time
import random
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

print("🎾 Incremental TennisScores Match Scraper")
print("=" * 80)
print("✅ Only scrapes NEW data based on most recent date in existing JSON")
print("✅ Appends new matches to existing data")
print("✅ Significantly faster than full re-scraping")
print("=" * 80)


def get_consolidated_match_history_path():
    """Get the path to the consolidated match history file"""
    script_dir = os.path.dirname(os.path.abspath(__file__))  # data/etl/scrapers/
    etl_dir = os.path.dirname(script_dir)  # data/etl/
    project_root = os.path.dirname(os.path.dirname(etl_dir))  # rally/
    
    return os.path.join(project_root, "data", "leagues", "all", "match_history.json")


def load_existing_match_data():
    """
    Load existing match data from the consolidated JSON file.
    
    Returns:
        tuple: (matches_list, most_recent_date) or (None, None) if file doesn't exist
    """
    json_path = get_consolidated_match_history_path()
    
    if not os.path.exists(json_path):
        print(f"📄 No existing match history found at: {json_path}")
        print("🔄 Will perform full scraping for all data")
        return None, None
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            matches = json.load(f)
        
        if not matches:
            print("📄 Existing match history is empty")
            return [], None
        
        print(f"📄 Loaded {len(matches):,} existing matches from: {json_path}")
        
        # Find the most recent date
        most_recent_date = None
        date_formats = [
            "%d-%b-%y",  # 09-Jan-25
            "%m/%d/%Y",  # 01/15/2025
            "%Y-%m-%d",  # 2025-01-15
        ]
        
        for match in matches:
            date_str = match.get("Date", "")
            if not date_str:
                continue
                
            for date_format in date_formats:
                try:
                    parsed_date = datetime.strptime(date_str, date_format).date()
                    if most_recent_date is None or parsed_date > most_recent_date:
                        most_recent_date = parsed_date
                    break
                except ValueError:
                    continue
        
        if most_recent_date:
            print(f"📅 Most recent match date in existing data: {most_recent_date}")
        else:
            print("⚠️ Could not determine most recent date from existing data")
        
        return matches, most_recent_date
        
    except Exception as e:
        print(f"❌ Error loading existing match data: {e}")
        return None, None


def get_league_data_path(league_subdomain):
    """Get the path to league-specific data directory"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    etl_dir = os.path.dirname(script_dir)
    project_root = os.path.dirname(os.path.dirname(etl_dir))
    
    # Map subdomain to league ID
    league_mappings = {
        "aptachicago": "APTA_CHICAGO",
        "nstf": "NSTF", 
        "cita": "CITA",
        "cnswpl": "CNSWPL"
    }
    league_id = league_mappings.get(league_subdomain.lower(), league_subdomain.upper())
    
    return os.path.join(project_root, "data", "leagues", league_id, "match_history.json")


def filter_matches_by_date(matches, cutoff_date):
    """
    Filter matches to only include those newer than the cutoff date.
    
    Args:
        matches (list): List of match dictionaries
        cutoff_date (datetime.date): Cutoff date (exclusive)
        
    Returns:
        list: Filtered matches newer than cutoff date
    """
    if cutoff_date is None:
        return matches
    
    filtered_matches = []
    date_formats = [
        "%d-%b-%y",  # 09-Jan-25
        "%m/%d/%Y",  # 1/15/2025
        "%Y-%m-%d",  # 2025-01-15
    ]
    
    for match in matches:
        date_str = match.get("Date", "")
        if not date_str:
            continue
        
        match_date = None
        for date_format in date_formats:
            try:
                match_date = datetime.strptime(date_str, date_format).date()
                break
            except ValueError:
                continue
        
        if match_date and match_date > cutoff_date:
            filtered_matches.append(match)
    
    print(f"📊 Filtered {len(matches)} matches to {len(filtered_matches)} newer than {cutoff_date}")
    return filtered_matches


def save_incremental_data(existing_matches, new_matches, league_id):
    """
    Save incremental data by appending new matches to existing data.
    
    Args:
        existing_matches (list): Existing matches from JSON
        new_matches (list): New matches to append
        league_id (str): League identifier for logging
    """
    if not new_matches:
        print(f"📊 No new matches found for {league_id}")
        return
    
    json_path = get_consolidated_match_history_path()
    
    # Combine existing and new matches
    if existing_matches is None:
        existing_matches = []
    
    combined_matches = existing_matches + new_matches
    
    # Deduplicate based on match_id and date
    unique_matches = []
    seen_matches = set()
    
    for match in combined_matches:
        match_id = match.get("match_id", "")
        date = match.get("Date", "")
        home_team = match.get("Home Team", "")
        away_team = match.get("Away Team", "")
        
        # Create a unique key for deduplication
        match_key = f"{match_id}_{date}_{home_team}_{away_team}"
        
        if match_key not in seen_matches:
            unique_matches.append(match)
            seen_matches.add(match_key)
    
    # Save the combined data
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(unique_matches, f, indent=2)
        
        print(f"💾 Incremental data saved: {len(new_matches)} new matches added")
        print(f"📊 Total matches in file: {len(unique_matches):,}")
        print(f"🔍 Deduplication: {len(combined_matches) - len(unique_matches)} duplicates removed")
        
    except Exception as e:
        print(f"❌ Error saving incremental data: {e}")


def run_original_scraper(league_subdomain, series_filter=None):
    """
    Run the original scraper by calling it as a subprocess.
    
    Args:
        league_subdomain (str): League subdomain
        series_filter (str): Series filter
        
    Returns:
        list: List of scraped matches
    """
    # Build the command to run the original scraper
    original_scraper_path = os.path.join(os.path.dirname(__file__), "scraper_match_scores.py")
    
    if not os.path.exists(original_scraper_path):
        print(f"❌ Original scraper not found at: {original_scraper_path}")
        return []
    
    # Build command arguments
    cmd = [sys.executable, original_scraper_path, league_subdomain]
    
    print(f"🔄 Running original scraper: {' '.join(cmd)}")
    
    try:
        # Run the original scraper
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)  # 1 hour timeout
        
        if result.returncode == 0:
            print("✅ Original scraper completed successfully")
            
            # Load the scraped data from the league-specific directory
            league_data_path = get_league_data_path(league_subdomain)
            
            if os.path.exists(league_data_path):
                with open(league_data_path, 'r', encoding='utf-8') as f:
                    matches = json.load(f)
                print(f"📊 Loaded {len(matches)} matches from original scraper")
                return matches
            else:
                print(f"❌ No match file found at: {league_data_path}")
                return []
        else:
            print(f"❌ Original scraper failed: {result.stderr}")
            return []
            
    except subprocess.TimeoutExpired:
        print("❌ Original scraper timed out")
        return []
    except Exception as e:
        print(f"❌ Error running original scraper: {e}")
        return []


def scrape_incremental_matches(league_subdomain, series_filter=None):
    """
    Scrape matches incrementally, only getting new data.
    
    Args:
        league_subdomain (str): League subdomain (e.g., 'aptachicago', 'nstf')
        series_filter (str, optional): Specific series to scrape
    
    Returns:
        list: List of new matches scraped
    """
    print(f"🎾 Starting incremental match scraping for {league_subdomain}")
    print("=" * 60)
    
    # Step 1: Load existing data
    existing_matches, existing_date = load_existing_match_data()
    
    # Step 2: Run the original scraper to get all matches
    print("🔄 Running original scraper to get all matches...")
    all_matches = run_original_scraper(league_subdomain, series_filter)
    
    if not all_matches:
        print("❌ No matches found by original scraper")
        return []
    
    # Step 3: Filter matches to only include new ones
    new_matches = filter_matches_by_date(all_matches, existing_date)
    
    # Step 4: Save incremental data
    league_mappings = {
        "aptachicago": "APTA_CHICAGO",
        "nstf": "NSTF", 
        "cita": "CITA",
        "cnswpl": "CNSWPL"
    }
    league_id = league_mappings.get(league_subdomain.lower(), league_subdomain.upper())
    save_incremental_data(existing_matches, new_matches, league_id)
    
    return new_matches


def main():
    """Main function for incremental scraping"""
    print("🔍 Incremental TennisScores Match Scraper")
    print("=" * 60)
    
    # Get league input
    if len(sys.argv) > 1:
        league_subdomain = sys.argv[1].strip().lower()
        print(f"📋 Using league from command line: {league_subdomain}")
    else:
        print("Available league options:")
        print("  • aptachicago - APTA Chicago league")
        print("  • nstf - NSTF league")
        print("  • cita - CITA league")
        print("  • cnswpl - CNSWPL league")
        print("  • all - Process all known leagues")
        print()
        league_subdomain = input("Enter league subdomain (e.g., 'aptachicago', 'nstf', 'all'): ").strip().lower()
    
    league_subdomain = league_subdomain.strip('"').strip("'")
    
    if not league_subdomain:
        print("❌ No league subdomain provided. Exiting.")
        exit(1)
    
    # Get series filter
    series_filter = None
    if league_subdomain != "all":
        print()
        print("Series filtering options:")
        print("  • Enter a single number (e.g., '22') to scrape only series containing that number")
        print("  • Enter multiple numbers separated by commas (e.g., '19,22,24SW') to scrape specific series")
        print("  • Enter 'all' to scrape all series for the selected league")
        print()
        series_input = input("Enter series filter (number, comma-separated numbers, or 'all'): ").strip()
        
        if series_input and series_input.lower() != "all":
            series_filter = series_input
            print(f"🎯 Will filter for series containing: '{series_filter}'")
        else:
            series_filter = "all"
            print("🌟 Will process all series for the selected league")
    
    # Handle 'all' option
    if league_subdomain == "all":
        known_leagues = ["aptachicago", "nstf", "cita", "cnswpl"]
        print(f"🌟 Processing all known leagues incrementally: {', '.join(known_leagues)}")
        
        total_new_matches = 0
        for league in known_leagues:
            print(f"\n{'='*60}")
            print(f"🏆 PROCESSING LEAGUE: {league.upper()}")
            print(f"{'='*60}")
            
            try:
                new_matches = scrape_incremental_matches(league, "all")
                total_new_matches += len(new_matches)
                print(f"✅ Successfully completed {league} - {len(new_matches)} new matches")
            except Exception as e:
                print(f"❌ Error processing {league}: {str(e)}")
                continue
        
        print(f"\n🎉 All leagues processing complete!")
        print(f"📊 Total new matches found: {total_new_matches}")
    else:
        # Process single league
        new_matches = scrape_incremental_matches(league_subdomain, series_filter)
        print(f"\n🎉 Incremental scraping complete!")
        print(f"📊 New matches found: {len(new_matches)}")


if __name__ == "__main__":
    main() 