#!/usr/bin/env python3
"""
Migration script to add missing columns to users table for Railway deployment.

This adds:
1. is_admin BOOLEAN column with default FALSE
2. tenniscores_player_id VARCHAR column for player ID mapping
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

def run_migration():
    """Run the missing columns migration"""
    # Load environment variables
    load_dotenv()
    
    # Get database URL from environment variable
    DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('DATABASE_PUBLIC_URL')
    if not DATABASE_URL:
        raise Exception("DATABASE_URL environment variable is not set")
    
    print("Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    print("Adding missing columns to users table...")
    
    # Add is_admin column if it doesn't exist
    try:
        cursor.execute('''
        ALTER TABLE users 
        ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE NOT NULL
        ''')
        print("✓ Added is_admin column")
    except Exception as e:
        print(f"Note: is_admin column may already exist: {e}")
    
    # Add tenniscores_player_id column if it doesn't exist
    try:
        cursor.execute('''
        ALTER TABLE users 
        ADD COLUMN IF NOT EXISTS tenniscores_player_id VARCHAR(255)
        ''')
        print("✓ Added tenniscores_player_id column")
    except Exception as e:
        print(f"Note: tenniscores_player_id column may already exist: {e}")
    
    print("Creating index for tenniscores_player_id...")
    try:
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_tenniscores_player_id ON users(tenniscores_player_id)')
        print("✓ Created tenniscores_player_id index")
    except Exception as e:
        print(f"Note: Index may already exist: {e}")
    
    conn.close()
    print("Missing columns migration completed successfully!")

if __name__ == '__main__':
    try:
        run_migration()
    except Exception as e:
        print(f"Migration failed: {str(e)}")
        sys.exit(1) 