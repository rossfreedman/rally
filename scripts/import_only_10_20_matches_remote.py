#!/usr/bin/env python3
"""
Import Only 10/20 Wilmette H(3) Matches to Remote Database
===========================================================

Targeted import - only imports the 4 missing 10/20 matches.
Much faster than importing all 2296 matches.

Usage:
    python3 scripts/import_only_10_20_matches_remote.py staging
    python3 scripts/import_only_10_20_matches_remote.py production
"""

import sys
import os
import json
import subprocess

# Database URLs
STAGING_DB_URL = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"
PRODUCTION_DB_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/import_only_10_20_matches_remote.py [staging|production]")
        sys.exit(1)
    
    env = sys.argv[1].lower()
    
    if env == "staging":
        db_url = STAGING_DB_URL
        env_name = "staging"
    elif env == "production":
        db_url = PRODUCTION_DB_URL
        env_name = "production"
    else:
        print("❌ Error: Environment must be 'staging' or 'production'")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print(f"🚀 Importing 10/20 Matches to {env_name.upper()}")
    print(f"{'='*60}\n")
    
    # Load local JSON
    json_path = "data/leagues/CNSWPL/match_scores.json"
    if not os.path.exists(json_path):
        backups = sorted([f"data/leagues/CNSWPL/{f}" for f in os.listdir("data/leagues/CNSWPL") 
                          if f.startswith("match_scores_backup_")])
        if backups:
            json_path = backups[-1]
    
    if not os.path.exists(json_path):
        print(f"❌ JSON file not found: {json_path}")
        sys.exit(1)
    
    print(f"📄 Loading matches from: {json_path}")
    with open(json_path) as f:
        all_matches = json.load(f)
    
    # Filter to only 10/20 Wilmette H(3) matches
    target_matches = []
    for match in all_matches:
        if ('Wilmette H(3)' in match.get('Home Team', '') and 
            'Tennaqua H' in match.get('Away Team', '') and 
            '20-Oct-25' in match.get('Date', '')):
            target_matches.append(match)
    
    if not target_matches:
        print("❌ No target matches found in JSON")
        sys.exit(1)
    
    print(f"✅ Found {len(target_matches)} matches to import\n")
    
    # Create temporary JSON with only these matches
    temp_json = "/tmp/wilmette_h3_10_20_matches.json"
    with open(temp_json, 'w') as f:
        json.dump(target_matches, f, indent=2)
    
    print(f"📝 Created temp file: {temp_json}\n")
    
    # Set environment
    env_vars = {
        "DATABASE_URL": db_url,
        "DATABASE_PUBLIC_URL": db_url,
        "RAILWAY_ENVIRONMENT": ""
    }
    
    # Import
    cmd = f'python3 data/etl/import/import_match_scores.py CNSWPL --file {temp_json}'
    
    print(f"🔄 Importing {len(target_matches)} matches to {env_name}...\n")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            env=env_vars,
            check=True
        )
        print(f"\n✅ Import complete!")
        
        # Verify
        verify_script = f"""
import os
os.environ['DATABASE_URL'] = '{db_url}'
os.environ['DATABASE_PUBLIC_URL'] = '{db_url}'
import psycopg2

conn = psycopg2.connect('{db_url}')
cur = conn.cursor()
cur.execute(\"\"\"
    SELECT COUNT(*) FROM match_scores 
    WHERE league_id = (SELECT id FROM leagues WHERE league_id = 'CNSWPL') 
    AND match_date = '2025-10-20' 
    AND tenniscores_match_id LIKE 'nndz-WWk2OHdyZnhqQT09%'
\"\"\")
count = cur.fetchone()[0]
print(f'✅ 10/20 matches in database: {{count}}')
cur.close()
conn.close()
"""
        verify_file = "/tmp/verify_10_20.py"
        with open(verify_file, 'w') as f:
            f.write(verify_script)
        
        subprocess.run(f"python3 {verify_file}", shell=True, env=env_vars)
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Import failed: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        if os.path.exists(temp_json):
            os.remove(temp_json)

if __name__ == "__main__":
    main()

