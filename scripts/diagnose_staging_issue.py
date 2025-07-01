#!/usr/bin/env python3
"""
Diagnose Staging Environment Issues
==================================

This script diagnoses what's wrong with the staging environment and 
tells you exactly what needs to be fixed.
"""

import psycopg2
import requests
from urllib.parse import urlparse
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_staging_app_response():
    """Test if the staging app responds and what database it's using"""
    print("🌐 TESTING STAGING APP RESPONSE")
    print("=" * 60)
    
    staging_url = "https://rally-staging.up.railway.app"
    
    try:
        response = requests.get(f"{staging_url}/health", timeout=10)
        print(f"✅ Staging app responds: {response.status_code}")
        
        # Try to get some info about the database from the app
        try:
            # If there's a debug endpoint that shows DB info
            debug_response = requests.get(f"{staging_url}/api/debug/database", timeout=5)
            if debug_response.status_code == 200:
                print(f"📊 Database info: {debug_response.text[:100]}...")
        except:
            pass
            
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Staging app not responding: {e}")
        return False

def test_staging_database_content():
    """Test what's in the staging database"""
    print("\n🗄️ TESTING STAGING DATABASE CONTENT")
    print("=" * 60)
    
    staging_db_url = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"
    
    try:
        parsed = urlparse(staging_db_url)
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
            # Check table count
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """)
            table_count = cursor.fetchone()[0]
            print(f"📊 Tables in staging database: {table_count}")
            
            # Check for key tables and their row counts
            key_tables = ['users', 'players', 'match_scores', 'leagues', 'clubs']
            
            for table in key_tables:
                try:
                    cursor.execute(f"""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' AND table_name = %s
                        )
                    """, (table,))
                    
                    if cursor.fetchone()[0]:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        print(f"   ✅ {table}: {count} records")
                    else:
                        print(f"   ❌ {table}: table missing")
                        
                except Exception as e:
                    print(f"   ⚠️ {table}: error checking ({e})")
            
            # Check if staging has recent data
            try:
                cursor.execute("SELECT MAX(created_at) FROM users WHERE created_at IS NOT NULL")
                result = cursor.fetchone()
                if result and result[0]:
                    print(f"📅 Most recent user: {result[0]}")
                else:
                    print("📅 No user creation dates found")
            except Exception as e:
                print(f"📅 Could not check user dates: {e}")
        
        conn.close()
        
        if table_count == 0:
            print("\n❌ DIAGNOSIS: Staging database is EMPTY")
            print("   🔧 SOLUTION: You need to run a clone script to populate it")
            return "empty"
        elif table_count < 20:
            print("\n⚠️ DIAGNOSIS: Staging database has minimal schema")
            print("   🔧 SOLUTION: You likely need to run a clone script")
            return "minimal"
        else:
            print("\n✅ DIAGNOSIS: Staging database has content")
            print("   🔍 The issue might be elsewhere (environment variables, etc.)")
            return "populated"
            
    except Exception as e:
        print(f"❌ Cannot connect to staging database: {e}")
        return "connection_failed"

def test_production_database_status():
    """Check production database to compare"""
    print("\n🏭 TESTING PRODUCTION DATABASE (for comparison)")
    print("=" * 60)
    
    production_db_url = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"
    
    try:
        parsed = urlparse(production_db_url)
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
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """)
            table_count = cursor.fetchone()[0]
            print(f"📊 Tables in production database: {table_count}")
            
            # Check users count as an indicator
            try:
                cursor.execute("SELECT COUNT(*) FROM users")
                user_count = cursor.fetchone()[0]
                print(f"👥 Production users: {user_count}")
            except Exception as e:
                print(f"👥 Could not count users: {e}")
        
        conn.close()
        return table_count
        
    except Exception as e:
        print(f"❌ Cannot connect to production database: {e}")
        return 0

def provide_recommendations(staging_db_status, staging_app_responds):
    """Provide specific recommendations based on diagnosis"""
    print("\n🎯 RECOMMENDATIONS")
    print("=" * 60)
    
    if staging_db_status == "empty":
        print("🔧 IMMEDIATE ACTION NEEDED:")
        print("   1. Run clone script to populate staging database:")
        print("      python data/etl/clone/clone_local_to_railway_STAGING_auto.py")
        print("   2. OR clone from production to staging:")
        print("      python scripts/clone_production_to_staging.py")
        print("")
        print("   The staging database is completely empty!")
        
    elif staging_db_status == "minimal":
        print("🔧 LIKELY ACTION NEEDED:")
        print("   1. Staging database has minimal data")
        print("   2. Consider running clone script to get fresh data:")
        print("      python data/etl/clone/clone_local_to_railway_STAGING_auto.py")
        
    elif staging_db_status == "populated":
        print("🔍 INVESTIGATE FURTHER:")
        print("   1. Staging database has data, so the issue might be:")
        print("      - Railway staging environment variables")
        print("      - Database schema differences")
        print("      - Application configuration")
        print("   2. Check Railway staging environment DATABASE_URL")
        
    elif staging_db_status == "connection_failed":
        print("❌ CONNECTION ISSUE:")
        print("   1. Cannot connect to staging database")
        print("   2. Check network connectivity")
        print("   3. Verify staging database credentials")
    
    if not staging_app_responds:
        print("\n🚨 STAGING APP NOT RESPONDING:")
        print("   1. Check Railway staging service status")
        print("   2. Check Railway staging logs")
        print("   3. Verify staging deployment succeeded")
    
    print("\n📋 NEXT STEPS:")
    print("   1. If database is empty → Run clone script")
    print("   2. If database has data → Check Railway environment config")
    print("   3. Test staging app after changes")

def main():
    """Run complete diagnosis"""
    print("🔍 STAGING ENVIRONMENT DIAGNOSIS")
    print("=" * 60)
    print("Checking what's wrong with staging and what needs to be fixed...\n")
    
    # Test staging app
    app_responds = test_staging_app_response()
    
    # Test staging database
    db_status = test_staging_database_content()
    
    # Test production for comparison
    prod_tables = test_production_database_status()
    
    # Provide recommendations
    provide_recommendations(db_status, app_responds)

if __name__ == "__main__":
    main() 