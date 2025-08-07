#!/usr/bin/env python3
"""
Execute SQL script on Railway production database from server environment
This runs the tenniscores_match_id fix directly on Railway infrastructure
"""

import os
import psycopg2
import psycopg2.extras
import sys

def get_database_url():
    """Get DATABASE_URL from Railway environment"""
    # Try public URL first (works from Railway runner)
    database_url = os.environ.get('DATABASE_PUBLIC_URL')
    if database_url:
        print(f"🔌 Using DATABASE_PUBLIC_URL")
        return database_url
    
    # Fallback to internal URL
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        print(f"🔌 Using DATABASE_URL")
        return database_url
        
    print("❌ ERROR: No DATABASE_URL or DATABASE_PUBLIC_URL found")
    print("Make sure this script is running in Railway environment")
    sys.exit(1)

def execute_sql_file(sql_file_path):
    """Execute SQL file on production database"""
    if not os.path.exists(sql_file_path):
        print(f"❌ ERROR: SQL file not found: {sql_file_path}")
        sys.exit(1)
    
    print(f"🔍 Reading SQL file: {sql_file_path}")
    with open(sql_file_path, 'r') as f:
        sql_content = f.read()
    
    # Count UPDATE statements
    update_count = sql_content.count('UPDATE match_scores')
    print(f"📊 Found {update_count} UPDATE statements in script")
    
    database_url = get_database_url()
    print(f"🔌 Connecting to production database...")
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print(f"✅ Connected! Executing SQL script...")
        print(f"⏰ This may take several minutes for {update_count} updates...")
        
        # Execute the entire script
        cursor.execute(sql_content)
        
        print(f"✅ SQL script executed successfully!")
        print(f"📊 Checking results...")
        
        # Get the verification results (script should end with verification query)
        results = cursor.fetchall()
        if results:
            for row in results:
                print(f"📈 Results: {row}")
        
        conn.close()
        print(f"🎉 SUCCESS! Database fix completed!")
        
    except Exception as e:
        print(f"❌ ERROR executing SQL: {e}")
        sys.exit(1)

def main():
    print("🚀 Railway SQL Executor")
    print("=" * 40)
    
    # Path to the SQL fix script
    sql_file = "fix_production_tenniscores_match_id_REAL.sql"
    
    if len(sys.argv) > 1:
        sql_file = sys.argv[1]
    
    execute_sql_file(sql_file)

if __name__ == "__main__":
    main()
