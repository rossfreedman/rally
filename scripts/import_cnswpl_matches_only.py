#!/usr/bin/env python3
"""
Import CNSWPL Matches Only to Staging
====================================

This script imports only CNSWPL match data to staging,
avoiding duplicate key violations from existing APTA/NSTF data.
"""

import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
import sys
from dotenv import load_dotenv

def import_cnswpl_matches_to_staging():
    print("🚀 IMPORTING CNSWPL MATCHES TO STAGING")
    print("=" * 60)
    
    # Load environment
    load_dotenv()
    staging_url = os.getenv('DATABASE_PUBLIC_URL')
    
    if staging_url.startswith("postgres://"):
        staging_url = staging_url.replace("postgres://", "postgresql://", 1)
    
    # Connect to staging
    parsed = urlparse(staging_url)
    conn = psycopg2.connect(
        dbname=parsed.path[1:],
        user=parsed.username,
        password=parsed.password,
        host=parsed.hostname,
        port=parsed.port or 5432,
        sslmode="require",
        connect_timeout=30
    )
    
    # Load CNSWPL data
    with open('data/leagues/CNSWPL/match_history.json', 'r') as f:
        cnswpl_matches = json.load(f)
    
    print(f"📂 Loaded {len(cnswpl_matches)} CNSWPL matches")
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        # Get CNSWPL league ID
        cursor.execute("SELECT id FROM leagues WHERE league_id = 'CNSWPL'")
        league = cursor.fetchone()
        cnswpl_league_id = league['id']
        print(f"🎯 Target league ID: {cnswpl_league_id}")
        
        # Import matches in batches
        batch_size = 100
        imported_count = 0
        skipped_count = 0
        
        for i in range(0, len(cnswpl_matches), batch_size):
            batch = cnswpl_matches[i:i + batch_size]
            
            for match in batch:
                try:
                    # Insert match with CNSWPL league ID
                    cursor.execute("""
                        INSERT INTO match_scores (
                            match_date, home_team, away_team, 
                            home_player_1_name, home_player_1_id,
                            home_player_2_name, home_player_2_id,
                            away_player_1_name, away_player_1_id,
                            away_player_2_name, away_player_2_id,
                            winner, scores, league_id
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (
                        match.get('match_date'),
                        match.get('home_team'),
                        match.get('away_team'),
                        match.get('home_player_1_name'),
                        match.get('home_player_1_id'),
                        match.get('home_player_2_name'),
                        match.get('home_player_2_id'),
                        match.get('away_player_1_name'),
                        match.get('away_player_1_id'),
                        match.get('away_player_2_name'),
                        match.get('away_player_2_id'),
                        match.get('winner'),
                        match.get('scores'),
                        cnswpl_league_id
                    ))
                    
                    imported_count += 1
                    
                except Exception as e:
                    print(f"⚠️ Skipped match: {e}")
                    skipped_count += 1
                    continue
            
            # Commit batch
            conn.commit()
            print(f"📊 Batch {i//batch_size + 1}: Imported {imported_count}, Skipped {skipped_count}")
        
        print(f"\n✅ CNSWPL IMPORT COMPLETE!")
        print(f"   Imported: {imported_count} matches")
        print(f"   Skipped: {skipped_count} matches")
        
        # Verify import
        cursor.execute("""
            SELECT COUNT(*) as total_cnswpl
            FROM match_scores
            WHERE league_id = %s
        """, (cnswpl_league_id,))
        
        final_count = cursor.fetchone()
        print(f"   Final CNSWPL matches in database: {final_count['total_cnswpl']}")
        
        # Check for Lisa Wagner
        lisa_player_id = "nndz-WkM2eHhybi9qUT09"
        cursor.execute("""
            SELECT COUNT(*) as lisa_matches
            FROM match_scores
            WHERE (home_player_1_id = %s OR home_player_2_id = %s
                   OR away_player_1_id = %s OR away_player_2_id = %s)
        """, (lisa_player_id, lisa_player_id, lisa_player_id, lisa_player_id))
        
        lisa_matches = cursor.fetchone()
        print(f"   Lisa Wagner matches: {lisa_matches['lisa_matches']}")
        
        if lisa_matches['lisa_matches'] > 0:
            print(f"\n🎉 SUCCESS! Lisa Wagner now has match data!")
            print(f"📱 Test: https://rally-staging.up.railway.app/mobile/analyze-me")
        else:
            print(f"\n⚠️ Lisa Wagner still has no matches - may need to fix player IDs")
    
    conn.close()
    return imported_count

if __name__ == "__main__":
    count = import_cnswpl_matches_to_staging()
    print(f"\n🏁 Import complete: {count} matches imported")
