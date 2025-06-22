#!/usr/bin/env python3
"""
⚠️  DEPRECATED SCRIPT ⚠️
This script references the old users.tenniscores_player_id column which has been removed.
The new schema uses user_player_associations table for many-to-many relationships.
Consider using the new association-based queries instead.
"""

import psycopg2
from psycopg2.extras import RealDictCursor

# Railway database URL
db_url = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

print("🔍 Checking existing users in Railway database...")
conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
cursor = conn.cursor()

cursor.execute(
    """
    SELECT u.id, u.first_name, u.last_name, u.email, 
           c.name as club_name, s.name as series_name, u.tenniscores_player_id
    FROM users u
    LEFT JOIN clubs c ON u.club_id = c.id
    LEFT JOIN series s ON u.series_id = s.id
    ORDER BY u.last_name, u.first_name
"""
)

users = cursor.fetchall()
print(f"📊 Found {len(users)} users in Railway database:")
print()

users_without_ids = []
for user in users:
    player_id_status = "✅ Has ID" if user["tenniscores_player_id"] else "❌ Missing ID"
    print(
        f'  • {user["first_name"]} {user["last_name"]} ({user["club_name"]}, {user["series_name"]}) - {player_id_status}'
    )

    if not user["tenniscores_player_id"]:
        users_without_ids.append(user)

print(f"\n📋 Summary: {len(users_without_ids)} users need player IDs assigned")

cursor.close()
conn.close()
