#!/usr/bin/env python3
"""
Manual Fix Template for Specific Null Player IDs
Update this script with specific player names and match IDs
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query_one, execute_update

# Manual fixes - update these with actual data
FIXES = [
    {
        "match_id": 815833,
        "field": "away_player_2_id", 
        "player_name": "Mariano Martinez",
        "resolved_id": "nndz-WkNHeHdiZjlqUT09"
    },
    # Add more fixes here...
]

def apply_manual_fixes(dry_run=True):
    """Apply the manual fixes"""
    print(f"🔧 Applying manual fixes (DRY RUN: {dry_run})")
    
    for fix in FIXES:
        match_id = fix["match_id"]
        field = fix["field"]
        player_name = fix["player_name"]
        resolved_id = fix["resolved_id"]
        
        print(f"  📝 Match {match_id}: {field} = '{player_name}' → {resolved_id}")
        
        if not dry_run:
            query = f"UPDATE match_scores SET {field} = %s WHERE id = %s"
            execute_update(query, [resolved_id, match_id])
            print(f"    ✅ Updated!")
        else:
            print(f"    🚀 Would update (dry run)")

if __name__ == "__main__":
    apply_manual_fixes(dry_run=True)
