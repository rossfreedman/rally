#!/usr/bin/env python3
"""
Club Logo Fixer Script
======================

This script sets the correct logo_filename values for clubs that have logos.
It should be run after ETL imports to restore logo filenames that get lost 
when the clubs table is recreated.

Usage:
    python scripts/fix_club_logos.py
"""

import sys
import os

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from database_utils import execute_update, execute_query_one


def fix_club_logos():
    """Set correct logo filenames for clubs that have logos"""
    
    # Define clubs that should have logos and their corresponding logo files
    club_logos = {
        'Glenbrook RC': 'static/images/clubs/glenbrook_rc_logo.png',
        'Tennaqua': 'static/images/clubs/tennaqua_logo.jpeg'
    }
    
    print("🎨 Fixing club logos...")
    
    for club_name, logo_filename in club_logos.items():
        try:
            # Check if club exists
            club_check = execute_query_one("SELECT id FROM clubs WHERE name = %s", [club_name])
            
            if club_check:
                # Update the logo filename
                result = execute_update(
                    "UPDATE clubs SET logo_filename = %s WHERE name = %s",
                    [logo_filename, club_name]
                )
                
                if result:
                    print(f"✅ Updated {club_name} logo: {logo_filename}")
                else:
                    print(f"⚠️  Failed to update {club_name} logo")
            else:
                print(f"❌ Club not found: {club_name}")
                
        except Exception as e:
            print(f"❌ Error updating {club_name}: {e}")
    
    print("🎨 Club logo fixing complete!")


def main():
    """Main entry point"""
    try:
        fix_club_logos()
        print("\n✅ Club logo fix completed successfully!")
        return 0
    except Exception as e:
        print(f"\n❌ Club logo fix failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 