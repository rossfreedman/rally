#!/usr/bin/env python3
"""
Rally Multi-League Migration Runner

This script runs all necessary migrations and ETL processes to transition
Rally from single-league to multi-league support.

Usage:
    python run_multi_league_migration.py [--dry-run]
"""
import sys
import os
import argparse
import psycopg2
from psycopg2.extras import RealDictCursor
from database_config import get_db

def run_sql_migration(migration_file, description):
    """Run a SQL migration file"""
    print(f"\n🔄 Running migration: {description}")
    print(f"   File: {migration_file}")
    
    if not os.path.exists(migration_file):
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    try:
        with get_db() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Read and execute the SQL file
            with open(migration_file, 'r') as f:
                sql_content = f.read()
            
            cursor.execute(sql_content)
            conn.commit()
            
        print(f"✅ Migration completed: {description}")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {description}")
        print(f"   Error: {str(e)}")
        return False

def run_etl_script(script_path, description):
    """Run an ETL Python script"""
    print(f"\n🔄 Running ETL: {description}")
    print(f"   Script: {script_path}")
    
    if not os.path.exists(script_path):
        print(f"❌ ETL script not found: {script_path}")
        return False
    
    try:
        # Import and run the ETL script
        sys.path.insert(0, os.path.dirname(script_path))
        import importlib.util
        
        spec = importlib.util.spec_from_file_location("etl_module", script_path)
        etl_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(etl_module)
        
        # Run the main function if it exists
        if hasattr(etl_module, 'main'):
            result = etl_module.main()
            if result is False:
                print(f"❌ ETL failed: {description}")
                return False
        
        print(f"✅ ETL completed: {description}")
        return True
        
    except Exception as e:
        print(f"❌ ETL failed: {description}")
        print(f"   Error: {str(e)}")
        return False

def main():
    """Run the complete multi-league migration"""
    parser = argparse.ArgumentParser(description="Run Rally multi-league migration")
    parser.add_argument('--dry-run', action='store_true', 
                       help='Run in dry-run mode (no actual changes)')
    args = parser.parse_args()
    
    print("🏓 Rally Multi-League Migration")
    print("=" * 50)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No actual changes will be made")
    
    # Define migration steps in order
    migration_steps = [
        # Step 1: Fix players table structure
        {
            'type': 'sql',
            'file': 'migrations/fix_players_table_structure.sql',
            'description': 'Fix players table structure (nullable email/password)'
        },
        
        # Step 2: Remove unique constraint on player_leagues
        {
            'type': 'sql', 
            'file': 'migrations/remove_player_leagues_unique_constraint.sql',
            'description': 'Remove unique constraint for multi-league support'
        },
        
        # Step 3: Normalize multi-league schema
        {
            'type': 'sql',
            'file': 'migrations/normalize_multi_league_schema.sql',
            'description': 'Normalize schema for multi-league relationships'
        },
        
        # Step 4: Import player data
        {
            'type': 'etl',
            'file': 'data/etl/import_players.py',
            'description': 'Import player data with multi-league support'
        },
        
        # Step 5: Restore foreign key constraints
        {
            'type': 'sql',
            'file': 'migrations/restore_foreign_keys.sql', 
            'description': 'Restore foreign key constraints'
        }
    ]
    
    # Track success/failure
    successful_steps = 0
    total_steps = len(migration_steps)
    
    for i, step in enumerate(migration_steps, 1):
        print(f"\n{'='*20} Step {i}/{total_steps} {'='*20}")
        
        if args.dry_run and step['type'] == 'etl':
            print(f"🔍 DRY RUN: Would run ETL - {step['description']}")
            successful_steps += 1
            continue
        elif args.dry_run:
            print(f"🔍 DRY RUN: Would run SQL migration - {step['description']}")
            successful_steps += 1
            continue
        
        # Run the actual migration step
        if step['type'] == 'sql':
            success = run_sql_migration(step['file'], step['description'])
        elif step['type'] == 'etl':
            success = run_etl_script(step['file'], step['description'])
        else:
            print(f"❌ Unknown step type: {step['type']}")
            success = False
        
        if success:
            successful_steps += 1
        else:
            print(f"\n❌ Migration failed at step {i}/{total_steps}")
            print("   Please fix the error and re-run the migration")
            sys.exit(1)
    
    # Final status
    print(f"\n{'='*50}")
    if successful_steps == total_steps:
        print("🎉 Multi-league migration completed successfully!")
        print(f"   {successful_steps}/{total_steps} steps completed")
        
        if not args.dry_run:
            print("\n📋 Next steps:")
            print("   1. Test player API endpoints")
            print("   2. Test registration with player matching")
            print("   3. Verify multi-league player data")
            print("   4. Update any remaining JSON-dependent code")
    else:
        print(f"⚠️  Migration incomplete: {successful_steps}/{total_steps} steps completed")
        
    return successful_steps == total_steps

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1) 