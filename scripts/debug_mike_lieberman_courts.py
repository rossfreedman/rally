#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collections import defaultdict
from database_utils import execute_query, execute_query_one

def debug_mike_lieberman_courts():
    print("=== DEBUGGING MIKE LIEBERMAN'S COURT ASSIGNMENTS ===")
    
    # Find Mike Lieberman in the database
    player_query = """
        SELECT tenniscores_player_id, first_name, last_name, team_id, league_id
        FROM players 
        WHERE LOWER(first_name) LIKE '%mike%' 
        AND LOWER(last_name) LIKE '%lieberman%'
        AND is_active = TRUE
    """
    
    mike_records = execute_query(player_query)
    print(f"Found {len(mike_records)} Mike Lieberman records:")
    
    for record in mike_records:
        print(f"  {record['first_name']} {record['last_name']} - ID: {record['tenniscores_player_id']}")
        print(f"    Team ID: {record['team_id']}, League ID: {record['league_id']}")
    
    if not mike_records:
        print("No Mike Lieberman found!")
        return
    
    # Check all Mike Lieberman records to find the one with 16 matches
    for mike in mike_records:
        player_id = mike['tenniscores_player_id']
        team_id = mike['team_id']
        league_id = mike['league_id']
        
        print(f"\n=== ANALYZING {mike['first_name']} {mike['last_name']} (ID: {player_id}) ===")
        
        # Get all matches for this Mike Lieberman
        matches_query = """
            SELECT 
                TO_CHAR(match_date, 'DD-Mon-YY') as "Date",
                match_date,
                id,
                home_team as "Home Team",
                away_team as "Away Team",
                winner as "Winner",
                home_player_1_id as "Home Player 1",
                home_player_2_id as "Home Player 2",
                away_player_1_id as "Away Player 1",
                away_player_2_id as "Away Player 2"
            FROM match_scores
            WHERE (
                home_player_1_id = %s OR 
                home_player_2_id = %s OR 
                away_player_1_id = %s OR 
                away_player_2_id = %s
            )
            AND league_id = %s
            ORDER BY match_date, id
        """
        
        mike_matches = execute_query(matches_query, [player_id, player_id, player_id, player_id, league_id])
        print(f"Found {len(mike_matches)} matches for this Mike")
        
        if len(mike_matches) == 16:
            print(f"🎯 THIS IS THE MIKE WITH 16 MATCHES!")
            analyze_court_assignments(mike, mike_matches, league_id)
        elif len(mike_matches) > 0:
            print(f"This Mike has {len(mike_matches)} matches (not the 16-match Mike)")
        else:
            print("No matches found for this Mike")

def analyze_court_assignments(mike, mike_matches, league_id):
    player_id = mike['tenniscores_player_id']
    
    # Initialize court stats like the backend does
    court_stats = {
        f"court{i}": {
            "matches": 0,
            "wins": 0,
            "losses": 0,
            "partners": defaultdict(lambda: {"matches": 0, "wins": 0, "losses": 0})
        }
        for i in range(1, 5)
    }
    
    # Process each match using the same logic as get_player_analysis
    all_team_matchups = {}
    
    for match in mike_matches:
        match_date = match.get("Date")
        home_team = match.get("Home Team", "")
        away_team = match.get("Away Team", "")
        match_id = match.get("id")
        matchup_key = f"{match_date}|{home_team}|{away_team}"
        
        # Get all matches for this team matchup (same logic as backend)
        if matchup_key not in all_team_matchups:
            team_matchup_query = """
                SELECT id
                FROM match_scores 
                WHERE TO_CHAR(match_date, 'DD-Mon-YY') = %s
                AND home_team = %s 
                AND away_team = %s
                AND league_id = %s
                ORDER BY id ASC
            """
            all_matches = execute_query(team_matchup_query, [match_date, home_team, away_team, league_id])
            all_team_matchups[matchup_key] = [m["id"] for m in all_matches]
        
        # Find this match's position in the ordered team matchup
        team_match_ids = all_team_matchups.get(matchup_key, [])
        court_num = None
        for i, team_match_id in enumerate(team_match_ids, 1):
            if team_match_id == match_id:
                court_num = i
                break
        
        # Fallback logic if court not found
        if court_num is None or court_num > 4:
            fallback_court = (match_id % 4) + 1
            court_num = fallback_court
            print(f"  Match {match_id} assigned to fallback court {court_num}")
        
        court_key = f"court{court_num}"
        
        # Determine if Mike won
        is_home = player_id in [match.get("Home Player 1"), match.get("Home Player 2")]
        winner = match.get("Winner") or ""
        won = (is_home and winner.lower() == "home") or (not is_home and winner.lower() == "away")
        
        # Update court stats
        court_stats[court_key]["matches"] += 1
        if won:
            court_stats[court_key]["wins"] += 1
        else:
            court_stats[court_key]["losses"] += 1
        
        print(f"  {match_date}: {home_team} vs {away_team} - Court {court_num} - {'Won' if won else 'Lost'}")
    
    print(f"\n=== MIKE'S COURT PERFORMANCE ===")
    
    # Calculate win rates for each court (same logic as backend)
    best_court = None
    best_court_rate = 0
    best_court_matches = 0
    
    for court_key, court_stat in court_stats.items():
        court_num = court_key.replace('court', '')
        matches = court_stat["matches"]
        wins = court_stat["wins"]
        losses = court_stat["losses"]
        
        if matches > 0:
            win_rate = round((wins / matches) * 100, 1)
            print(f"Court {court_num}: {matches} matches, {wins}-{losses}, {win_rate}% win rate")
            
            # Apply best court logic (minimum 3 matches)
            if matches >= 3:
                if win_rate > best_court_rate or (win_rate == best_court_rate and matches > best_court_matches):
                    best_court_rate = win_rate
                    best_court_matches = matches
                    best_court = f"Court {court_num}"
                    print(f"  ^^ NEW BEST COURT: {best_court} ({win_rate}% in {matches} matches)")
        else:
            print(f"Court {court_num}: 0 matches")
    
    print(f"\n=== FINAL RESULT ===")
    print(f"Best Court: {best_court}")
    print(f"Best Court Rate: {best_court_rate}%")
    print(f"Best Court Matches: {best_court_matches}")
    
    if best_court != "Court 4":
        print(f"\n❌ ISSUE CONFIRMED: Best court is {best_court}, not Court 4!")
        print("The Team Roster is showing incorrect data.")
    else:
        print(f"\n✅ Court 4 is correctly identified as best court")

if __name__ == "__main__":
    debug_mike_lieberman_courts() 