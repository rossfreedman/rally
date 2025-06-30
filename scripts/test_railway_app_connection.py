#!/usr/bin/env python3
"""
Test Railway Application Database Connection
Tests what database the Railway application is actually connecting to
"""

import os
import psycopg2
from urllib.parse import urlparse

def test_environment_variables():
    """Test what database environment variables are set"""
    print("🔍 TESTING ENVIRONMENT VARIABLES")
    print("=" * 60)
    
    env_vars = [
        'DATABASE_URL',
        'DATABASE_PUBLIC_URL', 
        'RAILWAY_ENVIRONMENT',
        'PGDATABASE',
        'PGHOST',
        'PGPORT',
        'PGUSER'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            # Mask passwords in URLs
            if 'postgresql://' in value or 'postgres://' in value:
                parsed = urlparse(value)
                masked_value = f"{parsed.scheme}://{parsed.username}:***@{parsed.hostname}:{parsed.port}{parsed.path}"
                print(f"   ✅ {var}: {masked_value}")
            else:
                print(f"   ✅ {var}: {value}")
        else:
            print(f"   ❌ {var}: Not set")

def test_database_config_module():
    """Test what the database_config module returns"""
    print(f"\n🔍 TESTING database_config MODULE")
    print("=" * 60)
    
    try:
        # Set environment to simulate Railway
        os.environ['RAILWAY_ENVIRONMENT'] = 'production'
        
        from database_config import get_db_url
        db_url = get_db_url()
        
        # Parse and mask the URL
        parsed = urlparse(db_url)
        masked_url = f"{parsed.scheme}://{parsed.username}:***@{parsed.hostname}:{parsed.port}{parsed.path}"
        
        print(f"   📊 get_db_url() returns: {masked_url}")
        print(f"   📊 Host: {parsed.hostname}")
        print(f"   📊 Port: {parsed.port}")
        print(f"   📊 Database: {parsed.path[1:]}")
        
        # Test if it's local vs Railway
        if parsed.hostname == 'localhost':
            print(f"   ⚠️ WARNING: Still connecting to localhost!")
        elif 'railway' in parsed.hostname:
            print(f"   ✅ Connecting to Railway database")
        else:
            print(f"   ❓ Unknown host: {parsed.hostname}")
            
        return db_url
        
    except Exception as e:
        print(f"   ❌ Failed to get database URL: {e}")
        return None

def test_actual_database_connection(db_url):
    """Test connection to the actual database and check data"""
    print(f"\n🔍 TESTING ACTUAL DATABASE CONNECTION")
    print("=" * 60)
    
    if not db_url:
        print("   ❌ No database URL to test")
        return
    
    try:
        # Parse URL and create connection
        parsed = urlparse(db_url)
        conn_params = {
            "dbname": parsed.path[1:],
            "user": parsed.username,
            "password": parsed.password,
            "host": parsed.hostname,
            "port": parsed.port or 5432,
        }
        
        if 'railway' in parsed.hostname:
            conn_params["sslmode"] = "require"
            conn_params["connect_timeout"] = 30
        
        conn = psycopg2.connect(**conn_params)
        
        # Test basic query
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM match_scores")
            total_matches = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT league_id, COUNT(*) as count 
                FROM match_scores 
                WHERE league_id IS NOT NULL 
                GROUP BY league_id 
                ORDER BY league_id
            """)
            league_counts = cursor.fetchall()
            
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM match_scores 
                WHERE league_id = 4489 
                AND (home_team LIKE '%Tennaqua%' OR away_team LIKE '%Tennaqua%')
            """)
            tennaqua_matches = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"   ✅ Connected successfully!")
        print(f"   📊 Total matches: {total_matches}")
        print(f"   📊 Leagues in match_scores:")
        for league_id, count in league_counts:
            print(f"      - League {league_id}: {count} matches")
        print(f"   📊 Tennaqua APTA matches (league 4489): {tennaqua_matches}")
        
        # Determine if this is the fixed database
        has_4489_data = any(league_id == 4489 for league_id, _ in league_counts)
        has_orphan_data = any(league_id in [4543, 4544, 4545, 4546] for league_id, _ in league_counts)
        
        if has_4489_data and not has_orphan_data:
            print(f"   ✅ This appears to be the FIXED database")
        elif has_orphan_data:
            print(f"   ⚠️ This appears to be the UNFIXED database (has orphaned leagues)")
        else:
            print(f"   ❓ Unknown database state")
            
        return {
            'total_matches': total_matches,
            'tennaqua_matches': tennaqua_matches,
            'is_fixed': has_4489_data and not has_orphan_data
        }
        
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return None

def test_app_imports():
    """Test if we can import the app modules and what they use"""
    print(f"\n🔍 TESTING APP MODULE IMPORTS")
    print("=" * 60)
    
    try:
        # Test database_utils import
        from database_utils import execute_query_one
        
        # Test what database it actually uses
        result = execute_query_one("SELECT COUNT(*) as count FROM leagues")
        print(f"   ✅ database_utils works: {result['count']} leagues")
        
        # Test match query
        tennaqua_result = execute_query_one("""
            SELECT COUNT(*) as count FROM match_scores 
            WHERE league_id = 4489 
            AND (home_team LIKE '%Tennaqua%' OR away_team LIKE '%Tennaqua%')
        """)
        
        print(f"   📊 Tennaqua matches via database_utils: {tennaqua_result['count']}")
        
        return tennaqua_result['count']
        
    except Exception as e:
        print(f"   ❌ App imports failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main testing function"""
    print("🚀 RAILWAY APPLICATION DATABASE CONNECTION TEST")
    print("=" * 60)
    print("Testing what database the application actually connects to...")
    
    # Test environment
    test_environment_variables()
    
    # Test database config
    db_url = test_database_config_module()
    
    # Test actual connection
    db_info = test_actual_database_connection(db_url)
    
    # Test app imports
    app_matches = test_app_imports()
    
    # Summary
    print(f"\n🎯 DIAGNOSIS")
    print("=" * 60)
    
    if db_info and app_matches is not None:
        if db_info['is_fixed'] and db_info['tennaqua_matches'] > 0:
            print(f"   ✅ Database connection: FIXED Railway database")
            print(f"   ✅ Tennaqua matches available: {db_info['tennaqua_matches']}")
            
            if app_matches == 0:
                print(f"   🚨 ISSUE: App modules return 0 matches despite fixed database!")
                print(f"   💡 This suggests a caching or connection issue in the application")
            elif app_matches == db_info['tennaqua_matches']:
                print(f"   ✅ App modules work correctly")
            else:
                print(f"   ⚠️ App modules return different count: {app_matches}")
                
        else:
            print(f"   ❌ Database: Not the fixed Railway database")
            
    print(f"\n💡 NEXT STEPS:")
    if db_info and db_info['is_fixed'] and app_matches == 0:
        print(f"   • Railway app may need restart to clear cached connections")
        print(f"   • Check if Railway app is using correct DATABASE_URL")
        print(f"   • Verify no connection pooling issues")
    elif not db_info or not db_info['is_fixed']:
        print(f"   • Application is connecting to wrong/unfixed database")
        print(f"   • Check Railway environment variables")

if __name__ == "__main__":
    main() 