#!/usr/bin/env python3
"""
Check Staging JSON Data
=======================

This script checks if CNSWPL data exists in the consolidated JSON files on staging.
"""

import json
import os
from pathlib import Path

def check_json_data():
    print("🔍 CHECKING STAGING JSON DATA")
    print("=" * 40)
    
    # Check if consolidated files exist
    data_dir = Path("/app/data/leagues/all")
    match_file = data_dir / "match_history.json"
    
    if not match_file.exists():
        print(f"❌ Match history file not found: {match_file}")
        return
    
    print(f"✅ Found match history file: {match_file}")
    
    try:
        with open(match_file, 'r') as f:
            matches = json.load(f)
        
        total_matches = len(matches)
        print(f"📊 Total matches in JSON: {total_matches}")
        
        # Count CNSWPL matches
        cnswpl_matches = 0
        lisa_wagner_matches = 0
        
        for match in matches:
            league_id = match.get('league_id', '').strip()
            source_league = match.get('source_league', '').strip()
            
            # Check if this is a CNSWPL match
            if league_id == 'CNSWPL' or source_league == 'CNSWPL':
                cnswpl_matches += 1
                
                # Check for Lisa Wagner
                players = [
                    match.get('Home Player 1 Name', ''),
                    match.get('Home Player 2 Name', ''),
                    match.get('Away Player 1 Name', ''),
                    match.get('Away Player 2 Name', '')
                ]
                
                for player in players:
                    if player and 'lisa' in player.lower() and 'wagner' in player.lower():
                        lisa_wagner_matches += 1
                        break
        
        print(f"🏆 CNSWPL matches in JSON: {cnswpl_matches}")
        print(f"👤 Lisa Wagner matches in JSON: {lisa_wagner_matches}")
        
        if cnswpl_matches == 0:
            print(f"❌ NO CNSWPL MATCHES IN JSON - consolidation failed!")
            
            # Check source leagues
            source_leagues = set()
            for match in matches[:100]:  # Sample first 100
                source = match.get('source_league', '')
                if source:
                    source_leagues.add(source)
            
            print(f"📋 Source leagues found: {sorted(source_leagues)}")
        else:
            print(f"✅ CNSWPL data exists in JSON - import process issue!")
            
            # Show sample CNSWPL match
            for match in matches:
                if match.get('source_league') == 'CNSWPL':
                    print(f"\n📋 Sample CNSWPL match:")
                    print(f"   Date: {match.get('Date')}")
                    print(f"   Teams: {match.get('Home Team')} vs {match.get('Away Team')}")
                    print(f"   League ID: {match.get('league_id')}")
                    print(f"   Source: {match.get('source_league')}")
                    break
    
    except Exception as e:
        print(f"❌ Error reading JSON: {e}")

if __name__ == "__main__":
    check_json_data()
