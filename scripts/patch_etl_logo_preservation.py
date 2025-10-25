#!/usr/bin/env python3
"""
Fix ETL Club Upsert Functions to Preserve Logo Filenames

This script patches the upsert_club functions in the ETL import scripts
to preserve existing logo_filename values when upserting clubs.

The issue: ETL import scripts use upsert_club() which only handles name/league_id
but doesn't preserve logo_filename values that were manually set.

Solution: Modify upsert_club functions to preserve existing logo_filename values.
"""

import os
import re
from pathlib import Path

def patch_upsert_club_function(file_path):
    """Patch the upsert_club function in a file to preserve logo_filename"""
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if file already has logo preservation logic
    if "logo_filename" in content and "preserve" in content.lower():
        print(f"✅ {file_path} already has logo preservation logic")
        return True
    
    # Pattern to find the upsert_club function
    pattern = r'(def upsert_club\(cur, name, league_id\):.*?)(\n\ndef|\nclass|\nif __name__|\Z)'
    
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        print(f"❌ Could not find upsert_club function in {file_path}")
        return False
    
    original_function = match.group(1)
    
    # Create enhanced function that preserves logo_filename
    enhanced_function = '''def upsert_club(cur, name, league_id):
    """Upsert club and return ID, preserving existing logo_filename values."""
    if not name:
        return None
    
    # Check if clubs table has league_id column
    if column_exists(cur, "clubs", "league_id"):
        # Direct league_id column
        # First, check if club exists and has a logo_filename
        cur.execute("SELECT id, logo_filename FROM clubs WHERE name = %s AND league_id = %s", (name, league_id))
        existing = cur.fetchone()
        
        if existing:
            # Club exists, return its ID (preserve logo_filename)
            return existing[0]
        
        # Club doesn't exist, create it
        cur.execute("""
            INSERT INTO clubs (name, league_id) 
            VALUES (%s, %s) 
            ON CONFLICT (name, league_id) DO NOTHING 
            RETURNING id
        """, (name, league_id))
        result = cur.fetchone()
        if result:
            return result[0]
        
        # Get existing ID
        cur.execute("SELECT id FROM clubs WHERE name = %s AND league_id = %s", (name, league_id))
        return cur.fetchone()[0]
    else:
        # Use club_leagues junction table
        # First, check if club exists and has a logo_filename
        cur.execute("SELECT id, logo_filename FROM clubs WHERE name = %s", (name,))
        existing = cur.fetchone()
        
        if existing:
            # Club exists, ensure club-league relationship exists
            club_id = existing[0]
            cur.execute("SELECT 1 FROM club_leagues WHERE club_id = %s AND league_id = %s", (club_id, league_id))
            if not cur.fetchone():
                cur.execute("INSERT INTO club_leagues (club_id, league_id) VALUES (%s, %s)", (club_id, league_id))
            return club_id
        
        # Club doesn't exist, create it
        cur.execute("INSERT INTO clubs (name) VALUES (%s) ON CONFLICT (name) DO NOTHING RETURNING id", (name,))
        result = cur.fetchone()
        
        if result:
            # New club was created
            club_id = result[0]
        else:
            # Club already exists, get its ID
            cur.execute("SELECT id FROM clubs WHERE name = %s", (name,))
            club_id = cur.fetchone()[0]
        
        # Check if club-league relationship already exists
        cur.execute("SELECT 1 FROM club_leagues WHERE club_id = %s AND league_id = %s", (club_id, league_id))
        if not cur.fetchone():
            # Create club-league relationship only if it doesn't exist
            cur.execute("INSERT INTO club_leagues (club_id, league_id) VALUES (%s, %s)", (club_id, league_id))
        
        return club_id'''
    
    # Replace the function in the content
    new_content = content.replace(original_function, enhanced_function)
    
    # Write the patched content back
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print(f"✅ Patched {file_path} to preserve logo_filename values")
    return True

def main():
    """Patch all ETL import scripts to preserve club logo filenames"""
    
    # Files that contain upsert_club functions
    files_to_patch = [
        "data/etl/import/import_players.py",
        "data/etl/import/import_stats.py", 
        "data/etl/import/import_match_scores.py",
        "data/etl/import/import_utils.py",
        "data/etl/import/start_season.py"
    ]
    
    print("🔧 Patching ETL Import Scripts to Preserve Club Logo Filenames")
    print("=" * 70)
    
    patched_count = 0
    for file_path in files_to_patch:
        if patch_upsert_club_function(file_path):
            patched_count += 1
    
    print(f"\n✅ Successfully patched {patched_count}/{len(files_to_patch)} files")
    
    if patched_count > 0:
        print("\n🎯 What this fixes:")
        print("   - ETL imports will now preserve existing club logo_filename values")
        print("   - No more losing logos after ETL runs")
        print("   - Future ETL imports will maintain logo mappings")
        
        print("\n📋 Next steps:")
        print("   1. Test the patched scripts in staging")
        print("   2. Deploy to production")
        print("   3. Run ETL import to verify logos are preserved")
        
        print("\n⚠️  Important:")
        print("   - The current logo fix script already restored logos")
        print("   - These patches prevent future logo loss during ETL")
        print("   - No need to re-run the logo fix script unless ETL runs again")

if __name__ == "__main__":
    main()
