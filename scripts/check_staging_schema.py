#!/usr/bin/env python3
"""
Check staging database schema for missing tables and columns
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_staging_schema():
    """Check staging database schema for missing components"""
    
    print("🔍 Checking Staging Database Schema")
    print("=" * 50)
    
    # Staging database URL
    staging_url = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"
    
    try:
        # Parse and connect to staging database
        parsed = urlparse(staging_url)
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
            
            # Check all tables
            print("\n📋 All Tables in Staging Database:")
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
            
            tables = cursor.fetchall()
            for table in tables:
                print(f"   - {table[0]}")
            
            # Check for specific missing tables
            print("\n🔍 Checking for Required Tables:")
            
            required_tables = [
                'captain_messages',
                'weather_cache',
                'pickup_games',
                'pickup_game_participants',
                'groups',
                'group_members'
            ]
            
            for table in required_tables:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    )
                """, [table])
                
                exists = cursor.fetchone()[0]
                status = "✅" if exists else "❌"
                print(f"   {status} {table}")
            
            # Check users table structure
            print("\n👥 Users Table Structure:")
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'users'
                ORDER BY ordinal_position
            """)
            
            columns = cursor.fetchall()
            for col in columns:
                nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                print(f"   - {col[0]}: {col[1]} ({nullable})")
            
            # Check if team_id column exists in users table
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns
                    WHERE table_name = 'users' AND column_name = 'team_id'
                )
            """)
            
            team_id_exists = cursor.fetchone()[0]
            print(f"\n🎯 team_id column in users table: {'✅' if team_id_exists else '❌'}")
            
            # Check teams table structure
            print("\n🏆 Teams Table Structure:")
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'teams'
                ORDER BY ordinal_position
            """)
            
            team_columns = cursor.fetchall()
            for col in team_columns:
                nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                print(f"   - {col[0]}: {col[1]} ({nullable})")
        
        conn.close()
        print(f"\n✅ Schema check completed")
        
    except Exception as e:
        print(f"❌ Error checking schema: {e}")
        return False
    
    return True

if __name__ == "__main__":
    check_staging_schema() 