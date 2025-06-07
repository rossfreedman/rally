#!/usr/bin/env python3
"""
Database migration runner for Railway deployment.

This script ensures all necessary database schema updates are applied
before the application starts, including:
- Creating leagues table and relationships
- Adding missing columns to users table
- Creating proper indexes
"""

import os
import sys
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
        # Run leagues tables migration
        print("📋 Running leagues tables migration...")
        run_leagues_migration()
        print("✅ Leagues tables migration completed")
        
        # Run missing columns migration  
        print("📋 Running missing user columns migration...")
        run_columns_migration()
        print("✅ User columns migration completed")
        
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