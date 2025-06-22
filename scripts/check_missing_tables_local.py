#!/usr/bin/env python3

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_config import get_db


def check_local_missing_tables():
    """Check what data exists locally for the missing tables"""
    print("🔍 CHECKING LOCAL DATABASE FOR MISSING TABLES")
    print("=" * 60)

    with get_db() as conn:
        cursor = conn.cursor()

        # Check player_history table
        print("\n📊 PLAYER_HISTORY TABLE:")
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

            # Check for NULL player_id values
            cursor.execute(
                "SELECT COUNT(*) FROM player_history WHERE player_id IS NULL"
            )
            null_count = cursor.fetchone()[0]
            print(f"  Records with NULL player_id: {null_count:,}")

            # Check for linked records
            cursor.execute(
                "SELECT COUNT(*) FROM player_history WHERE player_id IS NOT NULL"
            )
            linked_count = cursor.fetchone()[0]
            print(f"  Records with valid player_id: {linked_count:,}")

        # Check user_player_associations table
        print("\n👥 USER_PLAYER_ASSOCIATIONS TABLE:")
        cursor.execute("SELECT COUNT(*) FROM user_player_associations")
        upa_count = cursor.fetchone()[0]
        print(f"  Total records: {upa_count:,}")

        if upa_count > 0:
            # Sample records
            cursor.execute(
                "SELECT * FROM user_player_associations ORDER BY created_at DESC LIMIT 5"
            )
            print(f"  Sample records:")
            for row in cursor.fetchall():
                print(
                    f"    User ID: {row[0]}, Player ID: {row[1]}, Primary: {row[2]}, Created: {row[3]}"
                )

            # Check what users are linked
            cursor.execute(
                """
                SELECT u.email, u.first_name, u.last_name, upa.is_primary
                FROM user_player_associations upa
                JOIN users u ON upa.user_id = u.id
                ORDER BY u.email
            """
            )
            print(f"  Users with player associations:")
            for row in cursor.fetchall():
                primary_text = " (PRIMARY)" if row[3] else ""
                print(f"    {row[1]} {row[2]} ({row[0]}){primary_text}")


if __name__ == "__main__":
    check_local_missing_tables()
