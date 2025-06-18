#!/usr/bin/env python3
"""
Quick script to check local database schema
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query

def check_schema():
    """Check the actual schema of users table"""
    print("=== CHECKING LOCAL DATABASE SCHEMA ===")
    
    # Check users table columns
    print("\n1. USERS TABLE COLUMNS:")
    try:
        columns_query = """
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            ORDER BY ordinal_position
        """
        columns = execute_query(columns_query)
        for col in columns:
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            print(f"   {col['column_name']}: {col['data_type']} ({nullable})")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Check actual user data for James
    print(f"\n2. JAMES REDLAND'S USER DATA:")
    try:
        # Use only columns we know exist
        user_query = """
            SELECT email, first_name, last_name 
            FROM users 
            WHERE email = 'jredland@gmail.com'
        """
        user_data = execute_query(user_query)
        if user_data:
            print(f"   Found user: {user_data[0]}")
        else:
            print("   User not found")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Check leagues table 
    print(f"\n3. LEAGUES TABLE:")
    try:
        leagues_query = "SELECT id, league_id, league_name FROM leagues LIMIT 5"
        leagues = execute_query(leagues_query)
        for league in leagues:
            print(f"   ID {league['id']}: '{league['league_id']}' -> '{league['league_name']}'")
    except Exception as e:
        print(f"   Error: {e}")

if __name__ == "__main__":
    check_schema() 