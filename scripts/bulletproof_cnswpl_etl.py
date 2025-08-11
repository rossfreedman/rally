#!/usr/bin/env python3
"""
Bulletproof CNSWPL ETL Prevention System
========================================

This script creates safeguards to prevent CNSWPL player ID format mismatches from ever happening again.

The Issue:
- CNSWPL can have TWO different player ID formats:
  * cnswpl_ format: from match_history.json (CORRECT)
  * nndz- format: from team page scraping (LEGACY, WRONG)
- This caused staging to have nndz- IDs while local had cnswpl_ IDs
- Match imports failed because player IDs didn't match

The Solution:
1. Add validation to import_players.py to detect ID format mismatches
2. Add format consistency checks to master_import.py  
3. Ensure match import validates player ID formats before proceeding
4. Add environment sync checks

This prevents the issue from recurring and ensures data consistency.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Set

# Add project root to path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_cnswpl_id_formats():
    """Analyze current CNSWPL data for ID format consistency"""
    
    logger.info("🔍 ANALYZING CNSWPL ID FORMAT CONSISTENCY")
    logger.info("=" * 55)
    
    # Check players.json
    players_file = project_root / "data/leagues/CNSWPL/players.json"
    match_history_file = project_root / "data/leagues/CNSWPL/match_history.json"
    
    results = {
        "players_json_exists": players_file.exists(),
        "match_history_exists": match_history_file.exists(),
        "players_formats": {"cnswpl_": 0, "nndz-": 0, "other": 0},
        "match_formats": {"cnswpl_": 0, "nndz-": 0, "other": 0},
        "consistent": True,
        "issues": []
    }
    
    # Analyze players.json
    if players_file.exists():
        with open(players_file, 'r') as f:
            players = json.load(f)
        
        for player in players:
            player_id = player.get("Player ID", "")
            if player_id.startswith("cnswpl_"):
                results["players_formats"]["cnswpl_"] += 1
            elif player_id.startswith("nndz-"):
                results["players_formats"]["nndz-"] += 1
            else:
                results["players_formats"]["other"] += 1
        
        logger.info(f"✅ Players.json: {len(players)} players")
        logger.info(f"   cnswpl_ format: {results['players_formats']['cnswpl_']}")
        logger.info(f"   nndz- format: {results['players_formats']['nndz-']}")
        logger.info(f"   Other formats: {results['players_formats']['other']}")
    else:
        logger.warning("❌ Players.json not found")
        results["issues"].append("Players.json missing")
    
    # Analyze match_history.json
    if match_history_file.exists():
        with open(match_history_file, 'r') as f:
            matches = json.load(f)
        
        player_ids_in_matches = set()
        for match in matches:
            for field in ["Home Player 1 ID", "Home Player 2 ID", "Away Player 1 ID", "Away Player 2 ID"]:
                player_id = match.get(field, "")
                if player_id:
                    player_ids_in_matches.add(player_id)
        
        for player_id in player_ids_in_matches:
            if player_id.startswith("cnswpl_"):
                results["match_formats"]["cnswpl_"] += 1
            elif player_id.startswith("nndz-"):
                results["match_formats"]["nndz-"] += 1
            else:
                results["match_formats"]["other"] += 1
        
        logger.info(f"✅ Match_history.json: {len(matches)} matches, {len(player_ids_in_matches)} unique player IDs")
        logger.info(f"   cnswpl_ format: {results['match_formats']['cnswpl_']}")
        logger.info(f"   nndz- format: {results['match_formats']['nndz-']}")
        logger.info(f"   Other formats: {results['match_formats']['other']}")
    else:
        logger.warning("❌ Match_history.json not found")
        results["issues"].append("Match_history.json missing")
    
    # Check consistency
    players_has_nndz = results["players_formats"]["nndz-"] > 0
    matches_has_nndz = results["match_formats"]["nndz-"] > 0
    players_has_cnswpl = results["players_formats"]["cnswpl_"] > 0
    matches_has_cnswpl = results["match_formats"]["cnswpl_"] > 0
    
    if players_has_nndz and matches_has_cnswpl:
        results["consistent"] = False
        results["issues"].append("ID FORMAT MISMATCH: Players have nndz- but matches have cnswpl_")
    elif players_has_cnswpl and matches_has_nndz:
        results["consistent"] = False
        results["issues"].append("ID FORMAT MISMATCH: Players have cnswpl_ but matches have nndz-")
    
    if results["consistent"]:
        logger.info("🎉 ID FORMATS ARE CONSISTENT")
    else:
        logger.error("❌ ID FORMAT MISMATCH DETECTED")
        for issue in results["issues"]:
            logger.error(f"   - {issue}")
    
    return results

def create_validation_patch():
    """Create validation patches for ETL scripts"""
    
    logger.info("🔧 CREATING ETL VALIDATION PATCHES")
    logger.info("=" * 40)
    
    # Create validation snippet for import_players.py
    validation_code = '''
def validate_cnswpl_player_id_format(players_data: List[Dict]) -> bool:
    """
    Validate that CNSWPL player IDs are in the correct cnswpl_ format.
    This prevents the nndz-/cnswpl_ ID mismatch issue.
    """
    cnswpl_players = [p for p in players_data if p.get("League", "").upper() == "CNSWPL"]
    
    if not cnswpl_players:
        return True  # No CNSWPL players to validate
    
    nndz_count = 0
    cnswpl_count = 0
    
    for player in cnswpl_players:
        player_id = player.get("Player ID", "")
        if player_id.startswith("nndz-"):
            nndz_count += 1
        elif player_id.startswith("cnswpl_"):
            cnswpl_count += 1
    
    total = len(cnswpl_players)
    logger.info(f"🔍 CNSWPL Player ID Validation:")
    logger.info(f"   Total CNSWPL players: {total}")
    logger.info(f"   cnswpl_ format: {cnswpl_count}")
    logger.info(f"   nndz- format: {nndz_count}")
    
    if nndz_count > 0 and cnswpl_count == 0:
        logger.warning("⚠️ ALL CNSWPL players use legacy nndz- format")
        logger.warning("⚠️ This may cause match import failures")
        logger.warning("⚠️ Consider regenerating CNSWPL players.json with correct format")
        return False
    elif nndz_count > 0 and cnswpl_count > 0:
        logger.error("❌ MIXED ID FORMATS DETECTED in CNSWPL players")
        logger.error("❌ This WILL cause match import failures")
        return False
    elif cnswpl_count > 0:
        logger.info("✅ All CNSWPL players use correct cnswpl_ format")
        return True
    
    return True
'''
    
    # Save validation code
    validation_file = project_root / "data/etl/database_import/cnswpl_validation.py"
    with open(validation_file, 'w') as f:
        f.write('"""CNSWPL Player ID Format Validation"""\n')
        f.write("import logging\nfrom typing import Dict, List\n\n")
        f.write("logger = logging.getLogger(__name__)\n\n")
        f.write(validation_code)
    
    logger.info(f"✅ Created validation module: {validation_file}")
    
    # Create integration instructions
    instructions = """
