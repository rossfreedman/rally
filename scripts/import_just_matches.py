#!/usr/bin/env python3
"""
Simple script to import just matches from JSON data
"""

import json
import os
import sys
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from database_config import get_db

def main():
    print("🔄 Importing match history from JSON...")
    
    # Load match history
    match_file = os.path.join(project_root, "data", "leagues", "all", "match_history.json")
    
    try:
        with open(match_file, 'r') as f:
            matches = json.load(f)
            
        print(f"📊 Found {len(matches)} matches to import")
        
        # Get database connection
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Import matches
        imported = 0
        skipped = 0
        
        for match in matches:
            try:
                # Extract match data
                date = match.get('date', '').strip()
                home_team = match.get('home_team', '').strip()
                away_team = match.get('away_team', '').strip()
                scores = match.get('scores', '').strip()
                winner = match.get('winner', '').strip()
                league = match.get('league', '').strip()
                
                if not all([date, home_team, away_team, scores, league]):
                    skipped += 1
                    continue
                
                # Check if match already exists
                cursor.execute("""
                    SELECT id FROM match_scores 
                    WHERE date = %s AND home_team = %s AND away_team = %s AND league = %s
                """, (date, home_team, away_team, league))
                
                if cursor.fetchone():
                    skipped += 1
                    continue
                
                # Insert match
                cursor.execute("""
                    INSERT INTO match_scores (
                        date, home_team, away_team, scores, winner, league,
                        created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    date, home_team, away_team, scores, winner, league,
                    datetime.now(), datetime.now()
                ))
                
                imported += 1
                
                if imported % 1000 == 0:
                    print(f"   📊 Imported {imported} matches so far...")
                    
            except Exception as e:
                print(f"❌ Error importing match: {e}")
                skipped += 1
                continue
        
        conn.commit()
        print(f"✅ Import complete: {imported} imported, {skipped} skipped")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    finally:
        if 'conn' in locals():
            conn.close()
    
    return True

if __name__ == "__main__":
    main() 