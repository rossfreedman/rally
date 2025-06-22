#!/usr/bin/env python3
"""
Validate user_player_associations Migration
==========================================
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db


def validate_migration():
    """Check that migration completed successfully"""
    print("🔍 Validating user_player_associations migration...")

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # Check new schema exists
            cursor.execute(
                """
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'user_player_associations'
                ORDER BY ordinal_position
            """
            )

            columns = cursor.fetchall()
            expected_columns = {
                "user_id": "integer",
                "tenniscores_player_id": "character varying",
                "league_id": "integer",
                "is_primary": "boolean",
                "created_at": "timestamp with time zone",
            }

            actual_columns = {col[0]: col[1] for col in columns}

            print("📊 Current table schema:")
            for col_name, col_type in actual_columns.items():
                status = "✅" if col_name in expected_columns else "❌"
                print(f"   {status} {col_name}: {col_type}")

            # Check for old column
            if "player_id" in actual_columns:
                print("   ❌ OLD COLUMN STILL EXISTS: player_id")
                return False

            # Check data
            cursor.execute("SELECT COUNT(*) FROM user_player_associations")
            total_associations = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT COUNT(*) FROM user_player_associations upa
                LEFT JOIN players p ON p.tenniscores_player_id = upa.tenniscores_player_id 
                                   AND p.league_id = upa.league_id
                WHERE p.id IS NULL
            """
            )
            orphaned_associations = cursor.fetchone()[0]

            print(f"📈 Association Data:")
            print(f"   Total associations: {total_associations:,}")
            print(f"   Orphaned associations: {orphaned_associations:,}")

            if orphaned_associations > 0:
                print("   ❌ Found orphaned associations!")
                return False

            print("✅ Migration validation PASSED!")
            return True

    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False


if __name__ == "__main__":
    success = validate_migration()
    sys.exit(0 if success else 1)
