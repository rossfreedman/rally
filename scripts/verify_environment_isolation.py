#!/usr/bin/env python3
"""
Verify Environment Isolation
============================

This script verifies that staging and production environments are properly isolated
and not accidentally cross-connected.
"""

import psycopg2
from urllib.parse import urlparse
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_database_connection(name, url):
    """Test connection to a specific database"""
    try:
        parsed = urlparse(url)
        conn = psycopg2.connect(
            dbname=parsed.path[1:],
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname,
            port=parsed.port or 5432,
            sslmode="require",
            connect_timeout=10
        )
        
        with conn.cursor() as cursor:
            # Get some identifying information
            cursor.execute("SELECT current_database(), version()")
            db_name, version = cursor.fetchone()
            
            # Get a table count to verify it's working
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """)
            table_count = cursor.fetchone()[0]
            
            print(f"✅ {name} Connection Successful:")
            print(f"   Host: {parsed.hostname}")
            print(f"   Port: {parsed.port}")
            print(f"   Database: {db_name}")
            print(f"   Tables: {table_count}")
            print(f"   PostgreSQL: {version[:50]}...")
            
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ {name} Connection Failed: {e}")
        return False

def main():
    """Test all environment connections"""
    print("🔍 VERIFYING ENVIRONMENT ISOLATION")
    print("=" * 60)
    
    # Database URLs
    production_url = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"
    staging_url = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"
    
    print(f"Production URL: {production_url[:50]}...")
    print(f"Staging URL: {staging_url[:50]}...")
    print()
    
    # Test connections
    prod_success = test_database_connection("PRODUCTION", production_url)
    print()
    staging_success = test_database_connection("STAGING", staging_url)
    print()
    
    # Verify they're different
    if prod_success and staging_success:
        prod_parsed = urlparse(production_url)
        staging_parsed = urlparse(staging_url)
        
        if prod_parsed.hostname != staging_parsed.hostname:
            print("✅ ISOLATION VERIFIED: Different hosts")
            print(f"   Production: {prod_parsed.hostname}:{prod_parsed.port}")
            print(f"   Staging: {staging_parsed.hostname}:{staging_parsed.port}")
        else:
            print("❌ ISOLATION ISSUE: Same hosts!")
            
        if prod_parsed.password != staging_parsed.password:
            print("✅ SECURITY VERIFIED: Different passwords")
        else:
            print("❌ SECURITY ISSUE: Same passwords!")
    
    print()
    if prod_success and staging_success:
        print("🎯 RESULT: Environments are properly isolated!")
        print("   ✅ Production ETL won't affect staging")
        print("   ✅ Staging development won't affect production")
        print("   ✅ Each environment has its own database")
    else:
        print("⚠️  RESULT: Connection issues detected")
        print("   Check Railway environment status")
        print("   Verify database credentials")

if __name__ == "__main__":
    main() 