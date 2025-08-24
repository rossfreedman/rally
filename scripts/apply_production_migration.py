#!/usr/bin/env python3
"""
Script to apply the lineup escrow database migration to production
Adds initiator_team_id and recipient_team_id columns to lineup_escrow table
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def get_production_db_connection():
    """Get connection to production database using Railway environment variables"""
    try:
        # Use the public URL from Railway
        database_url = os.getenv('DATABASE_PUBLIC_URL')
        if not database_url:
            print("❌ DATABASE_PUBLIC_URL environment variable not found")
            print("Please ensure you're running this from Railway production environment")
            return None
        
        print(f"🔗 Connecting to production database...")
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to production database: {e}")
        return None

def check_table_structure(conn):
    """Check current structure of lineup_escrow table"""
    try:
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'lineup_escrow' 
            AND column_name IN ('initiator_team_id', 'recipient_team_id')
        """)
        
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        if existing_columns:
            print(f"✅ Columns already exist: {existing_columns}")
            return True
        else:
            print("❌ Required columns not found, need to add them")
            return False
            
    except Exception as e:
        print(f"❌ Error checking table structure: {e}")
        return False

def apply_migration(conn):
    """Apply the database migration"""
    try:
        cursor = conn.cursor()
        
        print("🔧 Applying migration: Adding team ID columns...")
        
        # Add team ID columns
        cursor.execute("""
            ALTER TABLE lineup_escrow 
            ADD COLUMN initiator_team_id INTEGER REFERENCES teams(id),
            ADD COLUMN recipient_team_id INTEGER REFERENCES teams(id)
        """)
        
        print("✅ Added team ID columns")
        
        # Add indexes for better performance
        print("🔧 Creating indexes...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_lineup_escrow_initiator_team 
            ON lineup_escrow(initiator_team_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_lineup_escrow_recipient_team 
            ON lineup_escrow(recipient_team_id)
        """)
        
        print("✅ Created indexes")
        
        # Add comments for documentation
        print("🔧 Adding column comments...")
        cursor.execute("""
            COMMENT ON COLUMN lineup_escrow.initiator_team_id IS 
            'Team ID of the initiator (sender) of the lineup escrow'
        """)
        
        cursor.execute("""
            COMMENT ON COLUMN lineup_escrow.recipient_team_id IS 
            'Team ID of the recipient (receiver) of the lineup escrow'
        """)
        
        print("✅ Added column comments")
        
        return True
        
    except Exception as e:
        print(f"❌ Error applying migration: {e}")
        return False

def verify_migration(conn):
    """Verify the migration was applied successfully"""
    try:
        cursor = conn.cursor()
        
        # Check if columns exist
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'lineup_escrow' 
            AND column_name IN ('initiator_team_id', 'recipient_team_id')
            ORDER BY column_name
        """)
        
        columns = cursor.fetchall()
        
        if len(columns) == 2:
            print("✅ Migration verification successful:")
            for col_name, data_type, is_nullable in columns:
                print(f"   - {col_name}: {data_type} (nullable: {is_nullable})")
            return True
        else:
            print(f"❌ Migration verification failed: found {len(columns)} columns")
            return False
            
    except Exception as e:
        print(f"❌ Error verifying migration: {e}")
        return False

def main():
    """Main function to apply production migration"""
    print("🚀 Lineup Escrow Production Database Migration")
    print("=" * 50)
    
    # Check if we're in production environment
    if os.getenv('RAILWAY_ENVIRONMENT') != 'production':
        print("⚠️  Warning: Not in production environment")
        print("Current environment:", os.getenv('RAILWAY_ENVIRONMENT', 'unknown'))
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("❌ Migration cancelled")
            return
    
    # Connect to production database
    conn = get_production_db_connection()
    if not conn:
        print("❌ Cannot proceed without database connection")
        return
    
    try:
        # Check current table structure
        if check_table_structure(conn):
            print("✅ Migration already applied, no action needed")
            return
        
        # Apply migration
        if apply_migration(conn):
            print("✅ Migration applied successfully")
            
            # Verify migration
            if verify_migration(conn):
                print("🎉 Production migration completed successfully!")
            else:
                print("⚠️  Migration applied but verification failed")
        else:
            print("❌ Migration failed")
            
    finally:
        if conn:
            conn.close()
            print("🔌 Database connection closed")

if __name__ == "__main__":
    main()
