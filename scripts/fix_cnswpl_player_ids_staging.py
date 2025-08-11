#!/usr/bin/env python3
"""
Fix CNSWPL Player IDs on Staging
================================

This script fixes the issue where staging database has old nndz- format CNSWPL player IDs
but the current players.json and match_history.json use cnswpl_ format IDs.

The fix:
1. Creates a mapping between old nndz- IDs and new cnswpl_ IDs based on player names
2. Updates the players table with correct cnswpl_ IDs  
3. Re-imports CNSWPL matches which will now work with consistent IDs

This resolves the mismatch where:
- Staging players table: nndz-WkM2eHhybi9qUT09 (Lisa Wagner)
- JSON files: cnswpl_2070e1ed22049df7 (Lisa Wagner)
"""

import json
import logging
import sys
from pathlib import Path

# Add project root to path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

from database_utils import execute_query, execute_update, execute_query_one

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_cnswpl_players_json():
    """Load the current CNSWPL players.json with cnswpl_ IDs"""
    json_path = project_root / "data/leagues/CNSWPL/players.json"
    
    if not json_path.exists():
        raise FileNotFoundError(f"CNSWPL players.json not found: {json_path}")
    
    with open(json_path, 'r') as f:
        players = json.load(f)
    
    logger.info(f"✅ Loaded {len(players)} players from CNSWPL players.json")
    return players

def get_staging_cnswpl_players():
    """Get current CNSWPL players from staging database with nndz- IDs"""
    query = """
        SELECT tenniscores_player_id, first_name, last_name, id, team_id, club_id, series_id, league_id
        FROM players 
        WHERE league_id = (SELECT id FROM leagues WHERE league_id = 'CNSWPL' OR league_name ILIKE '%CNSWPL%')
    """
    
    players = execute_query(query)
    logger.info(f"✅ Found {len(players)} CNSWPL players in staging database")
    
    return players

def create_id_mapping(staging_players, json_players):
    """Create mapping between old nndz- IDs and new cnswpl_ IDs based on name matching"""
    
    logger.info("🔗 Creating ID mapping between staging and JSON players...")
    
    # Create lookup dictionaries
    staging_by_name = {}
    for player in staging_players:
        full_name = f"{player['first_name']} {player['last_name']}".strip().lower()
        staging_by_name[full_name] = player
    
    json_by_name = {}  
    for player in json_players:
        full_name = f"{player.get('First Name', '')} {player.get('Last Name', '')}".strip().lower()
        json_by_name[full_name] = player
    
    # Create mapping
    id_mapping = {}  # old_nndz_id -> new_cnswpl_id
    matched_count = 0
    unmatched_staging = []
    unmatched_json = []
    
    for name, staging_player in staging_by_name.items():
        if name in json_by_name:
            old_id = staging_player['tenniscores_player_id']
            new_id = json_by_name[name].get('Player ID', '')
            
            if old_id and new_id:
                id_mapping[old_id] = new_id
                matched_count += 1
                logger.debug(f"   ✅ {name}: {old_id} → {new_id}")
            else:
                logger.warning(f"   ⚠️ Missing ID for {name}")
        else:
            unmatched_staging.append(name)
    
    # Find JSON players not in staging
    for name in json_by_name:
        if name not in staging_by_name:
            unmatched_json.append(name)
    
    logger.info(f"🎯 ID Mapping Results:")
    logger.info(f"   ✅ Matched players: {matched_count}")
    logger.info(f"   ❌ Unmatched staging players: {len(unmatched_staging)}")
    logger.info(f"   ❌ Unmatched JSON players: {len(unmatched_json)}")
    
    if unmatched_staging:
        logger.warning(f"Staging players not found in JSON: {unmatched_staging[:5]}...")
    
    if unmatched_json:
        logger.warning(f"JSON players not found in staging: {unmatched_json[:5]}...")
    
    return id_mapping

