#!/usr/bin/env python3
"""
Fix Wilmette H(3) player assignments.

This script:
1. Finds players from Wilmette H(3) matches that aren't in the players table
2. Creates player records for them with the correct team_id (60050)
3. Reassigns any existing players who should be on H(3) but are on wrong teams
"""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db_url, parse_db_url
import psycopg2

def get_wilmette_h3_players_from_matches():
    """Extract player information from match_scores.json for Wilmette H(3) matches."""
    match_scores_path = 'data/leagues/CNSWPL/match_scores.json'
    
    if not os.path.exists(match_scores_path):
        print(f"❌ {match_scores_path} not found")
        return []
    
    with open(match_scores_path, 'r') as f:
        matches = json.load(f)
    
    # Find all players from Wilmette H(3) matches
    players_map = {}  # player_id -> {'name': str, 'first_name': str, 'last_name': str}
    
    for match in matches:
        home_team = match.get('Home Team', '')
        away_team = match.get('Away Team', '')
        
        # Check if this match involves Wilmette H(3)
        # IMPORTANT: Only extract players who are ON Wilmette H(3), not players playing AGAINST them
        is_wilmette_h3_home = 'Wilmette H(3)' in home_team
        is_wilmette_h3_away = 'Wilmette H(3)' in away_team
        
        if is_wilmette_h3_home or is_wilmette_h3_away:
            # Extract players from the correct team (home or away)
            if is_wilmette_h3_home:
                # Wilmette H(3) is home team - get home players
                player_fields = [
                    ('Home Player 1', 'Home Player 1 ID'),
                    ('Home Player 2', 'Home Player 2 ID')
                ]
            else:
                # Wilmette H(3) is away team - get away players
                player_fields = [
                    ('Away Player 1', 'Away Player 1 ID'),
                    ('Away Player 2', 'Away Player 2 ID')
                ]
            
            for field_name, field_id_name in player_fields:
                player_id = match.get(field_id_name, '').strip()
                player_name = match.get(field_name, '').strip()
                
                if player_id and player_name and player_id.startswith('cnswpl_'):
                    # Parse name into first/last
                    name_parts = player_name.split(maxsplit=1)
                    if len(name_parts) == 2:
                        first_name, last_name = name_parts
                        players_map[player_id] = {
                            'name': player_name,
                            'first_name': first_name,
                            'last_name': last_name
                        }
    
    return players_map

def main():
    print("=" * 80)
    print("Fixing Wilmette H(3) Player Assignments")
    print("=" * 80)
    
    # Get database connection
    db_url = get_db_url()
    db_params = parse_db_url(db_url)
    
    conn = psycopg2.connect(**db_params)
    cur = conn.cursor()
    
    try:
        # Get league and team IDs
        cur.execute("SELECT id FROM leagues WHERE league_id = 'CNSWPL' OR league_name = 'CNSWPL' LIMIT 1")
        league_row = cur.fetchone()
        if not league_row:
            print("❌ CNSWPL league not found")
            return
        league_id = league_row[0]
        
        cur.execute("SELECT id FROM teams WHERE team_name = 'Wilmette H(3)' AND league_id = %s LIMIT 1", (league_id,))
        team_row = cur.fetchone()
        if not team_row:
            print("❌ Wilmette H(3) team not found")
            return
        team_id = team_row[0]
        
        print(f"\n✅ Found:")
        print(f"   League ID: {league_id}")
        print(f"   Team ID: {team_id} (Wilmette H(3))")
        
        # Get club_id and series_id for Wilmette H(3)
        cur.execute("""
            SELECT club_id, series_id 
            FROM teams 
            WHERE id = %s
        """, (team_id,))
        team_info = cur.fetchone()
        club_id, series_id = team_info
        
        print(f"   Club ID: {club_id}, Series ID: {series_id}")
        
        # Get players from match data
        print("\n📥 Extracting players from match_scores.json...")
        players_map = get_wilmette_h3_players_from_matches()
        print(f"   Found {len(players_map)} unique players from matches")
        
        # Check which players exist and which need to be created
        created = 0
        updated = 0
        existing = 0
        
        for player_id, player_info in players_map.items():
            # Check if player exists
            cur.execute("""
                SELECT id, team_id, first_name, last_name 
                FROM players 
                WHERE tenniscores_player_id = %s AND league_id = %s
            """, (player_id, league_id))
            
            player_row = cur.fetchone()
            
            if player_row:
                existing_player_id, existing_team_id, existing_first, existing_last = player_row
                
                # Check if they're on the correct team
                if existing_team_id == team_id:
                    print(f"   ✅ {player_info['name']} ({player_id[:20]}...) already on correct team")
                    existing += 1
                else:
                    # Update to correct team
                    cur.execute("""
                        UPDATE players 
                        SET team_id = %s, club_id = %s, series_id = %s
                        WHERE id = %s
                    """, (team_id, club_id, series_id, existing_player_id))
                    
                    existing_team_name = "Unknown"
                    if existing_team_id:
                        cur.execute("SELECT team_name FROM teams WHERE id = %s", (existing_team_id,))
                        existing_team_row = cur.fetchone()
                        if existing_team_row:
                            existing_team_name = existing_team_row[0]
                    
                    print(f"   🔄 {player_info['name']} reassigned from team_id {existing_team_id} ({existing_team_name}) to team_id {team_id}")
                    updated += 1
            else:
                # Create new player record
                cur.execute("""
                    INSERT INTO players (
                        tenniscores_player_id, first_name, last_name,
                        team_id, club_id, series_id, league_id, is_active
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, true)
                    RETURNING id
                """, (
                    player_id,
                    player_info['first_name'],
                    player_info['last_name'],
                    team_id,
                    club_id,
                    series_id,
                    league_id
                ))
                
                new_player_id = cur.fetchone()[0]
                print(f"   ✨ Created {player_info['name']} ({player_id[:20]}...) -> player_id {new_player_id}")
                created += 1
        
        # Commit changes
        conn.commit()
        
        print("\n" + "=" * 80)
        print("Summary:")
        print(f"   ✅ Existing (correct team): {existing}")
        print(f"   🔄 Updated (reassigned): {updated}")
        print(f"   ✨ Created (new players): {created}")
        print(f"   📊 Total: {len(players_map)}")
        print("=" * 80)
        
        # Verify final state
        cur.execute("""
            SELECT COUNT(*) 
            FROM players 
            WHERE team_id = %s AND league_id = %s AND is_active = true
        """, (team_id, league_id))
        final_count = cur.fetchone()[0]
        print(f"\n✅ Final player count for Wilmette H(3): {final_count}")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    main()

