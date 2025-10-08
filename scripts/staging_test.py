#!/usr/bin/env python3
"""
Simple test script for staging environment.
"""

import os
import sys
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

def test_staging():
    print("🧪 STAGING TEST")
    print("=" * 30)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Environment: {os.environ.get('RAILWAY_ENVIRONMENT', 'unknown')}")
    print()
    
    # Test 1: Basic imports
    print("1️⃣ Testing basic imports...")
    try:
        from database_config import get_db
        print("   ✅ database_config imported")
    except Exception as e:
        print(f"   ❌ database_config failed: {e}")
        return False
    
    # Test 2: Database connection
    print("2️⃣ Testing database connection...")
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM players")
                count = cur.fetchone()[0]
                print(f"   ✅ Database connected, {count:,} players in database")
    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
        return False
    
    # Test 3: Load players data
    print("3️⃣ Testing players data load...")
    try:
        with open("data/leagues/APTA_CHICAGO/players.json", 'r') as f:
            players_data = json.load(f)
        print(f"   ✅ Loaded {len(players_data):,} players")
    except Exception as e:
        print(f"   ❌ Failed to load players data: {e}")
        return False
    
    # Test 4: Test single player import
    print("4️⃣ Testing single player import...")
    try:
        from data.etl.import.import_players import upsert_player
        
        with get_db() as conn:
            with conn.cursor() as cur:
                # Get league ID
                cur.execute("SELECT id FROM leagues WHERE league_id = 'APTA_CHICAGO'")
                league_result = cur.fetchone()
                if not league_result:
                    print("   ❌ APTA_CHICAGO league not found")
                    return False
                
                league_id = league_result[0]
                print(f"   ✅ Found league ID: {league_id}")
                
                # Test with first player
                test_player = players_data[0]
                print(f"   Testing with: {test_player.get('First Name')} {test_player.get('Last Name')}")
                
                result = upsert_player(cur, league_id, test_player)
                print(f"   ✅ upsert_player result: {result}")
                
                # Rollback to avoid changes
                conn.rollback()
                print("   ✅ Rolled back changes")
                
    except Exception as e:
        print(f"   ❌ Single player import failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("✅ All tests passed!")
    return True

if __name__ == "__main__":
    success = test_staging()
    sys.exit(0 if success else 1)
