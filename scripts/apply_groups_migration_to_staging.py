#!/usr/bin/env python3
"""
Apply Groups Migration to Staging
================================

This script applies the groups tables SQL migration to the staging environment.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_staging_database_url():
    """Get the staging database URL from environment variables"""
    # Check for Railway staging environment variables
    staging_db_url = os.getenv("DATABASE_PUBLIC_URL") or os.getenv("DATABASE_URL")
    
    if not staging_db_url:
        logger.error("No staging database URL found. Please set DATABASE_PUBLIC_URL or DATABASE_URL")
        return None
    
    # Handle Railway's postgres:// URLs
    if staging_db_url.startswith("postgres://"):
        staging_db_url = staging_db_url.replace("postgres://", "postgresql://", 1)
    
    return staging_db_url

def execute_sql_file(sql_file_path):
    """Execute SQL file against staging database"""
    print(f"📁 Reading SQL file: {sql_file_path}")
    
    try:
        with open(sql_file_path, 'r') as f:
            sql_content = f.read()
        
        print("📄 SQL content loaded successfully")
        
        # Import database utilities
        from database_utils import execute_query_one, execute_query
        
        # Set environment for staging database
        original_db_url = os.environ.get('DATABASE_URL')
        staging_url = get_staging_database_url()
        
        if staging_url:
            os.environ['DATABASE_URL'] = staging_url
            print(f"🔗 Connected to staging database")
        
        # Clean up SQL content - remove \d commands and comments that aren't SQL
        lines = sql_content.split('\n')
        sql_statements = []
        current_statement = []
        
        for line in lines:
            stripped = line.strip()
            # Skip empty lines and comments
            if not stripped or stripped.startswith('--'):
                continue
            # Skip psql meta-commands
            if stripped.startswith('\\'):
                continue
            # Skip the success message SELECT
            if 'Groups tables created successfully' in stripped:
                continue
                
            current_statement.append(line)
            
            # Check if this line ends a complete statement
            if stripped.endswith(';'):
                stmt = '\n'.join(current_statement).strip()
                if stmt:
                    sql_statements.append(stmt)
                current_statement = []
        
        # Add any remaining statement
        if current_statement:
            stmt = '\n'.join(current_statement).strip()
            if stmt:
                sql_statements.append(stmt)
        
        print(f"🔄 Executing {len(sql_statements)} SQL statements...")
        
        for i, statement in enumerate(sql_statements, 1):
            if statement:
                print(f"   Executing statement {i}/{len(sql_statements)}...")
                try:
                    execute_query(statement)
                    print(f"   ✅ Statement {i} completed")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        print(f"   ⚠️  Statement {i} - Object already exists (skipping)")
                    else:
                        print(f"   ❌ Statement {i} failed: {e}")
                        # For debugging, show the problematic statement
                        print(f"      Statement was: {statement[:100]}...")
                        raise
        
        print("✅ All SQL statements executed successfully!")
        
        # Restore original database URL
        if original_db_url:
            os.environ['DATABASE_URL'] = original_db_url
        
        return True
        
    except Exception as e:
        print(f"❌ Error executing SQL file: {e}")
        return False

def verify_tables_created():
    """Verify the groups tables were created"""
    print("🔍 Verifying tables were created...")
    
    try:
        from database_utils import execute_query_one
        
        # Set environment for staging database
        staging_url = get_staging_database_url()
        if staging_url:
            os.environ['DATABASE_URL'] = staging_url
        
        # Check if groups table exists
        result = execute_query_one("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'groups'
        """)
        
        if result:
            print("✅ 'groups' table exists")
        else:
            print("❌ 'groups' table not found")
            return False
        
        # Check if group_members table exists
        result = execute_query_one("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'group_members'
        """)
        
        if result:
            print("✅ 'group_members' table exists")
        else:
            print("❌ 'group_members' table not found")
            return False
        
        print("✅ All tables verified successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying tables: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Applying Groups Migration to Staging")
    print("=" * 50)
    
    # Check if we have the necessary environment variables
    if not get_staging_database_url():
        print("❌ Cannot proceed without staging database URL")
        return 1
    
    # Execute the SQL file
    sql_file_path = os.path.join(os.path.dirname(__file__), "create_groups_tables_dbschema.sql")
    
    if not os.path.exists(sql_file_path):
        print(f"❌ SQL file not found: {sql_file_path}")
        return 1
    
    if not execute_sql_file(sql_file_path):
        print("❌ Failed to execute SQL migration")
        return 1
    
    # Verify tables were created
    if not verify_tables_created():
        print("⚠️  Migration completed but table verification failed")
        return 1
    
    print("\n🎉 Groups migration successfully applied to staging!")
    print("=" * 50)
    print("✅ Groups tables created")
    print("✅ Foreign key constraints applied")
    print("✅ Indexes created for performance")
    print()
    print("📝 Next steps:")
    print("   1. Test Group Chats functionality on staging")
    print("   2. Verify all CRUD operations work")
    print("   3. Deploy to production when ready")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 