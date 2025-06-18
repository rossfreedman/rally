#!/usr/bin/env python3
"""
Fix Remaining References to Old user_player_associations Schema
==============================================================

This script identifies and fixes remaining references to player_id in 
user_player_associations after migrating to tenniscores_player_id schema.
"""

import os
import re
from pathlib import Path

def find_problematic_files():
    """Find files that still reference user_player_associations with player_id"""
    problematic_files = []
    
    # Files to check (excluding migration history)
    check_patterns = [
        "data/etl/*.py",
        "data/etl/*.sql", 
        "scripts/*.py",
        "app/services/*.py",
        "app/routes/*.py",
        "app/utils/*.py"
    ]
    
    for pattern in check_patterns:
        for file_path in Path(".").glob(pattern):
            if file_path.is_file():
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                    
                    # Look for problematic patterns
                    patterns_to_check = [
                        r"user_player_associations.*\.player_id",
                        r"upa\.player_id",
                        r"JOIN.*user_player_associations.*ON.*player_id.*=",
                        r"UserPlayerAssociation\.player_id",
                        r"SELECT.*upa\.player_id"
                    ]
                    
                    found_issues = []
                    for i, line in enumerate(content.split('\n'), 1):
                        for pattern in patterns_to_check:
                            if re.search(pattern, line, re.IGNORECASE):
                                found_issues.append((i, line.strip(), pattern))
                    
                    if found_issues:
                        problematic_files.append((str(file_path), found_issues))
                        
                except Exception as e:
                    print(f"⚠️  Error reading {file_path}: {e}")
    
    return problematic_files

def fix_etl_cleanup_script():
    """Fix data/etl/cleanup_orphaned_associations.sql"""
    file_path = "data/etl/cleanup_orphaned_associations.sql"
    
    if not os.path.exists(file_path):
        print(f"⚠️  {file_path} not found")
        return
    
    print(f"🔧 Updating {file_path}...")
    
    old_content = """-- 1. Show current orphaned associations
SELECT 
    upa.user_id, 
    upa.player_id, 
    upa.is_primary,
    u.email as user_email,
    'ORPHANED - Player ID does not exist' as status
FROM user_player_associations upa
LEFT JOIN users u ON upa.user_id = u.id
LEFT JOIN players p ON upa.player_id = p.id
WHERE p.id IS NULL;"""

    new_content = """-- 1. Show current orphaned associations
SELECT 
    upa.user_id, 
    upa.tenniscores_player_id, 
    upa.league_id,
    upa.is_primary,
    u.email as user_email,
    'ORPHANED - Player does not exist' as status
FROM user_player_associations upa
LEFT JOIN users u ON upa.user_id = u.id
LEFT JOIN players p ON p.tenniscores_player_id = upa.tenniscores_player_id 
                   AND p.league_id = upa.league_id
WHERE p.id IS NULL;"""

    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        if old_content in content:
            content = content.replace(old_content, new_content)
            
            with open(file_path, 'w') as f:
                f.write(content)
            
            print(f"   ✅ Updated orphaned associations query")
        else:
            print(f"   ℹ️  Content already updated or not found")
            
    except Exception as e:
        print(f"   ❌ Error updating {file_path}: {e}")

def fix_backup_restore_script():
    """Fix data/etl/backup_restore_users.py"""
    file_path = "data/etl/backup_restore_users.py"
    
    if not os.path.exists(file_path):
        print(f"⚠️  {file_path} not found")
        return
    
    print(f"🔧 Updating {file_path}...")
    
    # This file has complex logic, just notify user to check it manually
    print(f"   ⚠️  MANUAL UPDATE REQUIRED: This file needs complex changes")
    print(f"   📝 Action: Review all SQL queries in this file")
    print(f"   📝 Update: Change upa.player_id references to use new schema")

def create_validation_script():
    """Create a script to validate the migration worked"""
    script_content = '''#!/usr/bin/env python3
"""
Validate user_player_associations Migration
==========================================
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db

def validate_migration():
    """Check that migration completed successfully"""
    print("🔍 Validating user_player_associations migration...")
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Check new schema exists
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'user_player_associations'
                ORDER BY ordinal_position
            """)
            
            columns = cursor.fetchall()
            expected_columns = {
                'user_id': 'integer',
                'tenniscores_player_id': 'character varying', 
                'league_id': 'integer',
                'is_primary': 'boolean',
                'created_at': 'timestamp with time zone'
            }
            
            actual_columns = {col[0]: col[1] for col in columns}
            
            print("📊 Current table schema:")
            for col_name, col_type in actual_columns.items():
                status = "✅" if col_name in expected_columns else "❌"
                print(f"   {status} {col_name}: {col_type}")
            
            # Check for old column
            if 'player_id' in actual_columns:
                print("   ❌ OLD COLUMN STILL EXISTS: player_id")
                return False
            
            # Check data
            cursor.execute("SELECT COUNT(*) FROM user_player_associations")
            total_associations = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM user_player_associations upa
                LEFT JOIN players p ON p.tenniscores_player_id = upa.tenniscores_player_id 
                                   AND p.league_id = upa.league_id
                WHERE p.id IS NULL
            """)
            orphaned_associations = cursor.fetchone()[0]
            
            print(f"📈 Association Data:")
            print(f"   Total associations: {total_associations:,}")
            print(f"   Orphaned associations: {orphaned_associations:,}")
            
            if orphaned_associations > 0:
                print("   ❌ Found orphaned associations!")
                return False
            
            print("✅ Migration validation PASSED!")
            return True
            
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False

if __name__ == "__main__":
    success = validate_migration()
    sys.exit(0 if success else 1)
'''
    
    with open("scripts/validate_migration.py", "w") as f:
        f.write(script_content)
    
    print("✅ Created scripts/validate_migration.py")

def main():
    """Main function to identify and fix issues"""
    print("🔍 SCANNING FOR REMAINING user_player_associations REFERENCES")
    print("=" * 70)
    
    # Find problematic files
    problematic_files = find_problematic_files()
    
    if not problematic_files:
        print("✅ No problematic references found!")
        return
    
    print(f"⚠️  Found {len(problematic_files)} files with issues:")
    print()
    
    for file_path, issues in problematic_files:
        print(f"📁 {file_path}:")
        for line_num, line_content, pattern in issues:
            print(f"   Line {line_num}: {line_content}")
        print()
    
    # Fix specific files
    print("🔧 FIXING KNOWN ISSUES:")
    print("-" * 30)
    
    fix_etl_cleanup_script()
    fix_backup_restore_script()
    create_validation_script()
    
    print("\n📝 MANUAL ACTIONS REQUIRED:")
    print("1. Review all files listed above")
    print("2. Update any remaining SQL queries to use:")
    print("   - upa.tenniscores_player_id instead of upa.player_id")
    print("   - JOIN ON tenniscores_player_id + league_id")
    print("3. Run: python scripts/validate_migration.py")
    print("4. Test all affected functionality")

if __name__ == "__main__":
    main() 