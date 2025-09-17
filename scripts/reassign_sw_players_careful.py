#!/usr/bin/env python3
"""
Carefully reassign SW players from generic 'Series SW' to their correct specific SW series
This script handles potential duplicates by checking before reassigning
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database_config import get_db

def reassign_sw_players_careful():
    """Carefully reassign SW players to their correct specific series."""
    print("🔄 Carefully Reassigning SW Players to Correct Series")
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
            
            print(f"\nReassigning players carefully...")
            
            # Reassign players based on their team names, one series at a time
            total_reassigned = 0
            
            for series_name, target_series_id in sw_series_mapping.items():
                # Extract the series number from the series name (e.g., "Series 15 SW" -> "15")
                series_num = series_name.replace('Series ', '').replace(' SW', '')
                
                print(f"\nProcessing {series_name} (looking for teams with '{series_num} SW'):")
                
                # Find players in generic Series SW whose teams contain the series number + "SW"
                cursor.execute("""
                    SELECT p.id, p.tenniscores_player_id, p.first_name, p.last_name, t.team_name, t.club_id
                    FROM players p 
                    JOIN teams t ON p.team_id = t.id 
                    WHERE p.league_id = %s 
                    AND p.series_id = %s
                    AND t.team_name LIKE %s
                """, (league_id, generic_sw_id, f'%{series_num} SW%'))
                
                candidates = cursor.fetchall()
                print(f"  Found {len(candidates)} candidates for {series_name}")
                
                reassigned_this_series = 0
                skipped_this_series = 0
                
                for player_id, tenniscores_id, first_name, last_name, team_name, club_id in candidates:
                    # Check if this player already exists in the target series
                    cursor.execute("""
                        SELECT id FROM players 
                        WHERE tenniscores_player_id = %s 
                        AND league_id = %s 
                        AND series_id = %s
                    """, (tenniscores_id, league_id, target_series_id))
                    
                    existing = cursor.fetchone()
                    
                    if existing:
                        # Player already exists in target series, skip
                        skipped_this_series += 1
                        print(f"    ⏭️  {first_name} {last_name} - already exists in {series_name}")
                    else:
                        # Safe to reassign
                        cursor.execute("""
                            UPDATE players 
                            SET series_id = %s
                            WHERE id = %s
                        """, (target_series_id, player_id))
                        
                        reassigned_this_series += 1
                        print(f"    ✅ {first_name} {last_name} - reassigned to {series_name}")
                
                total_reassigned += reassigned_this_series
                print(f"  {series_name}: {reassigned_this_series} reassigned, {skipped_this_series} skipped")
            
            # Commit changes
            db.commit()
            print(f"\n✅ Total players reassigned: {total_reassigned}")
            
            # Verify the reassignment
            print(f"\n🔍 Verifying reassignment...")
            
            # Check remaining players in generic 'Series SW'
            cursor.execute('SELECT COUNT(*) FROM players WHERE league_id = %s AND series_id = %s', (league_id, generic_sw_id))
            remaining_generic = cursor.fetchone()[0]
            print(f"Players still in generic 'Series SW': {remaining_generic}")
            
            # Check players in each specific SW series
            print(f"\nPlayers per SW series after reassignment:")
            cursor.execute('''
                SELECT s.name, COUNT(*) as count
                FROM players p 
                JOIN series s ON p.series_id = s.id 
                WHERE p.league_id = %s 
                AND s.name LIKE %s
                GROUP BY s.name 
                ORDER BY s.name
            ''', (league_id, '%SW%'))
            
            for series_name, count in cursor.fetchall():
                print(f"  {series_name}: {count} players")
            
    except Exception as e:
        print(f"❌ Error reassigning SW players: {e}")
        raise

if __name__ == "__main__":
    reassign_sw_players_careful()
