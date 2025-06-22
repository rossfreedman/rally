#!/usr/bin/env python3
"""
Migration: Enhance Player Uniqueness Constraint
==============================================

Replace the current unique constraint (tenniscores_player_id, league_id)
with (tenniscores_player_id, league_id, club_id, series_id) to allow
players to exist in multiple clubs/series with the same Player ID.

This fixes the ETL overwrite issue where players who moved between
clubs or series were losing their historical records.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2

from database_config import get_db


def upgrade():
    """Apply the migration"""
    print("🔄 Starting migration: Enhance Player Uniqueness Constraint")

    with get_db() as conn:
        cursor = conn.cursor()

        try:
            # Step 1: Drop the existing unique constraint
            print("📋 Step 1: Dropping existing unique_player_in_league constraint...")
            cursor.execute(
                """
                ALTER TABLE players 
                DROP CONSTRAINT IF EXISTS unique_player_in_league
            """
            )
            print("✅ Existing constraint dropped")

            # Step 2: Add the new enhanced unique constraint
            print("📋 Step 2: Adding enhanced unique constraint...")
            cursor.execute(
                """
                ALTER TABLE players 
                ADD CONSTRAINT unique_player_in_league_club_series 
                UNIQUE (tenniscores_player_id, league_id, club_id, series_id)
            """
            )
            print(
                "✅ Enhanced constraint added: (tenniscores_player_id, league_id, club_id, series_id)"
            )

            # Step 3: Create an index for performance
            print("📋 Step 3: Creating performance index...")
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_players_lookup 
                ON players (tenniscores_player_id, league_id)
            """
            )
            print("✅ Performance index created")

            conn.commit()
            print("🎉 Migration completed successfully!")
            print(
                "🔧 Players can now exist in multiple clubs/series with same Player ID"
            )

            return True

        except Exception as e:
            conn.rollback()
            print(f"❌ Migration failed: {str(e)}")
            return False

        finally:
            cursor.close()


def downgrade():
    """Rollback the migration"""
    print("🔄 Rolling back migration: Enhance Player Uniqueness Constraint")

    with get_db() as conn:
        cursor = conn.cursor()

        try:
            # Remove the new constraint
            cursor.execute(
                """
                ALTER TABLE players 
                DROP CONSTRAINT IF EXISTS unique_player_in_league_club_series
            """
            )

            # Restore the original constraint (this may fail if there are duplicates)
            cursor.execute(
                """
                ALTER TABLE players 
                ADD CONSTRAINT unique_player_in_league 
                UNIQUE (tenniscores_player_id, league_id)
            """
            )

            # Drop the performance index
            cursor.execute(
                """
                DROP INDEX IF EXISTS idx_players_lookup
            """
            )

            conn.commit()
            print("✅ Migration rolled back successfully")
            return True

        except Exception as e:
            conn.rollback()
            print(f"❌ Rollback failed: {str(e)}")
            return False

        finally:
            cursor.close()


def main():
    """Run the migration"""
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        return downgrade()
    else:
        return upgrade()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
