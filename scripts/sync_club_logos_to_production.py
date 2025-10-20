#!/usr/bin/env python3
"""
Sync club logo_filename values from local database to production database.

This script:
1. Reads club records from local database
2. Compares with production database
3. Backs up production values
4. Updates production with local values
5. Provides detailed summary

Usage:
  python sync_club_logos_to_production.py --yes  # Auto-confirm updates
  python sync_club_logos_to_production.py        # Prompt for confirmation
"""

import os
import sys
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Database URLs
LOCAL_DB_URL = os.getenv("DATABASE_URL", "postgresql://localhost/rally")
PRODUCTION_DB_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

# Ensure URLs use postgresql://
if LOCAL_DB_URL.startswith("postgres://"):
    LOCAL_DB_URL = LOCAL_DB_URL.replace("postgres://", "postgresql://", 1)
if PRODUCTION_DB_URL.startswith("postgres://"):
    PRODUCTION_DB_URL = PRODUCTION_DB_URL.replace("postgres://", "postgresql://", 1)


def connect_to_db(db_url, db_name):
    """Connect to database"""
    print(f"Connecting to {db_name} database...")
    conn = psycopg2.connect(db_url)
    print(f"✓ Connected to {db_name}")
    return conn


def get_club_logos(conn):
    """Get club ID, name, and logo_filename from database"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, logo_filename 
        FROM clubs 
        ORDER BY id
    """)
    results = cursor.fetchall()
    cursor.close()
    
    # Return as dictionary with id as key
    return {row[0]: {'id': row[0], 'name': row[1], 'logo_filename': row[2]} for row in results}


def main():
    # Check for --yes flag
    auto_confirm = '--yes' in sys.argv
    
    print("\n" + "="*80)
    print("SYNC CLUB LOGO FILENAMES: LOCAL → PRODUCTION")
    print("="*80 + "\n")
    
    # Connect to both databases
    try:
        local_conn = connect_to_db(LOCAL_DB_URL, "LOCAL")
        prod_conn = connect_to_db(PRODUCTION_DB_URL, "PRODUCTION")
    except Exception as e:
        print(f"\n❌ ERROR: Could not connect to databases: {e}")
        return
    
    print()
    
    # Get club data from both databases
    print("Fetching club data from LOCAL database...")
    local_clubs = get_club_logos(local_conn)
    print(f"✓ Found {len(local_clubs)} clubs in LOCAL\n")
    
    print("Fetching club data from PRODUCTION database...")
    prod_clubs = get_club_logos(prod_conn)
    print(f"✓ Found {len(prod_clubs)} clubs in PRODUCTION\n")
    
    # Compare and identify differences
    print("="*80)
    print("COMPARING LOGO FILENAMES")
    print("="*80 + "\n")
    
    differences = []
    for club_id, local_club in local_clubs.items():
        if club_id in prod_clubs:
            prod_club = prod_clubs[club_id]
            local_logo = local_club['logo_filename']
            prod_logo = prod_club['logo_filename']
            
            if local_logo != prod_logo:
                differences.append({
                    'id': club_id,
                    'name': local_club['name'],
                    'local_logo': local_logo,
                    'prod_logo': prod_logo
                })
    
    if not differences:
        print("✓ No differences found! All logo_filename values match.\n")
        local_conn.close()
        prod_conn.close()
        return
    
    print(f"Found {len(differences)} clubs with different logo_filename values:\n")
    
    for diff in differences:
        print(f"Club ID {diff['id']}: {diff['name']}")
        print(f"  PRODUCTION (old): {diff['prod_logo']}")
        print(f"  LOCAL (new):      {diff['local_logo']}")
        print()
    
    # Create backup
    print("="*80)
    print("CREATING BACKUP")
    print("="*80 + "\n")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backups/club_logos_production_backup_{timestamp}.json"
    
    # Ensure backups directory exists
    os.makedirs("backups", exist_ok=True)
    
    backup_data = {
        'timestamp': timestamp,
        'clubs': [prod_clubs[diff['id']] for diff in differences]
    }
    
    with open(backup_filename, 'w') as f:
        json.dump(backup_data, f, indent=2)
    
    print(f"✓ Backup saved to: {backup_filename}\n")
    
    # Ask for confirmation
    print("="*80)
    print("READY TO UPDATE PRODUCTION")
    print("="*80 + "\n")
    
    if auto_confirm:
        print(f"Auto-confirming update of {len(differences)} logo_filename values (--yes flag provided)\n")
    else:
        response = input(f"Update {len(differences)} logo_filename values in PRODUCTION? (yes/no): ")
        
        if response.lower() != 'yes':
            print("\n❌ Update cancelled by user.\n")
            local_conn.close()
            prod_conn.close()
            return
    
    print("\nUpdating PRODUCTION database...\n")
    
    # Execute updates
    prod_cursor = prod_conn.cursor()
    update_count = 0
    
    for diff in differences:
        try:
            prod_cursor.execute("""
                UPDATE clubs 
                SET logo_filename = %s 
                WHERE id = %s
            """, (diff['local_logo'], diff['id']))
            update_count += 1
            print(f"✓ Updated club ID {diff['id']}: {diff['name']}")
        except Exception as e:
            print(f"❌ ERROR updating club ID {diff['id']}: {e}")
    
    # Commit changes
    prod_conn.commit()
    prod_cursor.close()
    
    print(f"\n{'='*80}")
    print("UPDATE COMPLETE")
    print("="*80 + "\n")
    
    print(f"✓ Successfully updated {update_count}/{len(differences)} clubs")
    print(f"✓ Backup saved to: {backup_filename}")
    print()
    
    # Verify updates
    print("Verifying updates...")
    updated_prod_clubs = get_club_logos(prod_conn)
    
    verification_errors = []
    for diff in differences:
        club_id = diff['id']
        expected_logo = diff['local_logo']
        actual_logo = updated_prod_clubs[club_id]['logo_filename']
        
        if expected_logo != actual_logo:
            verification_errors.append(f"Club ID {club_id}: Expected '{expected_logo}', got '{actual_logo}'")
    
    if verification_errors:
        print(f"\n⚠️  WARNING: {len(verification_errors)} verification errors:")
        for error in verification_errors:
            print(f"  - {error}")
    else:
        print("✓ All updates verified successfully!\n")
    
    # Close connections
    local_conn.close()
    prod_conn.close()
    
    print("="*80)
    print("DONE")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()

