#!/usr/bin/env python3
"""
Manual Staging Upgrade Helper
============================

Helper script to guide you through manual staging upgrade.
"""

import os
import sys

def print_manual_instructions():
    """Print step-by-step manual instructions"""
    print("🏓 MANUAL STAGING UPGRADE GUIDE")
    print("=" * 50)
    print()
    print("📋 STAGING DATABASE INFO:")
    print("   Host: switchback.proxy.rlwy.net:28473")
    print("   Database: railway")
    print("   User: postgres")
    print("   Password: SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY")
    print()
    print("🔧 MANUAL STEPS:")
    print()
    print("1️⃣  Connect to staging database using your preferred tool:")
    print("   - psql: psql postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway")
    print("   - pgAdmin: Use the connection details above")
    print("   - DBeaver: Use the connection details above")
    print()
    print("2️⃣  Run the SQL script: scripts/manual_staging_upgrade.sql")
    print("   - Copy and paste the contents of the file")
    print("   - Or execute it directly if your tool supports file execution")
    print()
    print("3️⃣  Verify the upgrade by checking:")
    print("   - SELECT version_num FROM alembic_version; (should show 'sync_all_env_001')")
    print("   - Check that new columns exist in the tables")
    print()
    print("4️⃣  Test the upgrade by running:")
    print("   python3 scripts/test_staging_connection.py")
    print()
    print("📄 SQL SCRIPT LOCATION:")
    print("   File: scripts/manual_staging_upgrade.sql")
    print("   This contains all the necessary ALTER TABLE and CREATE INDEX commands")
    print()
    print("⚠️  IMPORTANT NOTES:")
    print("   - The script uses 'IF NOT EXISTS' so it's safe to run multiple times")
    print("   - All changes are backward compatible")
    print("   - No data will be lost")
    print()
    print("✅ After running the SQL script, staging should be fully synced with production!")

def show_sql_script():
    """Show the SQL script contents"""
    print("\n📄 SQL SCRIPT CONTENTS:")
    print("=" * 50)
    try:
        with open('scripts/manual_staging_upgrade.sql', 'r') as f:
            print(f.read())
    except FileNotFoundError:
        print("❌ SQL script file not found")
        return False
    return True

def main():
    """Main function"""
    print_manual_instructions()
    
    print("\n" + "=" * 50)
    response = input("Would you like to see the SQL script contents? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y']:
        show_sql_script()
    
    print("\n🎯 READY TO PROCEED!")
    print("Follow the manual steps above to upgrade staging.")
    print("The SQL script is safe to run and will sync staging with production.")

if __name__ == "__main__":
    main()
