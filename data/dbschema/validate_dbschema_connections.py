#!/usr/bin/env python3
"""
Database Connection Validator for DbSchema Setup
Validates all database connections that will be used in DbSchema for schema management and syncing.
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

# Add root directory to path for imports (go up two levels from data/dbschema)
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from database_config import get_db_url, parse_db_url

load_dotenv()

def test_connection(name, url, description=""):
    """Test database connection for DbSchema setup"""
    print(f"🔍 Testing {name}...")
    if description:
        print(f"   Purpose: {description}")
    
    try:
        db_params = parse_db_url(url)
        print(f"   Connecting to: {db_params['host']}:{db_params['port']}/{db_params['dbname']}")
        
        conn = psycopg2.connect(**db_params)
        
        with conn.cursor() as cursor:
            # Test basic connection
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            print(f"   ✅ Connected successfully")
            print(f"   PostgreSQL: {version[:50]}...")
            
            # Test schema access
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
            tables = [row[0] for row in cursor.fetchall()]
            print(f"   Tables found: {len(tables)}")
            
            # Test key Rally tables
            key_tables = [
                'users', 'leagues', 'clubs', 'series', 'teams', 'players',
                'user_player_associations', 'match_scores', 'schedule', 'series_stats'
            ]
            
            existing_key_tables = [table for table in key_tables if table in tables]
            missing_key_tables = [table for table in key_tables if table not in tables]
            
            print(f"   Key Rally tables: {len(existing_key_tables)}/{len(key_tables)}")
            if missing_key_tables:
                print(f"   ⚠️  Missing tables: {missing_key_tables}")
            
            # Test foreign key constraints
            cursor.execute("""
                SELECT COUNT(*) as constraint_count
                FROM information_schema.table_constraints 
                WHERE constraint_type = 'FOREIGN KEY' 
                AND table_schema = 'public'
            """)
            fk_count = cursor.fetchone()[0]
            print(f"   Foreign key constraints: {fk_count}")
            
            # Test user permissions
            cursor.execute("SELECT current_user")
            current_user = cursor.fetchone()[0]
            print(f"   Connected as: {current_user}")
            
        conn.close()
        print(f"   ✅ {name} validation complete\n")
        return True
        
    except psycopg2.OperationalError as e:
        error_msg = str(e)
        print(f"   ❌ Connection failed: {error_msg}")
        
        # Provide specific troubleshooting for common issues
        if "connection refused" in error_msg.lower():
            print(f"   💡 Troubleshooting:")
            print(f"      - Check if PostgreSQL is running")
            print(f"      - Verify host and port are correct")
            print(f"      - Check firewall settings")
        elif "authentication failed" in error_msg.lower():
            print(f"   💡 Troubleshooting:")
            print(f"      - Verify username and password")
            print(f"      - Check pg_hba.conf settings")
        elif "database" in error_msg.lower() and "does not exist" in error_msg.lower():
            print(f"   💡 Troubleshooting:")
            print(f"      - Create the database first")
            print(f"      - Check database name spelling")
        elif "timeout" in error_msg.lower():
            print(f"   💡 Troubleshooting:")
            print(f"      - Check network connectivity")
            print(f"      - Verify Railway database URL")
            print(f"      - Try DATABASE_PUBLIC_URL instead")
        
        print()
        return False
        
    except Exception as e:
        print(f"   ❌ Unexpected error: {str(e)}")
        print()
        return False

def get_railway_connection_info():
    """Extract Railway connection details for DbSchema setup"""
    railway_url = os.getenv("DATABASE_PUBLIC_URL")
    if not railway_url:
        return None
    
    try:
        db_params = parse_db_url(railway_url)
        return {
            "host": db_params['host'],
            "port": db_params['port'],
            "database": db_params['dbname'],
            "username": db_params['user'],
            "ssl_mode": db_params.get('sslmode', 'require')
        }
    except Exception as e:
        print(f"❌ Error parsing Railway URL: {e}")
        return None

def print_dbschema_connection_guide():
    """Print DbSchema connection configuration guide"""
    print("📋 DbSchema Connection Configuration Guide")
    print("=" * 50)
    
    print("\n🏠 LOCAL DATABASE CONNECTION:")
    print("   Connection Name: Rally Local")
    print("   Database Type: PostgreSQL")
    print("   Host: localhost")
    print("   Port: 5432")
    print("   Database: rally")
    print("   Username: rossfreedman")
    print("   SSL Mode: prefer")
    
    railway_info = get_railway_connection_info()
    if railway_info:
        print("\n🚂 RAILWAY PRODUCTION CONNECTION:")
        print("   Connection Name: Rally Production (Railway)")
        print("   Database Type: PostgreSQL")
        print(f"   Host: {railway_info['host']}")
        print(f"   Port: {railway_info['port']}")
        print(f"   Database: {railway_info['database']}")
        print(f"   Username: {railway_info['username']}")
        print(f"   SSL Mode: {railway_info['ssl_mode']}")
        print("   ⚠️  Password: (from your Railway dashboard)")
    else:
        print("\n🚂 RAILWAY PRODUCTION CONNECTION:")
        print("   ❌ DATABASE_PUBLIC_URL not configured")
        print("   💡 Set up Railway environment variables first")
    
    print("\n📖 JDBC URL Examples:")
    print("   Local: jdbc:postgresql://localhost:5432/rally")
    if railway_info:
        print(f"   Railway: jdbc:postgresql://{railway_info['host']}:{railway_info['port']}/{railway_info['database']}?sslmode={railway_info['ssl_mode']}")

def main():
    """Main validation function"""
    print("🔍 DbSchema Database Connection Validator")
    print("=" * 50)
    print("Validating database connections for DbSchema setup...\n")
    
    connections_tested = 0
    connections_successful = 0
    
    # Test local connection
    print("1️⃣ LOCAL DATABASE")
    local_url = "postgresql://rossfreedman@localhost/rally"
    if test_connection("Local Database", local_url, "Local development and schema design"):
        connections_successful += 1
    connections_tested += 1
    
    # Test Railway production
    print("2️⃣ RAILWAY PRODUCTION DATABASE")
    railway_url = os.getenv("DATABASE_PUBLIC_URL")
    if railway_url:
        if test_connection("Railway Production", railway_url, "Production schema comparison and documentation"):
            connections_successful += 1
    else:
        print("   ⚠️  DATABASE_PUBLIC_URL not configured")
        print("   💡 Set this environment variable to test Railway connection\n")
    connections_tested += 1
    
    # Test Railway staging (if configured)
    print("3️⃣ RAILWAY STAGING DATABASE")
    staging_url = os.getenv("DATABASE_STAGING_URL")
    if staging_url:
        if test_connection("Railway Staging", staging_url, "Staging environment validation"):
            connections_successful += 1
        connections_tested += 1
    else:
        print("   ℹ️  DATABASE_STAGING_URL not configured (optional)")
        print("   💡 Configure if you have a staging environment\n")
    
    # Summary
    print("📊 VALIDATION SUMMARY")
    print("=" * 30)
    print(f"Connections tested: {connections_tested}")
    print(f"Successful connections: {connections_successful}")
    
    if connections_successful == connections_tested:
        print("✅ All configured connections successful!")
        print("💚 Ready to set up DbSchema connections")
    elif connections_successful > 0:
        print("⚠️  Some connections failed")
        print("💛 Fix failed connections before proceeding")
    else:
        print("❌ No successful connections")
        print("💔 Fix database configuration before using DbSchema")
    
    print("\n" + "=" * 50)
    print_dbschema_connection_guide()
    
    print("\n🔗 Next Steps:")
    print("1. Open DbSchema")
    print("2. Create new project: Rally Database")
    print("3. Add connections using the details above")
    print("4. Import schema from local database")
    print("5. Run: python data/dbschema/compare_schemas_dbschema.py")

if __name__ == "__main__":
    main() 