#!/usr/bin/env python3
"""
Data Integrity Monitoring Script for Rally Platform Tennis

This script monitors data integrity issues and can be run regularly
to catch problems early before they impact users.
"""

import os
import sys
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one


class DataIntegrityMonitor:
    """Monitor data integrity across Rally database tables"""

    def __init__(self):
        self.issues = []
        self.warnings = []

    def add_issue(self, table, issue_type, description, count=None, examples=None):
        """Add a data integrity issue"""
        self.issues.append(
            {
                "table": table,
                "type": issue_type,
                "description": description,
                "count": count,
                "examples": examples or [],
                "severity": "ERROR",
            }
        )

    def add_warning(self, table, issue_type, description, count=None, examples=None):
        """Add a data integrity warning"""
        self.warnings.append(
            {
                "table": table,
                "type": issue_type,
                "description": description,
                "count": count,
                "examples": examples or [],
                "severity": "WARNING",
            }
        )

    def check_availability_integrity(self):
        """Check player_availability table integrity"""
        print("🔍 Checking player_availability table integrity...")

        # Check 1: NULL player_id values
        null_player_ids = execute_query(
            """
            SELECT COUNT(*) as count,
                   array_agg(DISTINCT player_name ORDER BY player_name) as player_names
            FROM player_availability 
            WHERE player_id IS NULL
        """
        )

        if null_player_ids[0]["count"] > 0:
            self.add_issue(
                "player_availability",
                "NULL_PLAYER_ID",
                "Availability records with NULL player_id values",
                count=null_player_ids[0]["count"],
                examples=null_player_ids[0]["player_names"][:5],  # First 5 examples
            )

        # Check 2: Orphaned availability records (player_id points to non-existent player)
        orphaned_records = execute_query(
            """
            SELECT pa.id, pa.player_name, pa.player_id, pa.match_date, pa.series_id
            FROM player_availability pa
            LEFT JOIN players p ON pa.player_id = p.id
            WHERE pa.player_id IS NOT NULL 
            AND p.id IS NULL
            LIMIT 10
        """
        )

        if orphaned_records:
            self.add_issue(
                "player_availability",
                "ORPHANED_RECORDS",
                "Availability records with player_id pointing to non-existent players",
                count=len(orphaned_records),
                examples=[
                    f"ID:{r['id']} player_id:{r['player_id']} name:{r['player_name']}"
                    for r in orphaned_records[:5]
                ],
            )

        # Check 3: Name/ID mismatches
        name_id_mismatches = execute_query(
            """
            SELECT pa.id, pa.player_name, pa.player_id,
                   CONCAT(p.first_name, ' ', p.last_name) as actual_name
            FROM player_availability pa
            JOIN players p ON pa.player_id = p.id
            WHERE pa.player_name != CONCAT(p.first_name, ' ', p.last_name)
            LIMIT 10
        """
        )

        if name_id_mismatches:
            self.add_warning(
                "player_availability",
                "NAME_ID_MISMATCH",
                "Player name in availability does not match player_id reference",
                count=len(name_id_mismatches),
                examples=[
                    f"ID:{r['id']} stored:'{r['player_name']}' actual:'{r['actual_name']}'"
                    for r in name_id_mismatches[:5]
                ],
            )

        # Check 4: Duplicate availability records
        duplicates = execute_query(
            """
            SELECT player_id, match_date, series_id, COUNT(*) as duplicate_count
            FROM player_availability
            WHERE player_id IS NOT NULL
            GROUP BY player_id, match_date, series_id
            HAVING COUNT(*) > 1
            LIMIT 10
        """
        )

        if duplicates:
            self.add_issue(
                "player_availability",
                "DUPLICATE_RECORDS",
                "Multiple availability records for same player/date/series",
                count=len(duplicates),
                examples=[
                    f"player_id:{r['player_id']} date:{r['match_date']} series:{r['series_id']} ({r['duplicate_count']} records)"
                    for r in duplicates[:5]
                ],
            )

        # Check 5: Invalid availability status values
        invalid_status = execute_query(
            """
            SELECT COUNT(*) as count,
                   array_agg(DISTINCT availability_status ORDER BY availability_status) as invalid_values
            FROM player_availability 
            WHERE availability_status NOT IN (1, 2, 3)
        """
        )

        if invalid_status[0]["count"] > 0:
            self.add_issue(
                "player_availability",
                "INVALID_STATUS",
                "Availability records with invalid status values (not 1, 2, or 3)",
                count=invalid_status[0]["count"],
                examples=invalid_status[0]["invalid_values"],
            )

        # Check 6: Records with series_id pointing to non-existent series
        orphaned_series = execute_query(
            """
            SELECT pa.id, pa.player_name, pa.series_id, pa.match_date
            FROM player_availability pa
            LEFT JOIN series s ON pa.series_id = s.id
            WHERE s.id IS NULL
            LIMIT 10
        """
        )

        if orphaned_series:
            self.add_issue(
                "player_availability",
                "ORPHANED_SERIES",
                "Availability records with series_id pointing to non-existent series",
                count=len(orphaned_series),
                examples=[
                    f"ID:{r['id']} name:{r['player_name']} series_id:{r['series_id']}"
                    for r in orphaned_series[:5]
                ],
            )

    def check_players_integrity(self):
        """Check players table integrity"""
        print("🔍 Checking players table integrity...")

        # Check 1: Players without series
        players_no_series = execute_query(
            """
            SELECT p.id, p.first_name, p.last_name, p.series_id
            FROM players p
            LEFT JOIN series s ON p.series_id = s.id
            WHERE s.id IS NULL
            LIMIT 10
        """
        )

        if players_no_series:
            self.add_issue(
                "players",
                "ORPHANED_SERIES",
                "Players with series_id pointing to non-existent series",
                count=len(players_no_series),
                examples=[
                    f"ID:{r['id']} {r['first_name']} {r['last_name']} series_id:{r['series_id']}"
                    for r in players_no_series[:5]
                ],
            )

        # Check 2: Duplicate players (same name in same series)
        duplicate_players = execute_query(
            """
            SELECT first_name, last_name, series_id, COUNT(*) as duplicate_count
            FROM players
            GROUP BY first_name, last_name, series_id
            HAVING COUNT(*) > 1
            LIMIT 10
        """
        )

        if duplicate_players:
            self.add_warning(
                "players",
                "DUPLICATE_PLAYERS",
                "Multiple player records with same name in same series",
                count=len(duplicate_players),
                examples=[
                    f"{r['first_name']} {r['last_name']} series:{r['series_id']} ({r['duplicate_count']} records)"
                    for r in duplicate_players[:5]
                ],
            )

    def check_recent_activity(self):
        """Check for suspicious recent activity"""
        print("🔍 Checking recent activity patterns...")

        # Check 1: High volume of availability changes (possible spam/attacks)
        recent_changes = execute_query(
            """
            SELECT DATE(updated_at) as change_date, COUNT(*) as change_count
            FROM player_availability
            WHERE updated_at >= NOW() - INTERVAL '7 days'
            GROUP BY DATE(updated_at)
            ORDER BY change_count DESC
            LIMIT 5
        """
        )

        for change in recent_changes:
            if change["change_count"] > 100:  # Threshold for suspicious activity
                self.add_warning(
                    "player_availability",
                    "HIGH_VOLUME_CHANGES",
                    f'Unusually high number of availability changes on {change["change_date"]}',
                    count=change["change_count"],
                )

        # Check 2: Failed availability updates (would be logged if we had error tracking)
        # This could be added if we implement error logging

    def run_all_checks(self):
        """Run all integrity checks"""
        print("🚀 Starting Rally Data Integrity Check")
        print("=" * 60)

        try:
            self.check_availability_integrity()
            self.check_players_integrity()
            self.check_recent_activity()

            return self.generate_report()

        except Exception as e:
            print(f"❌ Error during integrity check: {e}")
            import traceback

            print(traceback.format_exc())
            return False

    def generate_report(self):
        """Generate and display integrity report"""
        print("\n" + "=" * 60)
        print("📊 DATA INTEGRITY REPORT")
        print("=" * 60)

        if not self.issues and not self.warnings:
            print("✅ ALL CHECKS PASSED - No data integrity issues found!")
            return True

        # Display issues
        if self.issues:
            print(f"\n🚨 CRITICAL ISSUES FOUND: {len(self.issues)}")
            print("-" * 40)
            for i, issue in enumerate(self.issues, 1):
                print(f"{i}. {issue['table'].upper()}: {issue['type']}")
                print(f"   Description: {issue['description']}")
                if issue["count"]:
                    print(f"   Count: {issue['count']}")
                if issue["examples"]:
                    print(
                        f"   Examples: {issue['examples'][:3]}"
                    )  # Show up to 3 examples
                print()

        # Display warnings
        if self.warnings:
            print(f"\n⚠️  WARNINGS: {len(self.warnings)}")
            print("-" * 40)
            for i, warning in enumerate(self.warnings, 1):
                print(f"{i}. {warning['table'].upper()}: {warning['type']}")
                print(f"   Description: {warning['description']}")
                if warning["count"]:
                    print(f"   Count: {warning['count']}")
                if warning["examples"]:
                    print(f"   Examples: {warning['examples'][:3]}")
                print()

        # Recommendations
        print("💡 RECOMMENDATIONS:")
        print("-" * 40)

        if any(issue["type"] == "NULL_PLAYER_ID" for issue in self.issues):
            print(
                "• Run scripts/fix_availability_player_ids_COMPLETED.py to fix NULL player_id values"
            )

        if any(issue["type"] == "ORPHANED_RECORDS" for issue in self.issues):
            print(
                "• Clean up orphaned availability records referencing non-existent players"
            )

        if any(issue["type"] == "DUPLICATE_RECORDS" for issue in self.issues):
            print("• Remove duplicate availability records to prevent data conflicts")

        if self.issues:
            print(
                "• Run migrations/enforce_player_id_integrity.sql to add database constraints"
            )
            print(
                "• Consider implementing automated data validation in the application"
            )

        print("\n" + "=" * 60)

        # Return False if there are critical issues
        return len(self.issues) == 0


def main():
    """Main entry point"""
    monitor = DataIntegrityMonitor()
    success = monitor.run_all_checks()

    # Exit with appropriate code for automation
    if success:
        print("✅ Data integrity check completed successfully")
        sys.exit(0)
    else:
        print("❌ Data integrity issues found - manual intervention required")
        sys.exit(1)


if __name__ == "__main__":
    main()
