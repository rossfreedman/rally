#!/usr/bin/env python3
"""
Backup and Restore User Associations
===================================

This script backs up user associations before ETL and restores them after
using tenniscores_player_id matching to handle changing player IDs.
"""

import json
import os
import sys
from datetime import datetime

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db


def backup_user_associations():
    """Backup user associations with tenniscores_player_id for restoration"""
    print("📦 Backing up user associations...")

    backup_file = os.path.join(
        "data",
        "backups",
        "user_data",
        f"user_associations_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
    )

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # Get user associations with tenniscores_player_id for matching
            cursor.execute(
                """
                SELECT 
                    u.id as user_id,
                    u.email,
                    u.first_name,
                    u.last_name,
                    p.tenniscores_player_id,
                    l.league_id,
                    upa.is_primary,
                    upa.created_at
                FROM user_player_associations upa
                JOIN users u ON upa.user_id = u.id
                JOIN players p ON upa.player_id = p.id
                JOIN leagues l ON p.league_id = l.id
                ORDER BY u.id, upa.is_primary DESC
            """
            )

            associations = []
            for row in cursor.fetchall():
                associations.append(
                    {
                        "user_id": row[0],
                        "email": row[1],
                        "first_name": row[2],
                        "last_name": row[3],
                        "tenniscores_player_id": row[4],
                        "league_id": row[5],
                        "is_primary": row[6],
                        "created_at": row[7].isoformat() if row[7] else None,
                    }
                )

            # Also backup users table
            cursor.execute(
                """
                SELECT id, email, password_hash, first_name, last_name, 
                       club_automation_password, created_at, last_login, is_admin,
                       league_id, tenniscores_player_id
                FROM users ORDER BY id
            """
            )
            users = []
            for row in cursor.fetchall():
                users.append(
                    {
                        "id": row[0],
                        "email": row[1],
                        "password_hash": row[2],
                        "first_name": row[3],
                        "last_name": row[4],
                        "club_automation_password": row[5],
                        "created_at": row[6].isoformat() if row[6] else None,
                        "last_login": row[7].isoformat() if row[7] else None,
                        "is_admin": row[8],
                        "league_id": row[9],
                        "tenniscores_player_id": row[10],
                    }
                )

            backup_data = {
                "users": users,
                "associations": associations,
                "created_at": datetime.now().isoformat(),
            }

            with open(backup_file, "w") as f:
                json.dump(backup_data, f, indent=2, default=str)

            print(
                f"✅ Backed up {len(users)} users and {len(associations)} associations to {backup_file}"
            )
            return backup_file

    except Exception as e:
        print(f"❌ Error backing up user associations: {str(e)}")
        raise


def restore_user_associations(backup_file):
    """Restore user associations using tenniscores_player_id matching"""
    print(f"📥 Restoring user associations from {backup_file}...")

    try:
        with open(backup_file, "r") as f:
            backup_data = json.load(f)

        users = backup_data["users"]
        associations = backup_data["associations"]

        with get_db() as conn:
            cursor = conn.cursor()

            # Restore users first
            print("👥 Restoring users...")
            restored_users = 0
            for user in users:
                cursor.execute(
                    """
                    INSERT INTO users (
                        id, email, password_hash, first_name, last_name,
                        club_automation_password, created_at, last_login, is_admin,
                        league_id, tenniscores_player_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        email = EXCLUDED.email,
                        password_hash = EXCLUDED.password_hash,
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        club_automation_password = EXCLUDED.club_automation_password,
                        created_at = EXCLUDED.created_at,
                        last_login = EXCLUDED.last_login,
                        is_admin = EXCLUDED.is_admin,
                        league_id = EXCLUDED.league_id,
                        tenniscores_player_id = EXCLUDED.tenniscores_player_id
                """,
                    (
                        user["id"],
                        user["email"],
                        user["password_hash"],
                        user["first_name"],
                        user["last_name"],
                        user["club_automation_password"],
                        user["created_at"],
                        user["last_login"],
                        user["is_admin"],
                        user["league_id"],
                        user["tenniscores_player_id"],
                    ),
                )
                restored_users += 1

            # Fix user sequence
            cursor.execute("SELECT setval('users_id_seq', (SELECT MAX(id) FROM users))")

            # Restore associations using tenniscores_player_id matching
            print("🔗 Restoring user-player associations...")
            restored_associations = 0
            failed_associations = 0

            for assoc in associations:
                # Find the new player ID using tenniscores_player_id and league
                cursor.execute(
                    """
                    SELECT p.id
                    FROM players p
                    JOIN leagues l ON p.league_id = l.id
                    WHERE p.tenniscores_player_id = %s AND l.league_id = %s
                """,
                    (assoc["tenniscores_player_id"], assoc["league_id"]),
                )

                player_result = cursor.fetchone()
                if player_result:
                    new_player_id = player_result[0]

                    cursor.execute(
                        """
                        INSERT INTO user_player_associations (user_id, player_id, is_primary, created_at)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (user_id, player_id) DO UPDATE SET
                            is_primary = EXCLUDED.is_primary
                    """,
                        (
                            assoc["user_id"],
                            new_player_id,
                            assoc["is_primary"],
                            assoc["created_at"],
                        ),
                    )
                    restored_associations += 1
                else:
                    print(
                        f"⚠️  Could not find player {assoc['tenniscores_player_id']} in league {assoc['league_id']}"
                    )
                    failed_associations += 1

            conn.commit()

            print(f"✅ Restored {restored_users} users")
            print(f"✅ Restored {restored_associations} associations")
            if failed_associations > 0:
                print(f"⚠️  Failed to restore {failed_associations} associations")

    except Exception as e:
        print(f"❌ Error restoring user associations: {str(e)}")
        raise


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python backup_restore_users.py backup")
        print("  python backup_restore_users.py restore <backup_file>")
        return 1

    command = sys.argv[1]

    if command == "backup":
        backup_file = backup_user_associations()
        print(f"\n🎉 Backup complete! File: {backup_file}")
        print("Now you can run your ETL script safely.")
        print(f"After ETL, run: python backup_restore_users.py restore {backup_file}")

    elif command == "restore":
        if len(sys.argv) < 3:
            print("❌ Please provide backup file path")
            return 1
        backup_file = sys.argv[2]
        restore_user_associations(backup_file)
        print("\n🎉 Restore complete!")

    else:
        print("❌ Unknown command. Use 'backup' or 'restore'")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
