#!/usr/bin/env python3
"""
Check if Groups Tables Exist on Staging
=======================================
"""

import os
import sys

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Set the staging database URL
os.environ['DATABASE_PUBLIC_URL'] = 'postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway'

from database_utils import execute_query_one, execute_query

def check_groups_tables():
    """Check if groups tables exist on staging"""
    print("🔍 Checking Groups Tables on Staging")
    print("=" * 40)
    
    try:
        # Check if groups table exists
        result = execute_query_one("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'groups'
        """)
        
        if result:
            print("✅ 'groups' table EXISTS")
        else:
            print("❌ 'groups' table MISSING")
            
        # Check if group_members table exists
        result = execute_query_one("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'group_members'
        """)
        
        if result:
            print("✅ 'group_members' table EXISTS")
        else:
            print("❌ 'group_members' table MISSING")
            
        # List all tables to see what's actually there
        print("\n📋 All Tables on Staging:")
        tables = execute_query("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        
        for table in tables:
            table_name = table['table_name']
            if 'group' in table_name.lower():
                print(f"   🎯 {table_name}")
            else:
                print(f"   - {table_name}")
                
        print(f"\n📊 Total tables: {len(tables)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking tables: {e}")
        return False

def main():
    """Main function"""
    if check_groups_tables():
        print("\n✅ Check complete!")
    else:
        print("\n❌ Check failed!")

if __name__ == "__main__":
    main() 