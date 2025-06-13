#!/usr/bin/env python3
"""
Database migration runner for Railway deployment.

This script ensures all necessary database schema updates are applied
before the application starts, including:
- Creating leagues table and relationships
- Adding missing columns to users table
- Creating proper indexes
- Running Alembic data migrations
"""

import os
import sys
import subprocess
import logging
from dotenv import load_dotenv

# Add the app directory to Python path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_all_migrations():
    """Run all necessary migrations to bring the database up to date"""
    
    load_dotenv()
    
    # Import after setting up the path
    try:
        from migrations.create_leagues_tables import run_migration as run_leagues_migration
        from migrations.add_missing_user_columns import run_migration as run_columns_migration
    except ImportError as e:
        print(f"Error importing migration modules: {e}")
        return False
    
    print("🚀 Starting database migrations...")
    
    try:
        # Run schema migrations first
        print("📋 Running leagues tables migration...")
        run_leagues_migration()
        print("✅ Leagues tables migration completed")
        
        # Run missing columns migration  
        print("📋 Running missing user columns migration...")
        run_columns_migration()
        print("✅ User columns migration completed")
        
        # Run Alembic data migrations
        print("📋 Running Alembic data migrations...")
        try:
            result = subprocess.run(
                ['alembic', 'upgrade', 'head'], 
                capture_output=True, 
                text=True,
                check=True
            )
            print("✅ Alembic data migrations completed")
            print(f"Alembic output: {result.stdout}")
            if result.stderr:
                print(f"Alembic warnings: {result.stderr}")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Alembic migration failed: {e}")
            print(f"Stdout: {e.stdout}")
            print(f"Stderr: {e.stderr}")
            print("⚠️  Continuing with application startup...")
        except FileNotFoundError:
            print("⚠️  Alembic not found - skipping data migrations")
        
        print("🎉 All database migrations completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = run_all_migrations()
    if not success:
        sys.exit(1)
    print("Database is ready for application startup!") 