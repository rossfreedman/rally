#!/usr/bin/env python3
"""
Populate team associations for users in staging database
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def populate_staging_team_associations():
    """Populate team_id for users in staging based on their player associations"""
    
    print("🔗 Populating Team Associations for Staging Users")
    print("=" * 60)
    
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
            
            # 1. Check current state
            print("\n1️⃣ Current State:")
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            print(f"   Total users: {total_users}")
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE team_id IS NOT NULL")
            users_with_team = cursor.fetchone()[0]
            print(f"   Users with team_id: {users_with_team}")
            
            cursor.execute("SELECT COUNT(*) FROM user_player_associations")
            total_associations = cursor.fetchone()[0]
            print(f"   Total user-player associations: {total_associations}")
            
            cursor.execute("SELECT COUNT(*) FROM user_player_associations WHERE is_primary = true")
            primary_associations = cursor.fetchone()[0]
            print(f"   Primary associations: {primary_associations}")
            
            # 2. Show sample users and their associations
            print("\n2️⃣ Sample Users and Associations:")
            cursor.execute("""
                SELECT u.id, u.email, u.first_name, u.last_name, u.team_id,
                       upa.tenniscores_player_id, upa.is_primary,
                       p.team_id as player_team_id, p.first_name as player_first_name, p.last_name as player_last_name
                FROM users u
                LEFT JOIN user_player_associations upa ON u.id = upa.user_id
                LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                ORDER BY u.id, upa.is_primary DESC
                LIMIT 10
            """)
            
            users = cursor.fetchall()
            for user in users:
                print(f"   User {user[0]}: {user[2]} {user[3]} ({user[1]})")
                print(f"     Current team_id: {user[4]}")
                print(f"     Player ID: {user[5]}")
                print(f"     Is Primary: {user[6]}")
                print(f"     Player Team ID: {user[7]}")
                print(f"     Player Name: {user[8]} {user[9]}")
                print()
            
            # 3. Populate team_id for users based on primary player associations
            print("\n3️⃣ Populating team_id for users...")
            cursor.execute("""
                UPDATE users 
                SET team_id = p.team_id
                FROM user_player_associations upa
                JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                WHERE upa.user_id = users.id 
                AND upa.is_primary = true
                AND p.team_id IS NOT NULL
                AND users.team_id IS NULL
            """)
            
            updated_count = cursor.rowcount
            print(f"   ✅ Updated {updated_count} users with team_id")
            
            # 4. For users without primary associations, use any available association
            print("\n4️⃣ Populating team_id for users without primary associations...")
            cursor.execute("""
                UPDATE users 
                SET team_id = p.team_id
                FROM user_player_associations upa
                JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                WHERE upa.user_id = users.id 
                AND p.team_id IS NOT NULL
                AND users.team_id IS NULL
                AND NOT EXISTS (
                    SELECT 1 FROM user_player_associations upa2 
                    WHERE upa2.user_id = users.id AND upa2.is_primary = true
                )
            """)
            
            additional_updated = cursor.rowcount
            print(f"   ✅ Updated {additional_updated} additional users with team_id")
            
            # 5. Verify the results
            print("\n5️⃣ Verification:")
            cursor.execute("SELECT COUNT(*) FROM users WHERE team_id IS NOT NULL")
            final_users_with_team = cursor.fetchone()[0]
            print(f"   Users with team_id: {final_users_with_team}")
            
            # Show some examples
            cursor.execute("""
                SELECT u.id, u.first_name, u.last_name, u.team_id, t.team_name
                FROM users u
                LEFT JOIN teams t ON u.team_id = t.id
                WHERE u.team_id IS NOT NULL
                ORDER BY u.id
                LIMIT 5
            """)
            
            examples = cursor.fetchall()
            print(f"   Examples:")
            for example in examples:
                print(f"     User {example[0]}: {example[1]} {example[2]} -> Team {example[3]} ({example[4]})")
            
            # 6. Check for users still without team_id
            cursor.execute("""
                SELECT u.id, u.first_name, u.last_name, u.email
                FROM users u
                WHERE u.team_id IS NULL
                ORDER BY u.id
                LIMIT 5
            """)
            
            users_without_team = cursor.fetchall()
            if users_without_team:
                print(f"\n6️⃣ Users still without team_id:")
                for user in users_without_team:
                    print(f"     User {user[0]}: {user[1]} {user[2]} ({user[3]})")
            else:
                print(f"\n6️⃣ All users now have team_id! ✅")
        
        conn.commit()
        conn.close()
        print(f"\n✅ Team association population completed")
        
    except Exception as e:
        print(f"❌ Error populating team associations: {e}")
        return False
    
    return True

if __name__ == "__main__":
    populate_staging_team_associations() 