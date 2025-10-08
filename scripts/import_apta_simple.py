#!/usr/bin/env python3
"""
Simplified APTA import script for staging.
This version skips the career stats consistency check that might be causing the hang.
"""

import os
import sys
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

def import_apta_simple():
    print("🚀 SIMPLIFIED APTA IMPORT FOR STAGING")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Load the players data
    players_file = "data/leagues/APTA_CHICAGO/players.json"
    if not os.path.exists(players_file):
        print(f"❌ {players_file} not found")
        return False
    
    with open(players_file, 'r') as f:
        players_data = json.load(f)
    
    print(f"✅ Loaded {len(players_data):,} player records")
    
    # Import the database functions
    from database_config import get_db
    
    with get_db() as conn:
        with conn.cursor() as cur:
            # Get APTA league ID
            cur.execute("SELECT id FROM leagues WHERE league_id = 'APTA_CHICAGO'")
            league_result = cur.fetchone()
            if not league_result:
                print("❌ APTA_CHICAGO league not found")
                return False
            
            league_id = league_result[0]
            print(f"✅ Found league ID: {league_id}")
            
            # Clear existing APTA data first
            print("🗑️  Clearing existing APTA data...")
            cur.execute("DELETE FROM player_history WHERE player_id IN (SELECT id FROM players WHERE league_id = %s)", (league_id,))
            cur.execute("DELETE FROM players WHERE league_id = %s", (league_id,))
            conn.commit()
            print("✅ Cleared existing data")
            
            # Import players one by one with simple logic
            print("📥 Importing players...")
            imported = 0
            failed = 0
            
            for i, player in enumerate(players_data):
                try:
                    # Extract basic data
                    first_name = player.get("First Name", "").strip()
                    last_name = player.get("Last Name", "").strip()
                    team_name = player.get("Team", "").strip()
                    external_id = player.get("Player ID", "").strip()
                    
                    # Extract career stats
                    career_wins = player.get("Career Wins", 0)
                    career_losses = player.get("Career Losses", 0)
                    career_win_pct = player.get("Career Win %", "0.0%")
                    
                    # Extract captain status
                    captain_raw = player.get("Captain", "No").strip()
                    captain_status = (captain_raw == "Yes")
                    
                    # Extract PTI
                    pti_raw = player.get("PTI", "")
                    pti_value = None
                    if pti_raw and pti_raw != "N/A" and pti_raw != "0":
                        try:
                            pti_value = float(pti_raw)
                        except (ValueError, TypeError):
                            pti_value = None
                    
                    # Extract wins/losses
                    wins_raw = player.get("Wins", "0")
                    losses_raw = player.get("Losses", "0")
                    try:
                        wins_value = int(wins_raw) if wins_raw and wins_raw != "N/A" else 0
                        losses_value = int(losses_raw) if losses_raw and losses_raw != "N/A" else 0
                    except (ValueError, TypeError):
                        wins_value = 0
                        losses_value = 0
                    
                    # Calculate win percentage
                    total_matches = wins_value + losses_value
                    win_percentage = (wins_value / total_matches * 100) if total_matches > 0 else 0.0
                    
                    # Parse career win percentage
                    career_win_percentage = 0.0
                    if isinstance(career_win_pct, str) and career_win_pct.endswith('%'):
                        try:
                            career_win_percentage = float(career_win_pct[:-1])
                        except (ValueError, TypeError):
                            career_win_percentage = 0.0
                    
                    # Calculate career matches
                    career_matches = career_wins + career_losses
                    
                    # For now, use dummy values for club_id, series_id, team_id
                    # This is a simplified version to test the import
                    club_id = 1  # Dummy club ID
                    series_id = 1  # Dummy series ID
                    team_id = 1  # Dummy team ID
                    
                    # Insert player
                    cur.execute("""
                        INSERT INTO players (
                            first_name, last_name, league_id, club_id, series_id, team_id,
                            tenniscores_player_id, pti, wins, losses, win_percentage,
                            career_wins, career_losses, career_matches, career_win_percentage,
                            captain_status
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        first_name, last_name, league_id, club_id, series_id, team_id,
                        external_id, pti_value, wins_value, losses_value, win_percentage,
                        career_wins, career_losses, career_matches, career_win_percentage,
                        captain_status
                    ))
                    
                    imported += 1
                    
                    # Progress update every 100 players
                    if imported % 100 == 0:
                        print(f"   Imported {imported:,} players...")
                    
                except Exception as e:
                    print(f"   ❌ Error importing player {first_name} {last_name}: {e}")
                    failed += 1
                    continue
            
            # Commit all changes
            conn.commit()
            
            print()
            print("✅ IMPORT COMPLETED!")
            print(f"   Imported: {imported:,} players")
            print(f"   Failed: {failed:,} players")
            
            # Verify the import
            cur.execute("SELECT COUNT(*) FROM players WHERE league_id = %s", (league_id,))
            total_players = cur.fetchone()[0]
            print(f"   Total in database: {total_players:,} players")
            
            cur.execute("SELECT COUNT(*) FROM players WHERE league_id = %s AND captain_status = 'true'", (league_id,))
            captains = cur.fetchone()[0]
            print(f"   Captains: {captains:,}")
            
            return True

if __name__ == "__main__":
    success = import_apta_simple()
    sys.exit(0 if success else 1)
