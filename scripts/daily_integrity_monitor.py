#!/usr/bin/env python3
"""
Daily Database Integrity Monitor

This script should be run daily via cron to monitor data integrity
and alert on any issues. It's designed to be lightweight and send
alerts only when problems are detected.

Usage:
    python scripts/daily_integrity_monitor.py

Cron setup (run daily at 8 AM):
    0 8 * * * cd /path/to/rally && python scripts/daily_integrity_monitor.py >> logs/integrity_monitor.log 2>&1
"""

import os
import sys
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one


class DailyIntegrityMonitor:
    """Lightweight daily integrity monitoring"""

    def __init__(self):
        self.alerts = []
        self.warnings = []
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def add_alert(self, level, category, message, count=None):
        """Add an alert or warning"""
        alert = {
            "level": level,
            "category": category,
            "message": message,
            "count": count,
            "timestamp": self.timestamp,
        }

        if level == "ALERT":
            self.alerts.append(alert)
        else:
            self.warnings.append(alert)

    def check_availability_integrity(self):
        """Check player_availability table integrity"""

        # Critical check: NULL player_id (should be impossible now)
        null_player_ids = execute_query_one(
            """
            SELECT COUNT(*) as count 
            FROM player_availability 
            WHERE player_id IS NULL
        """
        )

        if null_player_ids["count"] > 0:
            self.add_alert(
                "ALERT",
                "AVAILABILITY",
                f"NULL player_id values detected - data integrity compromised!",
                null_player_ids["count"],
            )

        # Critical check: Orphaned player references
        orphaned_players = execute_query_one(
            """
            SELECT COUNT(*) as count
            FROM player_availability pa
            LEFT JOIN players p ON pa.player_id = p.id
            WHERE pa.player_id IS NOT NULL AND p.id IS NULL
        """
        )

        if orphaned_players["count"] > 0:
            self.add_alert(
                "ALERT",
                "AVAILABILITY",
                f"Orphaned player references found - players were deleted but availability remains",
                orphaned_players["count"],
            )

        # Critical check: Orphaned series references
        orphaned_series = execute_query_one(
            """
            SELECT COUNT(*) as count
            FROM player_availability pa
            LEFT JOIN series s ON pa.series_id = s.id
            WHERE s.id IS NULL
        """
        )

        if orphaned_series["count"] > 0:
            self.add_alert(
                "ALERT",
                "AVAILABILITY",
                f"Orphaned series references found - series were deleted but availability remains",
                orphaned_series["count"],
            )

        # Warning check: Invalid availability status
        invalid_status = execute_query_one(
            """
            SELECT COUNT(*) as count
            FROM player_availability
            WHERE availability_status NOT IN (1, 2, 3)
        """
        )

        if invalid_status["count"] > 0:
            self.add_alert(
                "WARNING",
                "AVAILABILITY",
                f"Invalid availability status values found",
                invalid_status["count"],
            )

        # Info check: Recent activity (last 7 days)
        recent_activity = execute_query_one(
            """
            SELECT COUNT(*) as count
            FROM player_availability
            WHERE updated_at >= NOW() - INTERVAL '7 days'
        """
        )

        return {
            "total_records": execute_query_one(
                "SELECT COUNT(*) as count FROM player_availability"
            )["count"],
            "recent_activity": recent_activity["count"],
        }

    def check_player_integrity(self):
        """Check players table integrity"""

        # Warning check: Players without series
        players_no_series = execute_query_one(
            """
            SELECT COUNT(*) as count
            FROM players p
            LEFT JOIN series s ON p.series_id = s.id
            WHERE s.id IS NULL AND p.is_active = true
        """
        )

        if players_no_series["count"] > 0:
            self.add_alert(
                "WARNING",
                "PLAYERS",
                f"Active players reference non-existent series",
                players_no_series["count"],
            )

        # Warning check: Duplicate player names in same series
        duplicate_names = execute_query(
            """
            SELECT series_id, CONCAT(first_name, ' ', last_name) as full_name, COUNT(*) as count
            FROM players
            WHERE is_active = true
            GROUP BY series_id, CONCAT(first_name, ' ', last_name)
            HAVING COUNT(*) > 1
            ORDER BY count DESC
        """
        )

        if duplicate_names:
            self.add_alert(
                "WARNING",
                "PLAYERS",
                f"Duplicate player names found in same series",
                len(duplicate_names),
            )

        return {
            "total_players": execute_query_one(
                "SELECT COUNT(*) as count FROM players WHERE is_active = true"
            )["count"],
            "duplicate_names": len(duplicate_names) if duplicate_names else 0,
        }

    def check_constraint_health(self):
        """Verify database constraints are still active"""

        # Check critical constraints exist
        critical_constraints = [
            "fk_player_availability_player_id",
            "valid_availability_status",
        ]

        existing_constraints = execute_query(
            """
            SELECT conname as constraint_name
            FROM pg_constraint 
            WHERE conrelid = 'player_availability'::regclass
            AND conname = ANY(%s)
        """,
            (critical_constraints,),
        )

        existing_names = [c["constraint_name"] for c in existing_constraints]

        for constraint in critical_constraints:
            if constraint not in existing_names:
                self.add_alert(
                    "ALERT", "CONSTRAINTS", f"Critical constraint missing: {constraint}"
                )

        # Check critical indexes exist
        critical_indexes = [
            "idx_player_availability_player_id",
            "idx_unique_player_availability",
        ]

        existing_indexes = execute_query(
            """
            SELECT indexname
            FROM pg_indexes 
            WHERE tablename = 'player_availability'
            AND indexname = ANY(%s)
        """,
            (critical_indexes,),
        )

        existing_index_names = [i["indexname"] for i in existing_indexes]

        for index in critical_indexes:
            if index not in existing_index_names:
                self.add_alert(
                    "WARNING", "INDEXES", f"Performance index missing: {index}"
                )

    def run_daily_check(self):
        """Run the daily integrity check"""

        print(f"🔍 DAILY INTEGRITY MONITOR - {self.timestamp}")
        print("=" * 60)

        try:
            # Run all checks
            availability_stats = self.check_availability_integrity()
            player_stats = self.check_player_integrity()
            self.check_constraint_health()

            # Print summary
            print(f"📊 DATABASE SUMMARY:")
            print(
                f"   Player availability records: {availability_stats['total_records']}"
            )
            print(
                f"   Recent availability updates (7d): {availability_stats['recent_activity']}"
            )
            print(f"   Active players: {player_stats['total_players']}")
            print(f"   Duplicate names: {player_stats['duplicate_names']}")

            # Report alerts
            if self.alerts:
                print(f"\n🚨 CRITICAL ALERTS ({len(self.alerts)}):")
                for alert in self.alerts:
                    count_str = f" ({alert['count']} records)" if alert["count"] else ""
                    print(f"   ❌ [{alert['category']}] {alert['message']}{count_str}")

            if self.warnings:
                print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
                for warning in self.warnings:
                    count_str = (
                        f" ({warning['count']} records)" if warning["count"] else ""
                    )
                    print(
                        f"   ⚠️  [{warning['category']}] {warning['message']}{count_str}"
                    )

            if not self.alerts and not self.warnings:
                print(f"\n✅ ALL CHECKS PASSED - Database integrity is healthy!")

            # Log to file
            self.log_results()

            # Return status for cron job
            return len(self.alerts) == 0

        except Exception as e:
            print(f"❌ ERROR during integrity check: {e}")
            self.add_alert("ALERT", "SYSTEM", f"Integrity monitor failed: {e}")
            return False

    def log_results(self):
        """Log results to file for history tracking"""

        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        log_file = os.path.join(log_dir, "integrity_monitor.log")

        with open(log_file, "a") as f:
            f.write(f"\n{self.timestamp} - Daily Integrity Check\n")
            f.write(f"Alerts: {len(self.alerts)}, Warnings: {len(self.warnings)}\n")

            if self.alerts:
                f.write("ALERTS:\n")
                for alert in self.alerts:
                    f.write(f"  - {alert['category']}: {alert['message']}\n")

            if self.warnings:
                f.write("WARNINGS:\n")
                for warning in self.warnings:
                    f.write(f"  - {warning['category']}: {warning['message']}\n")

            if not self.alerts and not self.warnings:
                f.write("Status: HEALTHY\n")

    def send_alerts(self):
        """Send alerts (email, Slack, etc.) - implement as needed"""

        if not self.alerts:
            return

        # Example: Print alerts for now
        # In production, implement email/Slack notifications
        print(f"\n📧 WOULD SEND ALERTS:")
        for alert in self.alerts:
            print(f"   To: admin@rallytennaqua.com")
            print(f"   Subject: [RALLY DB] {alert['category']} Alert")
            print(f"   Message: {alert['message']}")


def main():
    """Main monitoring function"""

    monitor = DailyIntegrityMonitor()
    success = monitor.run_daily_check()

    # Send alerts if any critical issues
    if monitor.alerts:
        monitor.send_alerts()

    # Exit with appropriate status for cron
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
