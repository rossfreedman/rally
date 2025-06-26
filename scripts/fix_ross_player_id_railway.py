#!/usr/bin/env python3
"""
Fix Ross's Player ID Issue on Railway
=====================================
This script specifically fixes rossfreedman@gmail.com's player association
on Railway by finding the matching player records and creating the association.
"""

import os
import sys
from urllib.parse import urlparse

import psycopg2

# Add the parent directory to path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one, execute_update

# Railway database connection
RAILWAY_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

def connect_to_railway():
    """Connect to Railway database"""
    parsed = urlparse(RAILWAY_URL)
    conn_params = {
        "dbname": parsed.path[1:],
        "user": parsed.username,
        "password": parsed.password,
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "sslmode": "require",
        "connect_timeout": 30,
    }
    return psycopg2.connect(**conn_params)


def find_ross_user(conn):
    """Find Ross's user record"""
    user = execute_query_one(conn, """
        SELECT id, email, first_name, last_name, league_context
        FROM users 
        WHERE email = %s
    """, ["rossfreedman@gmail.com"])
    
    if user:
        print(f"✅ Found user: {user['first_name']} {user['last_name']} (ID: {user['id']})")
        print(f"   League context: {user['league_context']}")
        return user
    else:
        print("❌ User rossfreedman@gmail.com not found")
        return None


def find_ross_players(conn):
    """Find potential player records for Ross"""
    players = execute_query(conn, """
        SELECT p.id, p.tenniscores_player_id, p.first_name, p.last_name,
               c.name as club_name, s.name as series_name, 
               l.league_name, l.id as league_db_id, l.league_id as league_string_id,
               p.is_active
        FROM players p
        JOIN clubs c ON p.club_id = c.id
        JOIN series s ON p.series_id = s.id  
        JOIN leagues l ON p.league_id = l.id
        WHERE p.first_name ILIKE %s AND p.last_name ILIKE %s
        ORDER BY p.is_active DESC, l.league_name
    """, ["Ross", "Freedman"])
    
    if players:
        print(f"✅ Found {len(players)} potential player record(s):")
        for i, player in enumerate(players, 1):
            status = "ACTIVE" if player['is_active'] else "INACTIVE"
            print(f"   {i}. Player ID: {player['tenniscores_player_id']} ({status})")
            print(f"      Name: {player['first_name']} {player['last_name']}")
            print(f"      Club: {player['club_name']}")
            print(f"      Series: {player['series_name']}")
            print(f"      League: {player['league_name']} (DB ID: {player['league_db_id']})")
            print()
        return players
    else:
        print("❌ No player records found for Ross Freedman")
        return []


def check_existing_associations(conn, user_id):
    """Check if Ross already has any player associations"""
    associations = execute_query(conn, """
        SELECT upa.tenniscores_player_id, upa.created_at,
               p.first_name, p.last_name, c.name as club_name, 
               s.name as series_name, l.league_name
        FROM user_player_associations upa
        LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
        LEFT JOIN clubs c ON p.club_id = c.id
        LEFT JOIN series s ON p.series_id = s.id
        LEFT JOIN leagues l ON p.league_id = l.id
        WHERE upa.user_id = %s
        ORDER BY upa.created_at DESC
    """, [user_id])
    
    if associations:
        print(f"⚠️  User already has {len(associations)} association(s):")
        for assoc in associations:
            print(f"   Player ID: {assoc['tenniscores_player_id']}")
            if assoc['first_name']:
                print(f"   Name: {assoc['first_name']} {assoc['last_name']}")
                print(f"   Club: {assoc['club_name']}")
                print(f"   Series: {assoc['series_name']}")
                print(f"   League: {assoc['league_name']}")
            else:
                print(f"   ⚠️  Player record not found in database")
            print(f"   Created: {assoc['created_at']}")
            print()
        return associations
    else:
        print("✅ No existing associations found")
        return []


def create_association(conn, user_id, player_record, league_context=None):
    """Create a user-player association"""
    try:
        # Update user's league context if provided
        if league_context:
            execute_update(conn, """
                UPDATE users 
                SET league_context = %s
                WHERE id = %s
            """, [league_context, user_id])
            print(f"✅ Updated user league_context to: {league_context}")
        
        # Create the association
        result = execute_update(conn, """
            INSERT INTO user_player_associations (user_id, tenniscores_player_id, created_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (user_id, tenniscores_player_id) DO NOTHING
        """, [user_id, player_record['tenniscores_player_id']])
        
        if result > 0:
            print(f"✅ Created association between user {user_id} and player {player_record['tenniscores_player_id']}")
            return True
        else:
            print(f"⚠️  Association already exists or failed to create")
            return False
            
    except Exception as e:
        print(f"❌ Error creating association: {e}")
        return False


def main():
    """Main execution function"""
    print("🔧 FIXING ROSS'S PLAYER ID ON RAILWAY")
    print("=" * 50)
    
    try:
        # Connect to Railway
        conn = connect_to_railway()
        print("✅ Connected to Railway database")
        
        # Find Ross's user record
        print("\n1. FINDING USER RECORD")
        print("-" * 30)
        user = find_ross_user(conn)
        if not user:
            return
            
        # Check existing associations
        print("\n2. CHECKING EXISTING ASSOCIATIONS")
        print("-" * 40)
        existing_associations = check_existing_associations(conn, user['id'])
        
        # Find potential player records
        print("\n3. FINDING PLAYER RECORDS")
        print("-" * 35)
        players = find_ross_players(conn)
        if not players:
            return
            
        # If no associations exist, create one
        if not existing_associations:
            print("\n4. CREATING ASSOCIATION")
            print("-" * 30)
            
            # Prefer Tennaqua + active players
            preferred_player = None
            for player in players:
                if (player['is_active'] and 
                    player['club_name'].lower() == 'tennaqua' and
                    'thursday' in player['series_name'].lower()):
                    preferred_player = player
                    break
            
            # Fallback to first active player
            if not preferred_player:
                for player in players:
                    if player['is_active']:
                        preferred_player = player
                        break
            
            # Fallback to first player
            if not preferred_player:
                preferred_player = players[0]
                
            print(f"🎯 Selected player:")
            print(f"   Player ID: {preferred_player['tenniscores_player_id']}")
            print(f"   Name: {preferred_player['first_name']} {preferred_player['last_name']}")
            print(f"   Club: {preferred_player['club_name']}")
            print(f"   Series: {preferred_player['series_name']}")
            print(f"   League: {preferred_player['league_name']}")
            
            # Create the association
            success = create_association(
                conn, 
                user['id'], 
                preferred_player, 
                league_context=preferred_player['league_db_id']
            )
            
            if success:
                print(f"\n✅ SUCCESS! Ross's player association has been created.")
                print(f"   The yellow alert should disappear on next login.")
            else:
                print(f"\n❌ FAILED to create association")
        else:
            print(f"\n✅ User already has associations - the session service should pick these up")
            print(f"   If you're still seeing the alert, it might be a session refresh issue.")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    main() 