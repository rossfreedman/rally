#!/usr/bin/env python3
"""
Generate tenniscores_match_id fix script for PRODUCTION database
This script connects to production DB and generates the correct UPDATE statements
"""

import psycopg2
import psycopg2.extras
from collections import defaultdict
import hashlib
import base64
import os

def get_production_connection():
    """Connect to production database"""
    # Railway production DB URL
    db_url = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"
    
    conn = psycopg2.connect(db_url)
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    return conn

def generate_base_id(match_date, home_team, away_team):
    """Generate base ID for team matchup - same logic as local"""
    matchup_string = f"{match_date}_{home_team}_vs_{away_team}"
    hash_object = hashlib.md5(matchup_string.encode())
    hash_hex = hash_object.hexdigest()
    base64_hash = base64.b64encode(bytes.fromhex(hash_hex)).decode()
    return f"nndz-{base64_hash}"

def main():
    print("🔍 Analyzing PRODUCTION database for tenniscores_match_id fix...")
    print("=" * 60)
    
    conn = get_production_connection()
    cursor = conn.cursor()
    
    # Find all matches missing tenniscores_match_id
    cursor.execute("""
        SELECT id, 
               TO_CHAR(match_date, 'DD-Mon-YY') as match_date,
               home_team, 
               away_team,
               tenniscores_match_id
        FROM match_scores 
        WHERE tenniscores_match_id IS NULL OR tenniscores_match_id = ''
        ORDER BY match_date, home_team, away_team, id
    """)
    
    missing_matches = cursor.fetchall()
    print(f"📊 Found {len(missing_matches)} matches missing tenniscores_match_id")
    
    if len(missing_matches) == 0:
        print("✅ No matches need fixing!")
        return
    
    # Group by team matchups
    matchups = defaultdict(list)
    for match in missing_matches:
        key = (match['match_date'], match['home_team'], match['away_team'])
        matchups[key].append(match)
    
    print(f"📋 Found {len(matchups)} unique team matchups")
    
    # Generate fix script
    fix_script = """-- Fix missing tenniscores_match_id values in PRODUCTION
-- Generated automatically based on production database analysis
-- This assigns court numbers based on database ID order within team matchups

BEGIN;

"""
    
    updates_count = 0
    
    for (match_date, home_team, away_team), matches in matchups.items():
        # Generate base ID for this matchup
        base_id = generate_base_id(match_date, home_team, away_team)
        
        # Sort matches by ID to ensure consistent court assignment
        matches.sort(key=lambda x: x['id'])
        
        # Generate LINE IDs
        for i, match in enumerate(matches):
            line_number = (i % 4) + 1  # Court 1-4
            tenniscores_match_id = f"{base_id}_Line{line_number}"
            
            fix_script += f"UPDATE match_scores SET tenniscores_match_id = '{tenniscores_match_id}' WHERE id = {match['id']};\n"
            updates_count += 1
    
    fix_script += f"""
COMMIT;

-- Verify the fix
SELECT 
    COUNT(*) as total_matches,
    COUNT(CASE WHEN tenniscores_match_id IS NOT NULL AND tenniscores_match_id != '' THEN 1 END) as has_match_id,
    ROUND(COUNT(CASE WHEN tenniscores_match_id IS NOT NULL AND tenniscores_match_id != '' THEN 1 END) * 100.0 / COUNT(*), 2) as percentage
FROM match_scores;
"""
    
    # Write fix script
    output_file = "scripts/fix_production_tenniscores_match_id_REAL.sql"
    with open(output_file, 'w') as f:
        f.write(fix_script)
    
    print(f"✅ Generated fix script: {output_file}")
    print(f"📊 Total UPDATE statements: {updates_count}")
    print(f"🎯 Expected result: {updates_count} records updated to 100% coverage")
    
    conn.close()
    
    # Show sample of what will be updated
    print("\n🔍 Sample updates to be applied:")
    print("-" * 40)
    sample_lines = fix_script.split('\n')[5:10]  # Skip header, show first 5 updates
    for line in sample_lines:
        if line.strip() and 'UPDATE' in line:
            print(f"  {line}")
    print("  ...")

if __name__ == "__main__":
    main()
