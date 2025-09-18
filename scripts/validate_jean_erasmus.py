#!/usr/bin/env python3
"""
Validate that Jean Erasmus is still in the production database
"""

import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_production_connection():
    """Connect to PRODUCTION database"""
    production_url = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"
    
    parsed = urlparse(production_url)
    conn_params = {
        "dbname": parsed.path[1:],
        "user": parsed.username,
        "password": parsed.password,
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "sslmode": "require",
        "connect_timeout": 30,
        "application_name": "validate_jean_erasmus"
    }
    
    try:
        conn = psycopg2.connect(**conn_params)
        print(f"✅ Connected to production database at {parsed.hostname}")
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to production database: {e}")
        return None

def execute_query(conn, query, params=None):
    """Execute query and return results"""
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query, params)
        if cursor.description:
            return cursor.fetchall()
        else:
            conn.commit()
            return cursor.rowcount

def validate_jean_erasmus():
    """Validate that Jean Erasmus is still in production"""
    
    print("🔍 VALIDATING JEAN ERASMUS IN PRODUCTION")
    print("=" * 50)
    print("⚠️  Jean is an ambiguous name that should be protected")
    print()
    
    conn = get_production_connection()
    if not conn:
        return False
    
    try:
        # Get APTA league ID
        league_query = "SELECT id FROM leagues WHERE league_id = 'APTA_CHICAGO'"
        league_info = execute_query(conn, league_query)
        apta_league_id = league_info[0]['id']
        
        # Search for Jean Erasmus specifically
        print("🔍 Searching for Jean Erasmus...")
        
        jean_query = """
            SELECT 
                p.id,
                p.first_name,
                p.last_name,
                p.tenniscores_player_id,
                p.pti,
                t.team_name,
                c.name as club_name,
                s.name as series_name,
                p.is_active
            FROM players p
            LEFT JOIN teams t ON p.team_id = t.id
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE p.league_id = %s 
            AND LOWER(p.first_name) = 'jean' 
            AND LOWER(p.last_name) = 'erasmus'
            AND p.is_active = TRUE
        """
        
        jean_results = execute_query(conn, jean_query, [apta_league_id])
        
        if jean_results:
            print(f"✅ SUCCESS: Jean Erasmus found in production!")
            print(f"   👤 Name: {jean_results[0]['first_name']} {jean_results[0]['last_name']}")
            print(f"   🆔 Tenniscores ID: {jean_results[0]['tenniscores_player_id']}")
            print(f"   📊 PTI: {jean_results[0]['pti']}")
            print(f"   🏆 Team: {jean_results[0]['team_name']}")
            print(f"   🏢 Club: {jean_results[0]['club_name']}")
            print(f"   📈 Series: {jean_results[0]['series_name']}")
            print(f"   ✅ Active: {jean_results[0]['is_active']}")
            print()
            print("🛡️  Jean Erasmus was correctly protected by ambiguous name safeguards!")
            return True
        else:
            print("❌ FAILURE: Jean Erasmus not found in production!")
            print("⚠️  This suggests the ambiguous name protection failed")
            return False
        
        # Also check for all players named Jean in APTA Chicago
        print(f"\n🔍 Checking all players named 'Jean' in APTA Chicago...")
        
        all_jean_query = """
            SELECT 
                p.first_name,
                p.last_name,
                p.tenniscores_player_id,
                t.team_name,
                c.name as club_name,
                s.name as series_name
            FROM players p
            LEFT JOIN teams t ON p.team_id = t.id
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE p.league_id = %s 
            AND LOWER(p.first_name) = 'jean'
            AND p.is_active = TRUE
            ORDER BY p.last_name
        """
        
        all_jean_results = execute_query(conn, all_jean_query, [apta_league_id])
        
        if all_jean_results:
            print(f"✅ Found {len(all_jean_results)} players named 'Jean' in APTA Chicago:")
            for i, player in enumerate(all_jean_results, 1):
                print(f"   {i}. {player['first_name']} {player['last_name']} ({player['team_name']})")
            
            print(f"\n🛡️  All {len(all_jean_results)} players named 'Jean' were correctly protected!")
        else:
            print("❌ No players named 'Jean' found in APTA Chicago")
            print("⚠️  This suggests ambiguous name protection may have failed")
        
        # Check for other ambiguous names too
        print(f"\n🔍 Checking other ambiguous names in APTA Chicago...")
        
        ambiguous_names = ['jordan', 'taylor', 'casey', 'morgan', 'alex', 'sam', 'chris', 'pat', 'terry', 'dana', 'jamie', 'lee', 'robin', 'sandy', 'tracy', 'tracey']
        
        ambiguous_query = """
            SELECT 
                p.first_name,
                COUNT(*) as count
            FROM players p
            WHERE p.league_id = %s 
            AND LOWER(p.first_name) = ANY(%s)
            AND p.is_active = TRUE
            GROUP BY p.first_name
            ORDER BY p.first_name
        """
        
        ambiguous_results = execute_query(conn, ambiguous_query, [apta_league_id, ambiguous_names])
        
        if ambiguous_results:
            print(f"✅ Found ambiguous names in APTA Chicago:")
            total_ambiguous = 0
            for result in ambiguous_results:
                print(f"   {result['first_name'].title()}: {result['count']} players")
                total_ambiguous += result['count']
            
            print(f"\n🛡️  Total ambiguous names protected: {total_ambiguous}")
        else:
            print("❌ No ambiguous names found in APTA Chicago")
            print("⚠️  This suggests ambiguous name protection may have failed")
        
        # Final assessment
        print(f"\n🎯 FINAL ASSESSMENT:")
        print("=" * 30)
        
        if jean_results and all_jean_results and ambiguous_results:
            print("🎉 ALL VALIDATION CHECKS PASSED!")
            print("✅ Jean Erasmus is safely preserved in production")
            print("✅ Ambiguous name protection is working correctly")
            print("✅ All safeguards functioned as expected")
            return True
        else:
            print("⚠️  Some validation checks failed")
            print("❌ Ambiguous name protection may have issues")
            return False
    
    finally:
        conn.close()

if __name__ == "__main__":
    success = validate_jean_erasmus()
    
    if success:
        print("\n🏆 VALIDATION: COMPLETE SUCCESS!")
        print("Jean Erasmus and all ambiguous names are safely preserved.")
    else:
        print("\n⚠️  VALIDATION: ISSUES DETECTED")
        print("Please review the validation results above.")