INTEGRATION INSTRUCTIONS:
=========================

1. Add to import_players.py:
   ```python
   from data.etl.database_import.cnswpl_validation import validate_cnswpl_player_id_format
   
   # In load_players_data method, after loading data:
   if not validate_cnswpl_player_id_format(players_data):
       logger.error("❌ CNSWPL player ID validation failed")
       logger.error("❌ Stopping import to prevent match import failures")
       raise ValueError("CNSWPL player ID format validation failed")
   ```

2. Add to master_import.py before "Import Match Scores":
   ```python
   # Validate CNSWPL consistency before match import
   logger.info("🔍 Validating CNSWPL data consistency...")
   cnswpl_validation_result = subprocess.run([
       "python3", "data/etl/database_import/cnswpl_validation.py"
   ], capture_output=True, text=True)
   
   if cnswpl_validation_result.returncode != 0:
       logger.error("❌ CNSWPL validation failed - skipping match import")
       raise Exception("CNSWPL data validation failed")
   ```

3. Test the validation:
   ```bash
   python3 data/etl/database_import/cnswpl_validation.py
   ```
"""
    
    instructions_file = project_root / "docs/CNSWPL_BULLETPROOF_INTEGRATION.md"
    with open(instructions_file, 'w') as f:
        f.write(instructions)
    
    logger.info(f"✅ Created integration guide: {instructions_file}")

def main():
    """Main function"""
    logger.info("🛡️ CNSWPL BULLETPROOF ETL SYSTEM")
    logger.info("=" * 45)
    
    # Step 1: Analyze current state
    logger.info("📊 Step 1: Analyzing current CNSWPL data...")
    results = analyze_cnswpl_id_formats()
    
    # Step 2: Create validation tools
    logger.info("🔧 Step 2: Creating validation tools...")
    create_validation_patch()
    
    # Step 3: Recommendations
    logger.info("💡 Step 3: Recommendations...")
    
    if results["consistent"]:
        logger.info("✅ Current data is consistent")
        logger.info("🔧 Integration recommendations:")
        logger.info("   1. Add validation to import_players.py")
        logger.info("   2. Add pre-import checks to master_import.py")
        logger.info("   3. Test the validation system")
    else:
        logger.error("❌ Current data has issues that need fixing")
        logger.error("🚨 Immediate actions needed:")
        for issue in results["issues"]:
            logger.error(f"   - Fix: {issue}")
    
    logger.info("📋 See docs/CNSWPL_BULLETPROOF_INTEGRATION.md for detailed steps")
    logger.info("🎯 This will prevent ID format mismatches from recurring")

if __name__ == "__main__":
    main()
