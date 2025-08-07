#!/usr/bin/env python3
"""
Step 2: Create backup of current tenniscores_match_id values before applying fix
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from database_utils import execute_query
from datetime import datetime

def create_backup():
    """Create backup of records that will be modified"""
    
    print("💾 Step 2: Creating Backup Before Fix")
    print("=" * 60)
    
    # Get all records that will be modified (those with NULL or empty tenniscores_match_id)
    backup_query = """
        SELECT 
            id,
            tenniscores_match_id,
            TO_CHAR(match_date, 'YYYY-MM-DD') as match_date,
            home_team,
            away_team
        FROM match_scores 
        WHERE tenniscores_match_id IS NULL OR tenniscores_match_id = ''
        ORDER BY id
    """
    
    print("📋 Backing up records that will be modified...")
    records_to_backup = execute_query(backup_query)
    
    if not records_to_backup:
        print("✅ No records need backup - all already have tenniscores_match_id")
        return
    
    # Create backup SQL file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"scripts/backup_tenniscores_match_id_{timestamp}.sql"
    
    backup_content = f"""-- Backup of tenniscores_match_id values before fix
-- Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- Records: {len(records_to_backup)}

-- To restore these values if needed:
BEGIN;

"""
    
    for record in records_to_backup:
        current_value = record['tenniscores_match_id']
        if current_value is None:
            backup_content += f"UPDATE match_scores SET tenniscores_match_id = NULL WHERE id = {record['id']};\n"
        else:
            backup_content += f"UPDATE match_scores SET tenniscores_match_id = '{current_value}' WHERE id = {record['id']};\n"
    
    backup_content += """
COMMIT;

-- Verification query:
SELECT 
    COUNT(*) as total_matches,
    COUNT(CASE WHEN tenniscores_match_id IS NOT NULL AND tenniscores_match_id != '' THEN 1 END) as has_match_id,
    ROUND(COUNT(CASE WHEN tenniscores_match_id IS NOT NULL AND tenniscores_match_id != '' THEN 1 END) * 100.0 / COUNT(*), 2) as percentage
FROM match_scores;
"""
    
    with open(backup_filename, 'w') as f:
        f.write(backup_content)
    
    print(f"✅ Backup created: {backup_filename}")
    print(f"📊 Backed up {len(records_to_backup)} records")
    
    # Show sample of what will be changed
    print(f"\n📋 Sample of records in backup:")
    for i, record in enumerate(records_to_backup[:5]):
        current = record['tenniscores_match_id'] if record['tenniscores_match_id'] else 'NULL'
        print(f"  ID {record['id']}: {current} | {record['match_date']} | {record['home_team']} vs {record['away_team']}")
    
    if len(records_to_backup) > 5:
        print(f"  ... and {len(records_to_backup) - 5} more records")
    
    print(f"\n🔄 If you need to restore, run: {backup_filename}")

if __name__ == "__main__":
    create_backup()
