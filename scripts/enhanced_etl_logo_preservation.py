#!/usr/bin/env python3
"""
Enhanced ETL Club Import with Logo Preservation

This script modifies the ETL import process to preserve club logo filenames
when clubs are recreated during season imports.

The issue: end_season.py deletes clubs, then start_season.py recreates them
without preserving the logo_filename values that were manually set.

Solution: Backup logo filenames before ETL, restore them after ETL.
"""

import os
import psycopg2
import json
from datetime import datetime
from dotenv import load_dotenv

def backup_club_logos(db_url):
    """Backup all club logo filenames before ETL import"""
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id, name, logo_filename FROM clubs WHERE logo_filename IS NOT NULL")
        clubs_with_logos = cursor.fetchall()
        
        backup_data = {}
        for club_id, name, logo_filename in clubs_with_logos:
            backup_data[name] = {
                'id': club_id,
                'logo_filename': logo_filename
            }
        
        # Save backup to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"data/etl/logs/club_logos_backup_{timestamp}.json"
        
        os.makedirs(os.path.dirname(backup_file), exist_ok=True)
        
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        print(f"✅ Backed up {len(backup_data)} club logos to {backup_file}")
        return backup_file
        
    finally:
        cursor.close()
        conn.close()

def restore_club_logos(db_url, backup_file):
    """Restore club logo filenames after ETL import"""
    if not os.path.exists(backup_file):
        print(f"❌ Backup file not found: {backup_file}")
        return
    
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    try:
        with open(backup_file, 'r') as f:
            backup_data = json.load(f)
        
        restored_count = 0
        for club_name, data in backup_data.items():
            logo_filename = data['logo_filename']
            
            # Strip path prefix if present
            if logo_filename.startswith("static/images/clubs/"):
                logo_filename = logo_filename.replace("static/images/clubs/", "")
            
            cursor.execute("""
                UPDATE clubs 
                SET logo_filename = %s 
                WHERE name = %s AND logo_filename IS NULL
            """, (logo_filename, club_name))
            
            if cursor.rowcount > 0:
                restored_count += 1
                print(f"✅ Restored logo for {club_name}: {logo_filename}")
        
        conn.commit()
        print(f"✅ Restored {restored_count} club logos from backup")
        
    finally:
        cursor.close()
        conn.close()

def enhance_upsert_club_functions():
    """Create enhanced upsert functions that preserve logo filenames"""
    
    enhanced_upsert_club = '''
def upsert_club_with_logo_preservation(cur, name, league_id):
    """Enhanced upsert club that preserves existing logo filenames"""
    if not name:
        return None
    
    # First, check if club already exists and has a logo
    cur.execute("SELECT id, logo_filename FROM clubs WHERE name = %s AND league_id = %s", (name, league_id))
    existing = cur.fetchone()
    
    if existing:
        # Club exists, return its ID (preserve logo_filename)
        return existing[0]
    
    # Check if clubs table has league_id column
    if column_exists(cur, "clubs", "league_id"):
        # Direct league_id column
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
        # First, try to insert the club
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
        
        return club_id
'''
    
    print("Enhanced upsert_club function created (see code above)")
    print("This function should be integrated into the ETL import scripts")

def main():
    """Main function to demonstrate logo preservation workflow"""
    load_dotenv()
    db_url = os.getenv('DATABASE_URL')
    
    if not db_url:
        print("❌ DATABASE_URL environment variable not set")
        return
    
    print("🔄 Club Logo Preservation Workflow")
    print("=" * 50)
    
    # Step 1: Backup logos before ETL
    print("\n1. Backing up club logos...")
    backup_file = backup_club_logos(db_url)
    
    # Step 2: Show enhanced upsert function
    print("\n2. Enhanced upsert function:")
    enhance_upsert_club_functions()
    
    # Step 3: Demonstrate restore process
    print("\n3. To restore logos after ETL:")
    print(f"   restore_club_logos('{db_url}', '{backup_file}')")
    
    print("\n✅ Logo preservation workflow ready!")
    print("\nNext steps:")
    print("1. Integrate enhanced upsert function into ETL scripts")
    print("2. Add backup/restore calls to master import scripts")
    print("3. Test with staging environment")

if __name__ == "__main__":
    main()
