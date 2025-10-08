#!/usr/bin/env python3
"""
Script to update career stats in local, staging, or production database from players_career_stats.json.
This script connects directly to the database and updates career stats.

Usage:
    # Auto-detect environment (checks RAILWAY_ENVIRONMENT and DATABASE_URL):
    python3 scripts/update_production_career_stats.py
    
    # Or specify explicitly:
    python3 scripts/update_production_career_stats.py local
    python3 scripts/update_production_career_stats.py staging
    python3 scripts/update_production_career_stats.py production

This script:
1. Auto-detects environment or uses provided argument
2. Loads career stats from data/leagues/APTA_CHICAGO/players_career_stats.json
3. Connects to the specified database (local, staging, or production)
4. Updates career stats for all players
5. Shows progress and summary
"""

import os
import sys
import json
from datetime import datetime

# Database URLs
LOCAL_DB_URL = 'postgresql://localhost/rally'
STAGING_DB_URL = 'postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway'
PRODUCTION_DB_URL = 'postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway'

def get_db_connection(environment):
    """Get direct database connection to staging or production"""
    try:
        import psycopg2
        from urllib.parse import urlparse
        
        # Select database URL based on environment
        if environment == 'production':
            db_url = PRODUCTION_DB_URL
        elif environment == 'staging':
            db_url = STAGING_DB_URL
        else:  # local
            db_url = LOCAL_DB_URL
        
        parsed = urlparse(db_url)
        
        # Determine SSL mode based on environment
        sslmode = 'prefer' if environment == 'local' else 'require'
        
        conn = psycopg2.connect(
            dbname=parsed.path[1:],
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname,
            port=parsed.port or 5432,
            sslmode=sslmode,
            connect_timeout=30
        )
        
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to {environment} database: {e}")
        sys.exit(1)

def parse_percentage(pct_string):
    """Parse percentage string like '54.2%' to float"""
    if not pct_string or pct_string == "N/A":
        return None
    try:
        return float(pct_string.replace("%", "").strip())
    except (ValueError, AttributeError):
        return None

def update_career_stats(environment):
    """Update career stats for all players from the JSON file"""
    if environment == 'production':
        db_url = PRODUCTION_DB_URL
    elif environment == 'staging':
        db_url = STAGING_DB_URL
    else:  # local
        db_url = LOCAL_DB_URL
    
    # Get database name for display
    if environment == 'local':
        db_name = 'localhost/rally'
    else:
        db_name = db_url.split('@')[1]
    
    print(f"🔄 Updating Career Stats in {environment.upper()} Database")
    print("=" * 60)
    print(f"⚠️  WARNING: This will update {environment} database!")
    print(f"Database: {db_name}")
    print("=" * 60)
    
    # Load the career stats JSON file
    # Try multiple paths: current directory, project root, or full path
    possible_paths = [
        'players_career_stats.json',  # Current directory (for SSH runs)
        'data/leagues/APTA_CHICAGO/players_career_stats.json',  # Project root
        os.path.join(os.path.dirname(__file__), '..', 'data/leagues/APTA_CHICAGO/players_career_stats.json')  # Relative to script
    ]
    
    json_path = None
    for path in possible_paths:
        if os.path.exists(path):
            json_path = path
            break
    
    if not json_path:
        print(f"❌ File not found: players_career_stats.json")
        print(f"   Tried locations:")
        for path in possible_paths:
            print(f"     - {path}")
        print(f"   Make sure the JSON file is in one of these locations")
        sys.exit(1)
    
    print(f"📂 Loading career stats from: {json_path}")
    
    with open(json_path, 'r') as f:
        career_stats_data = json.load(f)
    
    print(f"✅ Loaded {len(career_stats_data)} player records")
    
    print(f"\n🚀 Starting update to {environment} database...\n")
    
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
    
    # Connect to database
    conn = get_db_connection(environment)
    print(f"✅ Connected to {environment} database\n")
    
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
        print(f"\n💾 Committing updates to {environment} database...")
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
    print(f"📊 {environment.upper()} UPDATE SUMMARY")
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
    
    print(f"\n🎉 {environment.title()} career stats update completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"✅ {stats['updated']:,} players in {environment} now have correct career stats!")
    print(f"\n💡 The {environment} site should now display correct career statistics.")

if __name__ == "__main__":
    # Check if running with proper imports
    try:
        import psycopg2
    except ImportError:
        print("❌ Error: psycopg2 is not installed")
        print("   Install it with: pip install psycopg2-binary")
        sys.exit(1)
    
    # Auto-detect environment or use provided argument
    if len(sys.argv) < 2:
        # Auto-detect based on DATABASE_URL or RAILWAY_ENVIRONMENT
        railway_env = os.environ.get('RAILWAY_ENVIRONMENT')
        database_url = os.environ.get('DATABASE_URL', '')
        
        if railway_env == 'production' or 'ballast.proxy.rlwy.net' in database_url:
            environment = 'production'
            print("🔍 Auto-detected environment: PRODUCTION")
        elif railway_env == 'staging' or 'switchback.proxy.rlwy.net' in database_url:
            environment = 'staging'
            print("🔍 Auto-detected environment: STAGING")
        else:
            environment = 'local'
            print("🔍 Auto-detected environment: LOCAL")
        
        print("")
        print("💡 You can also specify environment explicitly:")
        print("   python3 scripts/update_production_career_stats.py [local|staging|production]")
        print("")
    else:
        environment = sys.argv[1].lower()
    
    if environment not in ['local', 'staging', 'production']:
        print(f"❌ Error: Invalid environment '{sys.argv[1]}'")
        print("   Must be 'local', 'staging', or 'production'")
        sys.exit(1)
    
    update_career_stats(environment)