def update_player_ids(id_mapping):
    """Update player IDs in staging database"""
    
    if not id_mapping:
        logger.warning("❌ No ID mappings to update")
        return 0
    
    logger.info(f"🔄 Updating {len(id_mapping)} player IDs in staging database...")
    
    updated_count = 0
    errors = []
    
    for old_id, new_id in id_mapping.items():
        try:
            # Update the player's tenniscores_player_id
            result = execute_update("""
                UPDATE players 
                SET tenniscores_player_id = %s 
                WHERE tenniscores_player_id = %s
            """, [new_id, old_id])
            
            updated_count += 1
            logger.debug(f"   ✅ Updated {old_id} → {new_id}")
            
        except Exception as e:
            error_msg = f"Failed to update {old_id} → {new_id}: {e}"
            errors.append(error_msg)
            logger.error(f"   ❌ {error_msg}")
    
    logger.info(f"🎯 Update Results:")
    logger.info(f"   ✅ Successfully updated: {updated_count}")
    logger.info(f"   ❌ Errors: {len(errors)}")
    
    if errors:
        logger.error("Errors encountered:")
        for error in errors[:5]:  # Show first 5 errors
            logger.error(f"   - {error}")
    
    return updated_count

def update_associations(id_mapping):
    """Update user_player_associations with new player IDs"""
    
    logger.info(f"🔄 Updating user_player_associations...")
    
    updated_count = 0
    for old_id, new_id in id_mapping.items():
        try:
            execute_update("""
                UPDATE user_player_associations 
                SET tenniscores_player_id = %s 
                WHERE tenniscores_player_id = %s
            """, [new_id, old_id])
            
            updated_count += 1
            
        except Exception as e:
            logger.error(f"   ❌ Failed to update association {old_id} → {new_id}: {e}")
    
    logger.info(f"   ✅ Updated {updated_count} user associations")

def verify_fix():
    """Verify the fix worked by checking a sample player"""
    
    logger.info("🔍 Verifying fix...")
    
    # Check Lisa Wagner specifically
    lisa = execute_query_one("""
        SELECT tenniscores_player_id, first_name, last_name
        FROM players 
        WHERE first_name = 'Lisa' AND last_name = 'Wagner'
        AND league_id = (SELECT id FROM leagues WHERE league_id = 'CNSWPL')
    """)
    
    if lisa:
        player_id = lisa['tenniscores_player_id']
        logger.info(f"✅ Lisa Wagner ID after fix: {player_id}")
        
        if player_id.startswith('cnswpl_'):
            logger.info("🎉 SUCCESS: Player ID is now in correct cnswpl_ format")
            return True
        else:
            logger.error("❌ FAILED: Player ID is still in wrong format")
            return False
    else:
        logger.error("❌ Lisa Wagner not found")
        return False

def main():
    """Main function"""
    logger.info("🎯 CNSWPL Player ID Fix Script")
    logger.info("=" * 50)
    
    try:
        # 1. Load data
        logger.info("📊 Step 1: Loading player data...")
        json_players = load_cnswpl_players_json()
        staging_players = get_staging_cnswpl_players()
        
        # 2. Create mapping
        logger.info("🔗 Step 2: Creating ID mappings...")
        id_mapping = create_id_mapping(staging_players, json_players)
        
        if not id_mapping:
            logger.error("❌ No ID mappings created. Cannot proceed.")
            return False
        
        # 3. Show sample mapping
        logger.info("📋 Sample mappings:")
        for i, (old_id, new_id) in enumerate(list(id_mapping.items())[:5]):
            logger.info(f"   {old_id} → {new_id}")
        
        # 4. Confirm before proceeding
        print(f"\n🚨 CONFIRMATION REQUIRED:")
        print(f"   About to update {len(id_mapping)} CNSWPL player IDs")
        print(f"   This will change nndz- format to cnswpl_ format")
        print(f"   This is IRREVERSIBLE on the staging database")
        
        confirm = input("\nProceed with update? (yes/no): ").strip().lower()
        if confirm != 'yes':
            logger.info("❌ Update cancelled by user")
            return False
        
        # 5. Update player IDs
        logger.info("🔄 Step 3: Updating player IDs...")
        updated_count = update_player_ids(id_mapping)
        
        # 6. Update associations
        logger.info("🔄 Step 4: Updating user associations...")
        update_associations(id_mapping)
        
        # 7. Verify fix
        logger.info("🔍 Step 5: Verifying fix...")
        success = verify_fix()
        
        if success:
            logger.info("🎉 CNSWPL Player ID fix completed successfully!")
            logger.info("📝 Next steps:")
            logger.info("   1. Re-run match import to import CNSWPL matches")
            logger.info("   2. Verify match data appears in UI")
            return True
        else:
            logger.error("❌ Fix verification failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Script failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
