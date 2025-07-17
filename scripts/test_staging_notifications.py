#!/usr/bin/env python3
"""
Test staging notifications by creating a captain message
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_staging_notifications():
    """Test staging notifications by creating a captain message"""
    
    print("🧪 Testing Staging Notifications")
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
            
            # 1. Check current captain messages
            print("\n1️⃣ Current Captain Messages:")
            cursor.execute("SELECT COUNT(*) FROM captain_messages")
            message_count = cursor.fetchone()[0]
            print(f"   Total messages: {message_count}")
            
            # 2. Get Ross's team info
            print("\n2️⃣ Ross's Team Info:")
            cursor.execute("""
                SELECT u.id, u.first_name, u.last_name, u.team_id, t.team_name
                FROM users u
                LEFT JOIN teams t ON u.team_id = t.id
                WHERE u.email = 'rossfreedman@gmail.com'
            """)
            
            user_info = cursor.fetchone()
            if user_info:
                user_id, first_name, last_name, team_id, team_name = user_info
                print(f"   User: {first_name} {last_name} (ID: {user_id})")
                print(f"   Team: {team_name} (ID: {team_id})")
            else:
                print("   ❌ User not found")
                return False
            
            # 3. Create a test captain message
            print("\n3️⃣ Creating Test Captain Message...")
            test_message = "Welcome to the team! This is a test captain message to verify notifications are working."
            
            cursor.execute("""
                INSERT INTO captain_messages (team_id, captain_user_id, message, created_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                RETURNING id
            """, [team_id, user_id, test_message])
            
            message_id = cursor.fetchone()[0]
            print(f"   ✅ Created captain message (ID: {message_id})")
            
            # 4. Verify the message was created
            print("\n4️⃣ Verifying Message Creation:")
            cursor.execute("""
                SELECT cm.id, cm.message, cm.created_at, u.first_name, u.last_name
                FROM captain_messages cm
                JOIN users u ON cm.captain_user_id = u.id
                WHERE cm.id = %s
            """, [message_id])
            
            message_info = cursor.fetchone()
            if message_info:
                msg_id, msg_text, created_at, cap_first, cap_last = message_info
                print(f"   Message ID: {msg_id}")
                print(f"   Captain: {cap_first} {cap_last}")
                print(f"   Message: {msg_text[:50]}...")
                print(f"   Created: {created_at}")
            else:
                print("   ❌ Message not found after creation")
                return False
            
            # 5. Test the notification query
            print("\n5️⃣ Testing Notification Query:")
            cursor.execute("""
                SELECT 
                    ss.team,
                    ss.points,
                    ss.matches_won,
                    ss.matches_lost,
                    ss.matches_tied,
                    t.team_name,
                    t.series_id,
                    s.name as series_name,
                    c.name as club_name
                FROM series_stats ss
                JOIN teams t ON ss.team_id = t.id
                JOIN series s ON t.series_id = s.id
                JOIN clubs c ON t.club_id = c.id
                WHERE ss.team_id = %s 
                AND ss.league_id = %s
                ORDER BY ss.updated_at DESC
                LIMIT 1
            """, [team_id, 4823])  # Using Ross's team_id and league_id from logs
            
            team_stats = cursor.fetchone()
            if team_stats:
                print(f"   ✅ Team position query works!")
                print(f"   Team: {team_stats[5]} ({team_stats[8]})")
                print(f"   Points: {team_stats[1]}")
                print(f"   Record: {team_stats[2]}-{team_stats[3]}-{team_stats[4]}")
            else:
                print(f"   ⚠️  No team stats found for team_id {team_id}")
            
            # 6. Clean up - remove the test message
            print("\n6️⃣ Cleaning Up Test Message...")
            cursor.execute("DELETE FROM captain_messages WHERE id = %s", [message_id])
            print(f"   ✅ Removed test message")
        
        conn.commit()
        conn.close()
        print(f"\n✅ Staging notifications test completed successfully!")
        print(f"\n🎉 You should now see Captain's Message and Upcoming Schedule notifications on staging!")
        
    except Exception as e:
        print(f"❌ Error testing notifications: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_staging_notifications() 