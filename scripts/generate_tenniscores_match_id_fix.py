#!/usr/bin/env python3
"""
Generate SQL script to fix missing tenniscores_match_id values in production
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from database_utils import execute_query
import hashlib

def generate_base_id(match_date, home_team, away_team):
    """Generate a base ID for a team matchup using same pattern as existing data"""
    
    # Create a unique string for this team matchup
    matchup_string = f"{match_date}_{home_team}_{away_team}"
    
    # Generate a hash similar to existing patterns (base64-like)
    hash_obj = hashlib.md5(matchup_string.encode())
    hash_hex = hash_obj.hexdigest()
    
    # Convert to base64-like format (similar to existing nndz- patterns)
    import base64
    base64_hash = base64.b64encode(hash_hex.encode()).decode()
    
    # Make it look like existing patterns: nndz-{hash}
    base_id = f"nndz-{base64_hash[:20]}"
    
    return base_id

def analyze_missing_data():
    """Analyze which matches need tenniscores_match_id values"""
    
    print("🔍 Analyzing Missing tenniscores_match_id Data")
    print("=" * 60)
    
    # Find all matches without tenniscores_match_id
    missing_query = """
        SELECT 
            id,
            TO_CHAR(match_date, 'YYYY-MM-DD') as match_date,
            home_team,
            away_team,
            tenniscores_match_id
        FROM match_scores 
        WHERE tenniscores_match_id IS NULL OR tenniscores_match_id = ''
        ORDER BY match_date DESC, id ASC
    """
    
    missing_matches = execute_query(missing_query)
    print(f"📊 Found {len(missing_matches)} matches missing tenniscores_match_id")
    
    if not missing_matches:
        print("✅ All matches already have tenniscores_match_id values!")
        return []
    
    # Group by team matchup to assign court numbers
    from collections import defaultdict
    matchups = defaultdict(list)
    
    for match in missing_matches:
        matchup_key = f"{match['match_date']}_{match['home_team']}_{match['away_team']}"
        matchups[matchup_key].append(match)
    
    print(f"📊 {len(matchups)} unique team matchups need tenniscores_match_id")
    
    # Generate fix SQL
    fix_statements = []
    
    for matchup_key, matches in matchups.items():
        # Sort by database ID to assign courts consistently
        matches.sort(key=lambda m: m['id'])
        
        # Generate base ID for this matchup
        match_date = matches[0]['match_date'] 
        home_team = matches[0]['home_team']
        away_team = matches[0]['away_team']
        base_id = generate_base_id(match_date, home_team, away_team)
        
        print(f"\n🎯 {match_date} | {home_team} vs {away_team}")
        print(f"   Base ID: {base_id}")
        print(f"   {len(matches)} matches to fix")
        
        # Assign court numbers
        for i, match in enumerate(matches):
            court_number = (i % 4) + 1  # Courts 1-4
            tenniscores_match_id = f"{base_id}_Line{court_number}"
            
            fix_sql = f"UPDATE match_scores SET tenniscores_match_id = '{tenniscores_match_id}' WHERE id = {match['id']};"
            fix_statements.append(fix_sql)
            
            print(f"   Match ID {match['id']}: Court {court_number} -> {tenniscores_match_id}")
    
    return fix_statements

def generate_sql_file(fix_statements):
    """Generate SQL file with all fix statements"""
    
    if not fix_statements:
        print("✅ No fixes needed!")
        return
    
    sql_content = """-- Fix missing tenniscores_match_id values
-- Generated automatically based on local database patterns
-- This assigns court numbers based on database ID order within team matchups

BEGIN;

"""
    
    sql_content += "\n".join(fix_statements)
    
    sql_content += """

COMMIT;

-- Verify the fix
SELECT 
    COUNT(*) as total_matches,
    COUNT(CASE WHEN tenniscores_match_id IS NOT NULL AND tenniscores_match_id != '' THEN 1 END) as has_match_id,
    ROUND(COUNT(CASE WHEN tenniscores_match_id IS NOT NULL AND tenniscores_match_id != '' THEN 1 END) * 100.0 / COUNT(*), 2) as percentage
FROM match_scores;
"""
    
    filename = "scripts/fix_production_tenniscores_match_id.sql"
    with open(filename, 'w') as f:
        f.write(sql_content)
    
    print(f"\n✅ Generated SQL fix file: {filename}")
    print(f"📊 {len(fix_statements)} UPDATE statements created")
    print("\n🚀 To apply the fix:")
    print("1. Review the generated SQL file")
    print("2. Run it against the production database")
    print("3. Verify all court analysis pages work correctly")

def main():
    fix_statements = analyze_missing_data()
    generate_sql_file(fix_statements)

if __name__ == "__main__":
    main()
