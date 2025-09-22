#!/usr/bin/env python3
"""
Update captain status for APTA Chicago players based on scraped data
"""

import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db

def main():
    print('👑 UPDATING CAPTAIN STATUS FROM SCRAPED DATA')
    print('=' * 60)
    
    # Load scraped data
    with open('data/leagues/APTA_CHICAGO/players.json', 'r') as f:
        scraped_data = json.load(f)
    
    print(f'📊 Loaded {len(scraped_data)} players from scraped data')
    
    # Create mapping of player ID to captain status
    captain_mapping = {}
    for player in scraped_data:
        player_id = player.get('Player ID')
        captain_status = player.get('Captain')
        if player_id and captain_status:
            captain_mapping[player_id] = captain_status
    
    print(f'📋 Found {len(captain_mapping)} players with captain status in scraped data')
    
    # Update database
    with get_db() as conn:
        cursor = conn.cursor()
        
        updated_count = 0
        captain_count = 0
        
        for player_id, captain_status in captain_mapping.items():
            # Convert "Yes"/"No" to database format
            db_captain_status = "Yes" if captain_status == "Yes" else None
            
            try:
                cursor.execute("""
                    UPDATE players 
                    SET captain_status = %s, updated_at = NOW()
                    WHERE tenniscores_player_id = %s 
                    AND league_id = (SELECT id FROM leagues WHERE league_name = 'APTA Chicago')
                """, (db_captain_status, player_id))
                
                if cursor.rowcount > 0:
                    updated_count += 1
                    if db_captain_status == "Yes":
                        captain_count += 1
                        
            except Exception as e:
                print(f"❌ Error updating player {player_id}: {e}")
        
        conn.commit()
        
        print(f'✅ Updated {updated_count} players')
        print(f'👑 Set {captain_count} players as captains')
        
        # Verify the update
        cursor.execute("""
            SELECT captain_status, COUNT(*) as count
            FROM players p 
            JOIN leagues l ON p.league_id = l.id 
            WHERE l.league_name = 'APTA Chicago'
            GROUP BY captain_status
            ORDER BY count DESC
        """)
        captain_stats = cursor.fetchall()
        
        print('\n📊 CAPTAIN STATUS AFTER UPDATE:')
        for status, count in captain_stats:
            print(f'   {status}: {count:,} players')
        
        # Check Ross Freedman specifically
        cursor.execute("""
            SELECT p.first_name, p.last_name, p.captain_status, p.team_id
            FROM players p 
            JOIN leagues l ON p.league_id = l.id 
            WHERE l.league_name = 'APTA Chicago' 
            AND p.first_name = 'Ross' AND p.last_name = 'Freedman'
        """)
        ross = cursor.fetchone()
        
        if ross:
            print(f'\n🔍 ROSS FREEDMAN: Captain={ross[2]}, Team={ross[3]}')
        else:
            print('\n❌ Ross Freedman not found')

if __name__ == "__main__":
    main()
