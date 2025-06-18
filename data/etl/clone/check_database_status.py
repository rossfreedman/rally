#!/usr/bin/env python3
"""
Check Database Status - Compare Local vs Railway

Quick utility to check migration status and basic table counts
for both local and Railway databases.
"""

import os
import sys
import subprocess
import psycopg2

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from database_config import parse_db_url

# Database URLs
LOCAL_DB_URL = "postgresql://postgres:postgres@localhost:5432/rally"
RAILWAY_DB_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

def get_migration_version(db_url, db_name):
    """Get Alembic migration version from database"""
    try:
        params = parse_db_url(db_url)
        if 'railway' in db_url:
            params['connect_timeout'] = 30
            
        conn = psycopg2.connect(**params)
        
        with conn.cursor() as cursor:
            # Check if alembic_version table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'alembic_version'
                )
            """)
            
            if cursor.fetchone()[0]:
                cursor.execute("SELECT version_num FROM alembic_version")
                version = cursor.fetchone()
                if version:
                    return version[0]
                else:
                    return "No version set"
            else:
                return "No alembic_version table"
                
        conn.close()
        
    except Exception as e:
        return f"Error: {e}"

def get_table_count(db_url, db_name):
    """Get total number of tables in database"""
    try:
        params = parse_db_url(db_url)
        if 'railway' in db_url:
            params['connect_timeout'] = 30
            
        conn = psycopg2.connect(**params)
        
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
            """)
            
            count = cursor.fetchone()[0]
            return count
                
        conn.close()
        
    except Exception as e:
        return f"Error: {e}"

def get_local_alembic_status():
    """Get local Alembic status via command line"""
    try:
        result = subprocess.run(["alembic", "current"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"Error: {result.stderr}"
    except Exception as e:
        return f"Error: {e}"

def main():
    print("Database Status Checker")
    print("=" * 50)
    
    # Local database status
    print("\n🏠 LOCAL DATABASE")
    print("-" * 20)
    local_migration = get_migration_version(LOCAL_DB_URL, "Local")
    local_tables = get_table_count(LOCAL_DB_URL, "Local")
    local_alembic = get_local_alembic_status()
    
    print(f"Migration Version (DB): {local_migration}")
    print(f"Migration Version (Alembic): {local_alembic}")
    print(f"Table Count: {local_tables}")
    
    # Railway database status
    print("\n🚂 RAILWAY DATABASE")
    print("-" * 20)
    railway_migration = get_migration_version(RAILWAY_DB_URL, "Railway")
    railway_tables = get_table_count(RAILWAY_DB_URL, "Railway")
    
    print(f"Migration Version: {railway_migration}")
    print(f"Table Count: {railway_tables}")
    
    # Summary
    print("\n📊 COMPARISON")
    print("-" * 20)
    
    # Migration comparison
    if local_migration == railway_migration:
        print("✅ Migration versions match")
    else:
        print(f"❌ Migration versions differ: Local='{local_migration}', Railway='{railway_migration}'")
    
    # Table count comparison
    if isinstance(local_tables, int) and isinstance(railway_tables, int):
        if local_tables == railway_tables:
            print("✅ Table counts match")
        else:
            print(f"❌ Table counts differ: Local={local_tables}, Railway={railway_tables}")
    else:
        print("⚠️  Unable to compare table counts due to connection errors")

if __name__ == "__main__":
    main() 