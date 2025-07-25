#!/usr/bin/env python3

"""
Quick Match Import - Direct import of all match scores to main database
"""

import json
import os
import sys
import time
from datetime import datetime

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
sys.path.insert(0, project_root)

from database_config import get_db

def load_match_data():
    """Load match data from consolidated JSON"""
    json_path = os.path.join(project_root, 'data', 'leagues', 'all', 'match_history.json')
    
    print(f"📂 Loading match data from: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Count records with match_id
    with_match_id = [r for r in data if r.get('match_id')]
    
    print(f"📊 Data loaded: {len(data)} total, {len(with_match_id)} with match_id")
    return data

def import_match_scores(match_data):
    """Import match scores with upsert logic"""
    print("📥 Importing match scores with upsert logic...")
    
    # Pre-cache lookup data
    print("🔧 Pre-caching league and team data...")
    
    league_cache = {}
    team_cache = {}
    player_cache = {}
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Cache leagues
        cursor.execute("SELECT id, league_id FROM leagues")
        for row in cursor.fetchall():
            league_cache[row[1]] = row[0]
        
        # Cache teams 
        cursor.execute("SELECT id, team_name, league_id FROM teams")
        for row in cursor.fetchall():
            key = f"{row[1]}_{row[2]}"
            team_cache[key] = row[0]
        
        # Cache players
        cursor.execute("SELECT tenniscores_player_id, first_name, last_name FROM players")
        for row in cursor.fetchall():
            player_cache[row[0]] = f"{row[1]} {row[2]}"
        
        print(f"✅ Cached {len(league_cache)} leagues, {len(team_cache)} teams, {len(player_cache)} players")
        
        # Process matches
        inserted_count = 0
        updated_count = 0
        error_count = 0
        
        for i, match in enumerate(match_data):
            if i % 1000 == 0 and i > 0:
                print(f"   📊 Processed {i} matches so far (inserted: {inserted_count}, updated: {updated_count})...")
            
            try:
                # Get match data
                match_date = match.get('Date', '')
                home_team = match.get('Home Team', '')
                away_team = match.get('Away Team', '')
                scores = match.get('Scores', '')
                winner = match.get('Winner', '').strip().lower()
                league_id = match.get('league_id', '')
                
                # Generate unique tenniscores_match_id by combining match_id + Line
                base_match_id = match.get('match_id', '').strip()
                line = match.get('Line', '').strip()
                
                # Create unique tenniscores_match_id
                if base_match_id and line:
                    # Extract line number (e.g., "Line 1" -> "Line1", "Line 2" -> "Line2")
                    line_number = line.replace(" ", "")  # "Line 1" -> "Line1"
                    tenniscores_match_id = f"{base_match_id}_{line_number}"
                else:
                    # Fallback: use original match_id if line info is missing
                    tenniscores_match_id = base_match_id
                
                # Handle invalid winner values - database only accepts 'home' or 'away'
                if winner not in ['home', 'away']:
                    if winner == 'unknown':
                        winner = None  # Set to NULL for unknown winners
                    else:
                        winner = None  # Set any other invalid winner to NULL
                
                # Convert date format
                if match_date:
                    try:
                        # Convert "11-Feb-25" to "2025-02-11"
                        dt = datetime.strptime(match_date, '%d-%b-%y')
                        match_date = dt.strftime('%Y-%m-%d')
                    except:
                        continue
                
                # Get league database ID
                league_db_id = league_cache.get(league_id)
                if not league_db_id:
                    continue
                
                # Get team IDs
                home_team_key = f"{home_team}_{league_db_id}"
                away_team_key = f"{away_team}_{league_db_id}"
                home_team_id = team_cache.get(home_team_key)
                away_team_id = team_cache.get(away_team_key)
                
                # Prepare player IDs
                home_player_1_id = match.get('Home Player 1 ID')
                home_player_2_id = match.get('Home Player 2 ID')
                away_player_1_id = match.get('Away Player 1 ID')
                away_player_2_id = match.get('Away Player 2 ID')
                
                # Perform upsert
                if tenniscores_match_id:
                    # Use upsert for records with match_id
                    cursor.execute("""
                        INSERT INTO match_scores (
                            match_date, home_team, away_team, home_team_id, away_team_id,
                            home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id,
                            scores, winner, league_id, tenniscores_match_id, created_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (tenniscores_match_id) WHERE tenniscores_match_id IS NOT NULL DO UPDATE
                        SET
                            match_date = EXCLUDED.match_date,
                            home_team = EXCLUDED.home_team,
                            away_team = EXCLUDED.away_team,
                            home_team_id = EXCLUDED.home_team_id,
                            away_team_id = EXCLUDED.away_team_id,
                            home_player_1_id = EXCLUDED.home_player_1_id,
                            home_player_2_id = EXCLUDED.home_player_2_id,
                            away_player_1_id = EXCLUDED.away_player_1_id,
                            away_player_2_id = EXCLUDED.away_player_2_id,
                            scores = EXCLUDED.scores,
                            winner = EXCLUDED.winner,
                            league_id = EXCLUDED.league_id
                    """, [
                        match_date, home_team, away_team, home_team_id, away_team_id,
                        home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id,
                        scores, winner, league_db_id, tenniscores_match_id
                    ])
                    
                    # Check if it was an insert or update
                    if cursor.rowcount == 1:
                        inserted_count += 1
                else:
                    # For records without tenniscores_match_id, check for duplicates first
                    cursor.execute("""
                        SELECT id FROM match_scores
                        WHERE match_date = %s
                        AND home_team = %s
                        AND away_team = %s
                        AND scores = %s
                        LIMIT 1
                    """, [match_date, home_team, away_team, scores])
                    
                    existing_record = cursor.fetchone()
                    
                    if not existing_record:
                        # Record doesn't exist, insert it
                        cursor.execute("""
                            INSERT INTO match_scores (
                                match_date, home_team, away_team, home_team_id, away_team_id,
                                home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id,
                                scores, winner, league_id, created_at
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        """, [
                            match_date, home_team, away_team, home_team_id, away_team_id,
                            home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id,
                            scores, winner, league_db_id
                        ])
                        inserted_count += 1
                
            except Exception as e:
                error_count += 1
                if error_count < 5:  # Only show first few errors
                    print(f"   ⚠️ Error processing match {i}: {e}")
        
        # Commit transaction
        conn.commit()
        cursor.close()
        
        print(f"✅ Match scores complete: {inserted_count} inserted, {updated_count} updated ({error_count} errors)")
        return inserted_count

def main():
    print("🚀 Quick Match Import: All Match Scores to Main Database")
    print("=" * 60)
    
    try:
        # Test database connection
        with get_db() as test_conn:
            pass
        print("✅ Database connection test successful")
        
        # Load data
        match_data = load_match_data()
        
        # Import matches
        start_time = time.time()
        imported_count = import_match_scores(match_data)
        end_time = time.time()
        
        duration = end_time - start_time
        print(f"\n🎉 Import Complete! ({duration:.1f}s)")
        print(f"   match_scores: {imported_count:,} records")
        
    except Exception as e:
        print(f"❌ Import failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 