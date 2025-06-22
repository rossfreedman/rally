#!/usr/bin/env python3
"""
Verify the status of tables on Railway to see if migration completed
"""

import os
import sys
from urllib.parse import urlparse

import psycopg2

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


def verify_tables():
    """Check the status of critical tables on Railway"""
    print("🔍 VERIFYING RAILWAY DATABASE TABLES")
    print("=" * 60)

    railway_conn = connect_to_railway()

    try:
        cursor = railway_conn.cursor()

        # Check player_history table
        print("\n📊 PLAYER_HISTORY TABLE:")
        try:
            cursor.execute("SELECT COUNT(*) FROM player_history")
            ph_count = cursor.fetchone()[0]
            print(f"  Total records: {ph_count:,}")

            if ph_count > 0:
                # Sample records
                cursor.execute(
                    "SELECT * FROM player_history ORDER BY created_at DESC LIMIT 3"
                )
                print(f"  Sample records:")
                for row in cursor.fetchall():
                    print(
                        f"    ID: {row[0]}, Player ID: {row[1]}, League ID: {row[2]}, Series: {row[3]}, Date: {row[4]}, PTI: {row[5]}"
                    )

                # Check for valid player_id links
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM player_history ph
                    JOIN players p ON ph.player_id = p.id
                """
                )
                valid_links = cursor.fetchone()[0]
                print(f"  Records with valid player links: {valid_links:,}")

        except Exception as e:
            print(f"  ❌ Error accessing player_history: {e}")

        # Check user_player_associations table
        print("\n👥 USER_PLAYER_ASSOCIATIONS TABLE:")
        try:
            cursor.execute("SELECT COUNT(*) FROM user_player_associations")
            upa_count = cursor.fetchone()[0]
            print(f"  Total records: {upa_count:,}")

            if upa_count > 0:
                # Sample records with user info
                cursor.execute(
                    """
                    SELECT u.email, u.first_name, u.last_name, upa.is_primary, p.first_name, p.last_name
                    FROM user_player_associations upa
                    JOIN users u ON upa.user_id = u.id
                    JOIN players p ON upa.player_id = p.id
                    ORDER BY upa.created_at DESC
                """
                )
                print(f"  User-player associations:")
                for row in cursor.fetchall():
                    primary_text = " (PRIMARY)" if row[3] else ""
                    print(
                        f"    {row[1]} {row[2]} ({row[0]}) -> {row[4]} {row[5]}{primary_text}"
                    )

        except Exception as e:
            print(f"  ❌ Error accessing user_player_associations: {e}")

        # Check players table for context
        print("\n👤 PLAYERS TABLE (for context):")
        try:
            cursor.execute("SELECT COUNT(*) FROM players")
            players_count = cursor.fetchone()[0]
            print(f"  Total players: {players_count:,}")

            cursor.execute(
                "SELECT COUNT(*) FROM players WHERE tenniscores_player_id IS NOT NULL"
            )
            tc_players_count = cursor.fetchone()[0]
            print(f"  Players with TC IDs: {tc_players_count:,}")

        except Exception as e:
            print(f"  ❌ Error accessing players: {e}")

        # Summary
        print(f"\n" + "=" * 60)
        print(f"📋 SUMMARY:")
        print(f"  • player_history: {ph_count:,} records")
        print(f"  • user_player_associations: {upa_count:,} records")
        print(f"  • players (with TC IDs): {tc_players_count:,} records")

        if ph_count > 100000 and upa_count > 0:
            print(f"✅ CRITICAL GAPS RESOLVED!")
            print(f"   Both missing tables now have data")
        else:
            print(f"⚠️  Still missing data in critical tables")

    finally:
        railway_conn.close()


if __name__ == "__main__":
    verify_tables()
