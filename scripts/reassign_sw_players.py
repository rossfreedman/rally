#!/usr/bin/env python3
"""
Reassign SW players from generic 'Series SW' to their correct specific SW series
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database_config import get_db

def reassign_sw_players():
    """Reassign SW players to their correct specific series."""
    print("🔄 Reassigning SW Players to Correct Series")
    print("=" * 50)
    
    league_id = 4783  # APTA_CHICAGO league ID
    
    try:
        with get_db() as db:
            cursor = db.cursor()
            
            # Get the generic 'Series SW' ID
            cursor.execute('SELECT id FROM series WHERE league_id = %s AND name = %s', (league_id, 'Series SW'))
            generic_sw_id = cursor.fetchone()[0]
            print(f"Generic 'Series SW' ID: {generic_sw_id}")
            
            # Get all SW series mappings
            sw_series_mapping = {}
            cursor.execute('SELECT id, name FROM series WHERE league_id = %s AND name LIKE %s AND name != %s', (league_id, '%SW%', 'Series SW'))
            sw_series = cursor.fetchall()
            
            for series_id, series_name in sw_series:
                sw_series_mapping[series_name] = series_id
                print(f"  {series_name}: ID {series_id}")
            
            print(f"\nReassigning players...")
            
            # Reassign players based on their team names
            reassigned_count = 0
            
            for series_name, series_id in sw_series_mapping.items():
                # Extract the series number from the series name (e.g., "Series 15 SW" -> "15")
                series_num = series_name.replace('Series ', '').replace(' SW', '')
                
                # Update players whose team names contain the series number + "SW"
                cursor.execute("""
                    UPDATE players 
                    SET series_id = %s
                    WHERE league_id = %s 
                    AND series_id = %s
                    AND team_id IN (
                        SELECT t.id FROM teams t 
                        WHERE t.league_id = %s 
                        AND t.team_name LIKE %s
                    )
                """, (series_id, league_id, generic_sw_id, league_id, f'%{series_num} SW%'))
                
                updated_count = cursor.rowcount
                reassigned_count += updated_count
                print(f"  ✅ {series_name}: {updated_count} players reassigned")
            
            # Commit changes
            db.commit()
            print(f"\n✅ Total players reassigned: {reassigned_count}")
            
            # Verify the reassignment
            print(f"\n🔍 Verifying reassignment...")
            
            # Check remaining players in generic 'Series SW'
            cursor.execute('SELECT COUNT(*) FROM players WHERE league_id = %s AND series_id = %s', (league_id, generic_sw_id))
            remaining_generic = cursor.fetchone()[0]
            print(f"Players still in generic 'Series SW': {remaining_generic}")
            
            # Check players in each specific SW series
            print(f"\nPlayers per SW series after reassignment:")
            for series_name, series_id in sw_series_mapping.items():
                cursor.execute('SELECT COUNT(*) FROM players WHERE league_id = %s AND series_id = %s', (league_id, series_id))
                count = cursor.fetchone()[0]
                print(f"  {series_name}: {count} players")
            
            # Show some sample reassigned players
            print(f"\nSample reassigned players:")
            cursor.execute("""
                SELECT p.first_name, p.last_name, t.team_name, s.name 
                FROM players p 
                JOIN teams t ON p.team_id = t.id 
                JOIN series s ON p.series_id = s.id 
                WHERE p.league_id = %s 
                AND s.name LIKE %s 
                AND s.name != %s
                LIMIT 5
            """, (league_id, '%SW%', 'Series SW'))
            
            sample_players = cursor.fetchall()
            for first, last, team, series in sample_players:
                print(f"  {first} {last} - {team} ({series})")
            
    except Exception as e:
        print(f"❌ Error reassigning SW players: {e}")
        raise

if __name__ == "__main__":
    reassign_sw_players()
