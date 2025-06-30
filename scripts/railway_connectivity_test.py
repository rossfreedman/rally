#!/usr/bin/env python3
"""
Simple Railway Connectivity Test
Simple script to test database connectivity from Railway environment
"""

import os
import psycopg2
from urllib.parse import urlparse

def main():
    print("🚀 RAILWAY DATABASE CONNECTIVITY TEST")
    print("=" * 50)
    
    # Get database URL from environment
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL not found in environment")
        return
    
    print(f"✅ DATABASE_URL found")
    
    try:
        # Parse and connect
        parsed = urlparse(db_url)
        
        conn_params = {
            "dbname": parsed.path[1:],
            "user": parsed.username,
            "password": parsed.password,
            "host": parsed.hostname,
            "port": parsed.port or 5432,
        }
        
        # Add SSL for Railway
        if 'railway' in parsed.hostname or 'ballast' in parsed.hostname:
            conn_params["sslmode"] = "require"
            conn_params["connect_timeout"] = 30
        
        print(f"📊 Connecting to: {parsed.hostname}:{parsed.port}")
        
        conn = psycopg2.connect(**conn_params)
        
        with conn.cursor() as cursor:
            # Basic connectivity test
            cursor.execute("SELECT 1")
            print("✅ Database connection successful")
            
            # Check league data
            cursor.execute("SELECT id, league_name FROM leagues ORDER BY id")
            leagues = cursor.fetchall()
            print(f"📊 Leagues available: {len(leagues)}")
            for league_id, name in leagues:
                print(f"   - {league_id}: {name}")
            
            # Check match data by league
            cursor.execute("""
                SELECT league_id, COUNT(*) as count 
                FROM match_scores 
                WHERE league_id IS NOT NULL 
                GROUP BY league_id 
                ORDER BY league_id
            """)
            match_counts = cursor.fetchall()
            print(f"📊 Match data by league:")
            for league_id, count in match_counts:
                print(f"   - League {league_id}: {count} matches")
            
            # Specific test for Ross Freedman / Tennaqua
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM match_scores 
                WHERE league_id = 4489 
                AND (home_team LIKE '%Tennaqua%' OR away_team LIKE '%Tennaqua%')
            """)
            tennaqua_count = cursor.fetchone()[0]
            print(f"📊 Tennaqua APTA matches (league 4489): {tennaqua_count}")
            
            # Test user data
            cursor.execute("""
                SELECT u.first_name, u.last_name, l.league_name, c.name as club
                FROM users u
                JOIN user_player_associations upa ON u.id = upa.user_id AND upa.is_primary = true
                JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                JOIN leagues l ON p.league_id = l.id
                JOIN clubs c ON p.club_id = c.id
                WHERE p.tenniscores_player_id = 'nndz-WkMrK3didjlnUT09'
            """)
            user_data = cursor.fetchone()
            if user_data:
                print(f"📊 Test user found: {user_data[0]} {user_data[1]} @ {user_data[3]} ({user_data[2]})")
            else:
                print(f"❌ Test user not found")
        
        conn.close()
        
        # Summary
        print(f"\n🎯 SUMMARY:")
        has_apta_data = any(league_id == 4489 for league_id, _ in match_counts)
        has_orphan_data = any(league_id in [4543, 4544, 4545, 4546] for league_id, _ in match_counts)
        
        if has_apta_data and tennaqua_count > 0:
            print(f"✅ Database appears FIXED - APTA league data accessible")
            print(f"✅ Tennaqua has {tennaqua_count} matches available")
        elif has_orphan_data:
            print(f"❌ Database appears BROKEN - orphaned league data detected")
        else:
            print(f"❓ Database state unclear")
            
        if user_data:
            print(f"✅ User associations working correctly")
        else:
            print(f"❌ User association issues detected")
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

if __name__ == "__main__":
    main() 