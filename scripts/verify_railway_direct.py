#!/usr/bin/env python3
"""
Direct Railway database verification - bypasses local config
"""

from urllib.parse import urlparse

import psycopg2

RAILWAY_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"


def verify_railway_direct():
    """Verify Railway database directly"""
    print("🔍 DIRECT RAILWAY DATABASE VERIFICATION")
    print("=" * 60)

    parsed = urlparse(RAILWAY_URL)
    conn_params = {
        "dbname": parsed.path[1:],
        "user": parsed.username,
        "password": parsed.password,
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "sslmode": "require",
        "connect_timeout": 10,
    }

    print(f"🌐 Connecting to: {conn_params['host']}:{conn_params['port']}")
    print(f"📚 Database: {conn_params['dbname']}")

    try:
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()

        # Check critical tables
        print("\n📊 CRITICAL TABLES STATUS:")

        # player_history
        cursor.execute("SELECT COUNT(*) FROM player_history")
        ph_count = cursor.fetchone()[0]
        print(f"   player_history: {ph_count:,} records")

        if ph_count > 0:
            cursor.execute(
                "SELECT COUNT(*) FROM player_history WHERE player_id IS NOT NULL"
            )
            linked_count = cursor.fetchone()[0]
            print(f"   └─ With valid player links: {linked_count:,}")

            # Sample record
            cursor.execute(
                "SELECT * FROM player_history ORDER BY created_at DESC LIMIT 1"
            )
            sample = cursor.fetchone()
            if sample:
                print(
                    f"   └─ Latest record: Player {sample[1]}, PTI {sample[5]}, Date {sample[4]}"
                )

        # user_player_associations
        cursor.execute("SELECT COUNT(*) FROM user_player_associations")
        upa_count = cursor.fetchone()[0]
        print(f"   user_player_associations: {upa_count:,} records")

        if upa_count > 0:
            cursor.execute(
                """
                SELECT u.email, u.first_name, u.last_name, upa.is_primary
                FROM user_player_associations upa
                JOIN users u ON upa.user_id = u.id
                ORDER BY upa.created_at DESC
            """
            )
            associations = cursor.fetchall()
            print(f"   └─ User associations:")
            for assoc in associations:
                primary_text = " (PRIMARY)" if assoc[3] else ""
                print(f"      • {assoc[1]} {assoc[2]} ({assoc[0]}){primary_text}")

        # players (for context)
        cursor.execute("SELECT COUNT(*) FROM players")
        players_count = cursor.fetchone()[0]
        print(f"   players: {players_count:,} total")

        cursor.execute(
            "SELECT COUNT(*) FROM players WHERE tenniscores_player_id IS NOT NULL"
        )
        tc_players = cursor.fetchone()[0]
        print(f"   └─ With TC IDs: {tc_players:,}")

        # users (for context)
        cursor.execute("SELECT COUNT(*) FROM users")
        users_count = cursor.fetchone()[0]
        print(f"   users: {users_count:,} total")

        # Summary
        print(f"\n" + "=" * 60)
        print(f"🎯 CRITICAL GAPS STATUS:")

        if ph_count > 100000:
            print(f"✅ player_history: RESOLVED ({ph_count:,} records)")
        else:
            print(f"❌ player_history: MISSING ({ph_count:,} records)")

        if upa_count > 0:
            print(f"✅ user_player_associations: RESOLVED ({upa_count:,} records)")
        else:
            print(f"❌ user_player_associations: MISSING ({upa_count:,} records)")

        if ph_count > 100000 and upa_count > 0:
            print(f"\n🎉 ALL CRITICAL GAPS RESOLVED!")
            print(f"🌐 Your application should now work properly at:")
            print(f"   https://www.lovetorally.com")
        else:
            print(f"\n⚠️  Critical gaps still exist")

        conn.close()

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    verify_railway_direct()
