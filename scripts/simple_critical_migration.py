#!/usr/bin/env python3
"""
Simple, robust migration for critical missing tables
Focus: player_history and user_player_associations
"""

import os
import sys
from urllib.parse import urlparse

import psycopg2

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_config import get_db

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
        "connect_timeout": 10,
    }
    return psycopg2.connect(**conn_params)


def create_simple_mapping(local_conn, railway_conn):
    """Create simple player ID mapping"""
    print("🗺️  Creating player mapping...")

    local_cursor = local_conn.cursor()
    railway_cursor = railway_conn.cursor()

    # Get mappings via tenniscores_player_id
    local_cursor.execute(
        "SELECT tenniscores_player_id, id FROM players WHERE tenniscores_player_id IS NOT NULL"
    )
    local_map = dict(local_cursor.fetchall())

    railway_cursor.execute(
        "SELECT tenniscores_player_id, id FROM players WHERE tenniscores_player_id IS NOT NULL"
    )
    railway_map = dict(railway_cursor.fetchall())

    # Create local_id -> railway_id mapping
    mapping = {}
    for tc_id, local_id in local_map.items():
        if tc_id in railway_map:
            mapping[local_id] = railway_map[tc_id]

    print(f"  ✅ Mapped {len(mapping):,} players")
    return mapping


def migrate_player_history_simple(local_conn, railway_conn, mapping):
    """Simple player_history migration"""
    print("\n📊 Migrating player_history...")

    local_cursor = local_conn.cursor()
    railway_cursor = railway_conn.cursor()

    # Clear existing data
    railway_cursor.execute("TRUNCATE TABLE player_history CASCADE")
    railway_conn.commit()

    # Get mappable records count
    local_cursor.execute(
        "SELECT COUNT(*) FROM player_history WHERE player_id IN %s",
        (tuple(mapping.keys()),),
    )
    total = local_cursor.fetchone()[0]
    print(f"  Records to migrate: {total:,}")

    # Migrate in small batches
    batch_size = 500
    migrated = 0

    local_cursor.execute(
        """
        SELECT player_id, league_id, series, date, end_pti, created_at
        FROM player_history 
        WHERE player_id IN %s
        ORDER BY id
    """,
        (tuple(mapping.keys()),),
    )

    batch = []
    while True:
        row = local_cursor.fetchone()
        if not row:
            break

        local_player_id = row[0]
        railway_player_id = mapping[local_player_id]

        # Map to Railway IDs
        mapped_row = (railway_player_id, row[1], row[2], row[3], row[4], row[5])
        batch.append(mapped_row)

        if len(batch) >= batch_size:
            # Insert batch
            railway_cursor.executemany(
                """
                INSERT INTO player_history (player_id, league_id, series, date, end_pti, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """,
                batch,
            )
            railway_conn.commit()

            migrated += len(batch)
            print(f"    ✅ {migrated:,}/{total:,} records")
            batch = []

    # Insert remaining batch
    if batch:
        railway_cursor.executemany(
            """
            INSERT INTO player_history (player_id, league_id, series, date, end_pti, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """,
            batch,
        )
        railway_conn.commit()
        migrated += len(batch)

    print(f"  ✅ Completed: {migrated:,} records migrated")
    return migrated


def migrate_user_associations_simple(local_conn, railway_conn, player_mapping):
    """Simple user_player_associations migration"""
    print("\n👥 Migrating user_player_associations...")

    local_cursor = local_conn.cursor()
    railway_cursor = railway_conn.cursor()

    # Clear existing data
    railway_cursor.execute("TRUNCATE TABLE user_player_associations CASCADE")
    railway_conn.commit()

    # Get user mappings
    local_cursor.execute("SELECT id, email FROM users")
    local_users = dict(local_cursor.fetchall())

    railway_cursor.execute("SELECT id, email FROM users")
    railway_users = {email: rid for rid, email in railway_cursor.fetchall()}

    # Get associations
    local_cursor.execute(
        """
        SELECT user_id, player_id, is_primary, created_at
        FROM user_player_associations
    """
    )

    migrated = 0
    for user_id, player_id, is_primary, created_at in local_cursor.fetchall():
        # Map user
        user_email = None
        for uid, email in local_users.items():
            if uid == user_id:
                user_email = email
                break

        if not user_email or user_email not in railway_users:
            continue

        # Map player
        if player_id not in player_mapping:
            continue

        railway_user_id = railway_users[user_email]
        railway_player_id = player_mapping[player_id]

        # Insert
        railway_cursor.execute(
            """
            INSERT INTO user_player_associations (user_id, player_id, is_primary, created_at)
            VALUES (%s, %s, %s, %s)
        """,
            (railway_user_id, railway_player_id, is_primary, created_at),
        )
        migrated += 1

    railway_conn.commit()
    print(f"  ✅ Completed: {migrated:,} associations migrated")
    return migrated


def main():
    """Main migration"""
    print("🚀 SIMPLE CRITICAL MIGRATION")
    print("=" * 50)

    try:
        with get_db() as local_conn:
            railway_conn = connect_to_railway()

            try:
                # Create mapping
                mapping = create_simple_mapping(local_conn, railway_conn)

                if not mapping:
                    print("❌ No player mapping available")
                    return False

                # Migrate tables
                ph_count = migrate_player_history_simple(
                    local_conn, railway_conn, mapping
                )
                upa_count = migrate_user_associations_simple(
                    local_conn, railway_conn, mapping
                )

                # Summary
                print(f"\n" + "=" * 50)
                print(f"✅ MIGRATION COMPLETED!")
                print(f"  • player_history: {ph_count:,} records")
                print(f"  • user_player_associations: {upa_count:,} records")
                print(f"  • Total: {ph_count + upa_count:,} records")

                return True

            finally:
                railway_conn.close()

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
