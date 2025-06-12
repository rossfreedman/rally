#!/usr/bin/env python3
"""
Analyze player ID mappings between local and Railway databases
"""

import sys
import os
import psycopg2
from urllib.parse import urlparse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_config import get_db

RAILWAY_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

def connect_to_railway():
    """Connect to Railway database"""
    parsed = urlparse(RAILWAY_URL)
    conn_params = {
        'dbname': parsed.path[1:],
        'user': parsed.username,
        'password': parsed.password,
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'sslmode': 'require',
        'connect_timeout': 10
    }
    return psycopg2.connect(**conn_params)

def analyze_player_mappings():
    """Analyze player ID mappings between local and Railway"""
    print("🔍 ANALYZING PLAYER ID MAPPINGS")
    print("="*60)
    
    with get_db() as local_conn:
        railway_conn = connect_to_railway()
        
        try:
            local_cursor = local_conn.cursor()
            railway_cursor = railway_conn.cursor()
            
            # Get local players with their info
            print("📋 Local players with unique identifiers...")
            local_cursor.execute("""
                SELECT id, tenniscores_player_id, first_name, last_name, pti
                FROM players 
                WHERE tenniscores_player_id IS NOT NULL
                ORDER BY id
                LIMIT 10
            """)
            local_players = local_cursor.fetchall()
            
            print(f"  Sample local players:")
            for player in local_players:
                print(f"    ID: {player[0]}, TC_ID: {player[1]}, Name: {player[2]} {player[3]}, PTI: {player[4]}")
            
            # Get Railway players with their info
            print(f"\n📋 Railway players with unique identifiers...")
            railway_cursor.execute("""
                SELECT id, tenniscores_player_id, first_name, last_name, pti
                FROM players 
                WHERE tenniscores_player_id IS NOT NULL
                ORDER BY id
                LIMIT 10
            """)
            railway_players = railway_cursor.fetchall()
            
            print(f"  Sample Railway players:")
            for player in railway_players:
                print(f"    ID: {player[0]}, TC_ID: {player[1]}, Name: {player[2]} {player[3]}, PTI: {player[4]}")
            
            # Create mapping dictionaries
            print(f"\n🔗 Creating mapping dictionaries...")
            
            # Local: tenniscores_player_id -> local_id
            local_cursor.execute("SELECT tenniscores_player_id, id FROM players WHERE tenniscores_player_id IS NOT NULL")
            local_tc_to_id = dict(local_cursor.fetchall())
            print(f"  Local players with TC IDs: {len(local_tc_to_id):,}")
            
            # Railway: tenniscores_player_id -> railway_id  
            railway_cursor.execute("SELECT tenniscores_player_id, id FROM players WHERE tenniscores_player_id IS NOT NULL")
            railway_tc_to_id = dict(railway_cursor.fetchall())
            print(f"  Railway players with TC IDs: {len(railway_tc_to_id):,}")
            
            # Find mapping overlap
            common_tc_ids = set(local_tc_to_id.keys()) & set(railway_tc_to_id.keys())
            print(f"  Common TC IDs between databases: {len(common_tc_ids):,}")
            
            # Check specific problem player_id
            print(f"\n🔍 Analyzing problem player_id 11748...")
            local_cursor.execute("SELECT * FROM players WHERE id = 11748")
            local_problem_player = local_cursor.fetchone()
            
            if local_problem_player:
                print(f"  Local player ID 11748: {local_problem_player[3]} {local_problem_player[4]} (TC: {local_problem_player[1]})")
                
                # Check if this TC ID exists in Railway
                tc_id = local_problem_player[1]
                if tc_id and tc_id in railway_tc_to_id:
                    railway_id = railway_tc_to_id[tc_id]
                    print(f"  Same player in Railway has ID: {railway_id}")
                else:
                    print(f"  ❌ Player with TC ID {tc_id} not found in Railway")
            else:
                print(f"  ❌ Player ID 11748 not found in local database")
            
            # Check player_history references
            print(f"\n📊 Analyzing player_history references...")
            local_cursor.execute("""
                SELECT DISTINCT player_id, COUNT(*) as record_count
                FROM player_history 
                GROUP BY player_id 
                ORDER BY record_count DESC 
                LIMIT 10
            """)
            ph_player_refs = local_cursor.fetchall()
            
            print(f"  Top player_history references (local):")
            for player_id, count in ph_player_refs:
                local_cursor.execute("SELECT first_name, last_name, tenniscores_player_id FROM players WHERE id = %s", (player_id,))
                player_info = local_cursor.fetchone()
                if player_info:
                    print(f"    Player ID {player_id}: {count:,} records - {player_info[0]} {player_info[1]} (TC: {player_info[2]})")
                else:
                    print(f"    Player ID {player_id}: {count:,} records - PLAYER NOT FOUND")
            
            # Create full mapping for migration
            print(f"\n🗺️  Creating full ID mapping...")
            local_to_railway_mapping = {}
            unmapped_count = 0
            
            for tc_id in local_tc_to_id:
                local_id = local_tc_to_id[tc_id]
                if tc_id in railway_tc_to_id:
                    railway_id = railway_tc_to_id[tc_id]
                    local_to_railway_mapping[local_id] = railway_id
                else:
                    unmapped_count += 1
            
            print(f"  Successfully mapped players: {len(local_to_railway_mapping):,}")
            print(f"  Unmapped players: {unmapped_count:,}")
            
            # Test specific mapping
            if 11748 in local_to_railway_mapping:
                print(f"  ✅ Player ID 11748 maps to Railway ID: {local_to_railway_mapping[11748]}")
            else:
                print(f"  ❌ Player ID 11748 cannot be mapped to Railway")
            
            return local_to_railway_mapping
            
        finally:
            railway_conn.close()

if __name__ == "__main__":
    mapping = analyze_player_mappings() 