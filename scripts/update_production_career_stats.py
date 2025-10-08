#!/usr/bin/env python3
"""
Script to update career stats in production database from players_career_stats.json.
This script connects directly to the production database and updates career stats.

Usage:
    python3 scripts/update_production_career_stats.py

This script:
1. Loads career stats from data/leagues/APTA_CHICAGO/players_career_stats.json
2. Connects to the production database
3. Updates career stats for all players
4. Shows progress and summary
"""

import os
import sys
import json
from datetime import datetime

# Production database URL (hardcoded for this script)
PRODUCTION_DB_URL = 'postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway'

def get_db_connection():
    """Get direct database connection to production"""
    try:
        import psycopg2
        from urllib.parse import urlparse
        
        parsed = urlparse(PRODUCTION_DB_URL)
        
        conn = psycopg2.connect(
            dbname=parsed.path[1:],
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname,
            port=parsed.port or 5432,
            sslmode='require',
            connect_timeout=30
        )
        
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to production database: {e}")
        sys.exit(1)

def parse_percentage(pct_string):
    """Parse percentage string like '54.2%' to float"""
    if not pct_string or pct_string == "N/A":
        return None
    try:
        return float(pct_string.replace("%", "").strip())
    except (ValueError, AttributeError):
        return None

def update_career_stats():
    """Update career stats for all players from the JSON file"""
    print("🔄 Updating Career Stats in PRODUCTION Database")
    print("=" * 60)
    print(f"⚠️  WARNING: This will update production database!")
    print(f"Database: {PRODUCTION_DB_URL.split('@')[1]}")
    print("=" * 60)
    
    # Load the career stats JSON file
    json_path = 'data/leagues/APTA_CHICAGO/players_career_stats.json'
    
    if not os.path.exists(json_path):
        print(f"❌ File not found: {json_path}")
        print(f"   Make sure you're running this from the project root directory")
        sys.exit(1)
    
    print(f"📂 Loading career stats from: {json_path}")
    
    with open(json_path, 'r') as f:
        career_stats_data = json.load(f)
    
    print(f"✅ Loaded {len(career_stats_data)} player records")
    
    # Ask for confirmation
    print("\n⚠️  Ready to update production database. Continue? (yes/no): ", end='')
    confirmation = input().strip().lower()
    
    if confirmation != 'yes':
        print("❌ Update cancelled by user")
        sys.exit(0)
    
    print("\n🚀 Starting update...\n")
    
    # Statistics
    stats = {
        'total': len(career_stats_data),
        'updated': 0,
        'skipped_no_player': 0,
        'skipped_no_career_stats': 0,
        'errors': 0
    }
    
    # Track Jeff Day specifically
    jeff_day_updated = False
    jeff_day_before = None
    jeff_day_after = None
    
    # Connect to production database
    conn = get_db_connection()
    print(f"✅ Connected to production database\n")
    
    try:
        cur = conn.cursor()
        
        for i, player_data in enumerate(career_stats_data):
            player_id = player_data.get("Player ID")
            career_wins = player_data.get("Career Wins")
            career_losses = player_data.get("Career Losses")
            career_win_pct_raw = player_data.get("Career Win %")
            
            if not player_id:
                stats['errors'] += 1
                continue
            
            # Skip if no career stats available
            if career_wins is None and career_losses is None:
                stats['skipped_no_career_stats'] += 1
                continue
            
            # Parse career stats
            try:
                career_wins_int = int(career_wins) if career_wins is not None else 0
                career_losses_int = int(career_losses) if career_losses is not None else 0
                career_matches = career_wins_int + career_losses_int
                career_win_pct = parse_percentage(career_win_pct_raw)
                
                # Calculate win percentage if not provided
                if career_win_pct is None and career_matches > 0:
                    career_win_pct = (career_wins_int / career_matches) * 100
                
            except (ValueError, TypeError) as e:
                print(f"⚠️  Error parsing career stats for {player_id}: {e}")
                stats['errors'] += 1
                continue
            
            # Check if player exists in database and get current stats
            check_query = """
                SELECT id, first_name, last_name, career_wins, career_losses, career_matches
                FROM players 
                WHERE tenniscores_player_id = %s
                LIMIT 1
            """
            
            cur.execute(check_query, [player_id])
            player_record = cur.fetchone()
            
            if not player_record:
                stats['skipped_no_player'] += 1
                continue
            
            # Store Jeff Day's before stats
            if player_id == 'nndz-WkMrK3didnhnUT09':
                jeff_day_before = {
                    'name': f"{player_record[1]} {player_record[2]}",
                    'wins': player_record[3],
                    'losses': player_record[4],
                    'matches': player_record[5]
                }
            
            # Update career stats
            update_query = """
                UPDATE players 
                SET career_wins = %s,
                    career_losses = %s,
                    career_matches = %s,
                    career_win_percentage = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE tenniscores_player_id = %s
            """
            
            try:
                cur.execute(update_query, [
                    career_wins_int,
                    career_losses_int,
                    career_matches,
                    career_win_pct,
                    player_id
                ])
                stats['updated'] += 1
                
                # Track Jeff Day update
                if player_id == 'nndz-WkMrK3didnhnUT09':
                    jeff_day_updated = True
                    jeff_day_after = {
                        'wins': career_wins_int,
                        'losses': career_losses_int,
                        'matches': career_matches,
                        'win_pct': career_win_pct
                    }
                
                # Show progress every 500 updates
                if stats['updated'] % 500 == 0:
                    print(f"📊 Progress: {stats['updated']:,} players updated...")
                
            except Exception as e:
                print(f"❌ Error updating {player_id}: {e}")
                stats['errors'] += 1
                continue
        
        # Commit all updates
        print("\n💾 Committing updates to production database...")
        conn.commit()
        print("✅ All updates committed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during update: {e}")
        print("🔄 Rolling back changes...")
        conn.rollback()
        sys.exit(1)
        
    finally:
        cur.close()
        conn.close()
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 PRODUCTION UPDATE SUMMARY")
    print("=" * 60)
    print(f"Total records in JSON: {stats['total']:,}")
    print(f"Successfully updated: {stats['updated']:,}")
    print(f"Skipped (no player in DB): {stats['skipped_no_player']:,}")
    print(f"Skipped (no career stats): {stats['skipped_no_career_stats']:,}")
    print(f"Errors: {stats['errors']:,}")
    print("=" * 60)
    
    # Show Jeff Day details
    if jeff_day_updated and jeff_day_before and jeff_day_after:
        print(f"\n✨ Jeff Day Update Details:")
        print(f"   Name: {jeff_day_before['name']}")
        print(f"   Before: {jeff_day_before['wins']} wins, {jeff_day_before['losses']} losses, {jeff_day_before['matches']} matches")
        print(f"   After:  {jeff_day_after['wins']} wins, {jeff_day_after['losses']} losses, {jeff_day_after['matches']} matches")
        print(f"   Career Win %: {jeff_day_after['win_pct']:.2f}%")
    
    print(f"\n🎉 Production career stats update completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"✅ {stats['updated']:,} players in production now have correct career stats!")
    print(f"\n💡 The production site should now display correct career statistics.")

if __name__ == "__main__":
    # Check if running with proper imports
    try:
        import psycopg2
    except ImportError:
        print("❌ Error: psycopg2 is not installed")
        print("   Install it with: pip install psycopg2-binary")
        sys.exit(1)
    
    update_career_stats()

