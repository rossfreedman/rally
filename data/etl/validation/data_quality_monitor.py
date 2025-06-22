#!/usr/bin/env python3
"""
Data Quality Monitoring Dashboard
=================================

Continuous monitoring system for data quality metrics and health indicators.
Generates reports, alerts, and trend analysis for the Rally database.

Can be run:
- Daily via cron for ongoing monitoring
- After ETL imports for quality assurance
- On-demand for troubleshooting
"""

import json
import os
import sys
import traceback
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../.."))

from database_utils import execute_query, execute_query_one


class DataQualityMonitor:
    def __init__(self):
        self.metrics = {}
        self.alerts = []
        self.trends = []
        self.start_time = datetime.now()

    def calculate_basic_metrics(self):
        """Calculate basic data health metrics"""
        print("📊 CALCULATING BASIC METRICS")
        print("=" * 40)

        # Core table counts
        tables = [
            "leagues",
            "clubs",
            "series",
            "teams",
            "players",
            "match_scores",
            "series_stats",
            "schedule",
        ]

        for table in tables:
            try:
                count_result = execute_query_one(
                    f"SELECT COUNT(*) as count FROM {table}"
                )
                count = count_result["count"] if count_result else 0
                self.metrics[f"{table}_count"] = count
                print(f"✅ {table}: {count:,} records")

            except Exception as e:
                self.metrics[f"{table}_count"] = 0
                self.add_alert("ERROR", f"Cannot access {table} table", str(e))
                print(f"❌ {table}: Error - {str(e)}")

    def calculate_data_freshness(self):
        """Calculate data freshness metrics"""
        print("\n🕐 ANALYZING DATA FRESHNESS")
        print("=" * 40)

        try:
            # Latest match date
            latest_match = execute_query_one(
                """
                SELECT MAX(match_date) as latest_date,
                       COUNT(CASE WHEN match_date >= CURRENT_DATE - INTERVAL '7 days' THEN 1 END) as recent_matches
                FROM match_scores
            """
            )

            if latest_match and latest_match["latest_date"]:
                latest_date = latest_match["latest_date"]
                days_since = (datetime.now().date() - latest_date).days
                recent_count = latest_match["recent_matches"]

                self.metrics["latest_match_days_ago"] = days_since
                self.metrics["recent_matches_7d"] = recent_count

                print(f"✅ Latest match: {latest_date} ({days_since} days ago)")
                print(f"✅ Recent matches (7d): {recent_count}")

                if days_since > 14:
                    self.add_alert(
                        "WARNING",
                        "Stale match data",
                        f"Latest match is {days_since} days old",
                    )
                if recent_count < 10:
                    self.add_alert(
                        "WARNING",
                        "Low recent activity",
                        f"Only {recent_count} matches in past 7 days",
                    )

            else:
                self.add_alert("ERROR", "No match data", "No matches found in database")

        except Exception as e:
            self.add_alert("ERROR", "Data freshness check failed", str(e))

    def calculate_completeness_metrics(self):
        """Calculate data completeness and quality metrics"""
        print("\n📋 ANALYZING DATA COMPLETENESS")
        print("=" * 40)

        # Player data completeness
        try:
            player_completeness = execute_query_one(
                """
                SELECT 
                    COUNT(*) as total_players,
                    COUNT(CASE WHEN first_name IS NOT NULL AND first_name != '' THEN 1 END) as has_first_name,
                    COUNT(CASE WHEN last_name IS NOT NULL AND last_name != '' THEN 1 END) as has_last_name,
                    COUNT(CASE WHEN club_id IS NOT NULL THEN 1 END) as has_club,
                    COUNT(CASE WHEN tenniscores_player_id IS NOT NULL THEN 1 END) as has_player_id
                FROM players
            """
            )

            if player_completeness:
                total = player_completeness["total_players"]
                name_rate = (
                    (player_completeness["has_first_name"] / total * 100)
                    if total > 0
                    else 0
                )
                club_rate = (
                    (player_completeness["has_club"] / total * 100) if total > 0 else 0
                )
                id_rate = (
                    (player_completeness["has_player_id"] / total * 100)
                    if total > 0
                    else 0
                )

                self.metrics["player_name_completeness"] = round(name_rate, 1)
                self.metrics["player_club_completeness"] = round(club_rate, 1)
                self.metrics["player_id_completeness"] = round(id_rate, 1)

                print(f"✅ Player names: {name_rate:.1f}% complete")
                print(f"✅ Player clubs: {club_rate:.1f}% complete")
                print(f"✅ Player IDs: {id_rate:.1f}% complete")

                if name_rate < 90:
                    self.add_alert(
                        "WARNING",
                        "Poor player name data",
                        f"Only {name_rate:.1f}% have names",
                    )
                if id_rate < 80:
                    self.add_alert(
                        "WARNING",
                        "Poor player ID linkage",
                        f"Only {id_rate:.1f}% have Tennis ID",
                    )

        except Exception as e:
            self.add_alert("ERROR", "Player completeness check failed", str(e))

        # Match data quality
        try:
            match_quality = execute_query_one(
                """
                SELECT 
                    COUNT(*) as total_matches,
                    COUNT(CASE WHEN winner IS NOT NULL AND winner != '' THEN 1 END) as has_winner,
                    COUNT(CASE WHEN scores IS NOT NULL AND scores != '' THEN 1 END) as has_scores,
                    COUNT(CASE WHEN home_team IS NOT NULL AND away_team IS NOT NULL THEN 1 END) as has_teams
                FROM match_scores
            """
            )

            if match_quality:
                total = match_quality["total_matches"]
                winner_rate = (
                    (match_quality["has_winner"] / total * 100) if total > 0 else 0
                )
                score_rate = (
                    (match_quality["has_scores"] / total * 100) if total > 0 else 0
                )
                team_rate = (
                    (match_quality["has_teams"] / total * 100) if total > 0 else 0
                )

                self.metrics["match_winner_completeness"] = round(winner_rate, 1)
                self.metrics["match_score_completeness"] = round(score_rate, 1)
                self.metrics["match_team_completeness"] = round(team_rate, 1)

                print(f"✅ Match winners: {winner_rate:.1f}% complete")
                print(f"✅ Match scores: {score_rate:.1f}% complete")
                print(f"✅ Match teams: {team_rate:.1f}% complete")

                if winner_rate < 95:
                    self.add_alert(
                        "WARNING",
                        "Missing match winners",
                        f"Only {winner_rate:.1f}% have winners",
                    )
                if team_rate < 99:
                    self.add_alert(
                        "ERROR",
                        "Missing team data",
                        f"Only {team_rate:.1f}% have complete team info",
                    )

        except Exception as e:
            self.add_alert("ERROR", "Match quality check failed", str(e))

    def calculate_consistency_metrics(self):
        """Calculate data consistency and integrity metrics"""
        print("\n🔗 ANALYZING DATA CONSISTENCY")
        print("=" * 40)

        # Series stats vs match data consistency
        try:
            stats_consistency = execute_query_one(
                """
                SELECT 
                    COUNT(DISTINCT s.team) as teams_in_stats,
                    COUNT(DISTINCT all_teams.team) as teams_in_matches
                FROM series_stats s
                FULL OUTER JOIN (
                    SELECT home_team as team FROM match_scores WHERE home_team IS NOT NULL
                    UNION
                    SELECT away_team as team FROM match_scores WHERE away_team IS NOT NULL
                ) all_teams ON s.team = all_teams.team
            """
            )

            if stats_consistency:
                stats_teams = stats_consistency["teams_in_stats"] or 0
                match_teams = stats_consistency["teams_in_matches"] or 0
                coverage = (stats_teams / match_teams * 100) if match_teams > 0 else 0

                self.metrics["series_stats_coverage"] = round(coverage, 1)
                print(
                    f"✅ Series stats coverage: {coverage:.1f}% ({stats_teams}/{match_teams} teams)"
                )

                if coverage < 90:
                    self.add_alert(
                        "ERROR",
                        "Poor series stats coverage",
                        f"Only {coverage:.1f}% teams have statistics",
                    )
                elif coverage < 95:
                    self.add_alert(
                        "WARNING",
                        "Incomplete series stats",
                        f"{coverage:.1f}% coverage",
                    )

        except Exception as e:
            self.add_alert("ERROR", "Consistency check failed", str(e))

        # Foreign key integrity
        try:
            integrity_check = execute_query_one(
                """
                SELECT 
                    (SELECT COUNT(*) FROM players p LEFT JOIN leagues l ON p.league_id = l.id WHERE l.id IS NULL) as orphaned_players,
                    (SELECT COUNT(*) FROM series_stats s LEFT JOIN leagues l ON s.league_id = l.id WHERE l.id IS NULL) as orphaned_stats,
                    (SELECT COUNT(*) FROM match_scores m LEFT JOIN leagues l ON m.league_id = l.id WHERE l.id IS NULL) as orphaned_matches
            """
            )

            if integrity_check:
                orphaned_players = integrity_check["orphaned_players"]
                orphaned_stats = integrity_check["orphaned_stats"]
                orphaned_matches = integrity_check["orphaned_matches"]

                self.metrics["orphaned_players"] = orphaned_players
                self.metrics["orphaned_stats"] = orphaned_stats
                self.metrics["orphaned_matches"] = orphaned_matches

                print(f"✅ Orphaned players: {orphaned_players}")
                print(f"✅ Orphaned stats: {orphaned_stats}")
                print(f"✅ Orphaned matches: {orphaned_matches}")

                if orphaned_players > 0:
                    self.add_alert(
                        "WARNING",
                        "Orphaned player records",
                        f"{orphaned_players} players without valid league",
                    )
                if orphaned_stats > 0:
                    self.add_alert(
                        "ERROR",
                        "Orphaned series stats",
                        f"{orphaned_stats} stats without valid league",
                    )
                if orphaned_matches > 0:
                    self.add_alert(
                        "ERROR",
                        "Orphaned matches",
                        f"{orphaned_matches} matches without valid league",
                    )

        except Exception as e:
            self.add_alert("ERROR", "Integrity check failed", str(e))

    def calculate_league_specific_metrics(self):
        """Calculate league-specific health metrics"""
        print("\n🏆 ANALYZING LEAGUE-SPECIFIC METRICS")
        print("=" * 40)

        # Major league health check
        major_leagues = ["CNSWPL", "APTA_CHICAGO", "NSTF"]

        for league_id in major_leagues:
            try:
                league_health = execute_query_one(
                    """
                    SELECT 
                        l.league_id,
                        (SELECT COUNT(*) FROM players p WHERE p.league_id = l.id) as player_count,
                        (SELECT COUNT(*) FROM series_stats s WHERE s.league_id = l.id) as team_count,
                        (SELECT COUNT(*) FROM match_scores m WHERE m.league_id = l.id) as match_count,
                        (SELECT MAX(m.match_date) FROM match_scores m WHERE m.league_id = l.id) as latest_match
                    FROM leagues l
                    WHERE l.league_id = %s
                """,
                    [league_id],
                )

                if league_health:
                    players = league_health["player_count"]
                    teams = league_health["team_count"]
                    matches = league_health["match_count"]
                    latest = league_health["latest_match"]

                    self.metrics[f"{league_id}_players"] = players
                    self.metrics[f"{league_id}_teams"] = teams
                    self.metrics[f"{league_id}_matches"] = matches

                    print(
                        f"✅ {league_id}: {players:,} players, {teams} teams, {matches:,} matches"
                    )

                    # League-specific thresholds
                    min_thresholds = {
                        "CNSWPL": {"players": 200, "teams": 50, "matches": 500},
                        "APTA_CHICAGO": {"players": 150, "teams": 30, "matches": 300},
                        "NSTF": {"players": 100, "teams": 20, "matches": 200},
                    }

                    thresholds = min_thresholds.get(
                        league_id, {"players": 50, "teams": 10, "matches": 100}
                    )

                    if players < thresholds["players"]:
                        self.add_alert(
                            "WARNING",
                            f"{league_id} low player count",
                            f"Only {players} players (need {thresholds['players']})",
                        )
                    if teams < thresholds["teams"]:
                        self.add_alert(
                            "WARNING",
                            f"{league_id} low team count",
                            f"Only {teams} teams (need {thresholds['teams']})",
                        )
                    if matches < thresholds["matches"]:
                        self.add_alert(
                            "WARNING",
                            f"{league_id} low match count",
                            f"Only {matches} matches (need {thresholds['matches']})",
                        )

                    # Check data staleness
                    if latest:
                        days_since = (datetime.now().date() - latest).days
                        if days_since > 30:
                            self.add_alert(
                                "WARNING",
                                f"{league_id} stale data",
                                f"Latest match is {days_since} days old",
                            )
                else:
                    self.add_alert(
                        "ERROR",
                        f"League {league_id} not found",
                        "League missing from database",
                    )

            except Exception as e:
                self.add_alert("ERROR", f"League {league_id} analysis failed", str(e))

    def calculate_performance_metrics(self):
        """Calculate system performance and efficiency metrics"""
        print("\n⚡ ANALYZING PERFORMANCE METRICS")
        print("=" * 40)

        try:
            # Database performance indicators
            perf_metrics = execute_query_one(
                """
                SELECT 
                    (SELECT pg_database_size(current_database())) as db_size_bytes,
                    (SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active') as active_connections
            """
            )

            if perf_metrics:
                db_size_mb = round(perf_metrics["db_size_bytes"] / (1024 * 1024), 2)
                active_conns = perf_metrics["active_connections"]

                self.metrics["database_size_mb"] = db_size_mb
                self.metrics["active_connections"] = active_conns

                print(f"✅ Database size: {db_size_mb:,} MB")
                print(f"✅ Active connections: {active_conns}")

                if db_size_mb > 5000:  # 5GB threshold
                    self.add_alert(
                        "WARNING",
                        "Large database size",
                        f"Database is {db_size_mb:,} MB",
                    )
                if active_conns > 20:
                    self.add_alert(
                        "WARNING",
                        "High connection count",
                        f"{active_conns} active connections",
                    )

        except Exception as e:
            # PostgreSQL-specific queries might fail in other DBs
            print(f"⚠️  Performance metrics unavailable: {str(e)}")

    def add_alert(self, level: str, title: str, message: str):
        """Add an alert to the monitoring system"""
        alert = {
            "level": level,  # ERROR, WARNING, INFO
            "title": title,
            "message": message,
            "timestamp": datetime.now(),
        }
        self.alerts.append(alert)

    def generate_health_score(self) -> int:
        """Generate overall health score (0-100)"""
        score = 100

        # Deduct points for alerts
        for alert in self.alerts:
            if alert["level"] == "ERROR":
                score -= 15
            elif alert["level"] == "WARNING":
                score -= 5

        # Bonus for good metrics
        if self.metrics.get("series_stats_coverage", 0) >= 95:
            score += 5
        if self.metrics.get("player_name_completeness", 0) >= 95:
            score += 5
        if self.metrics.get("match_winner_completeness", 0) >= 98:
            score += 5

        return max(0, min(100, score))

    def run_monitoring(self):
        """Run complete monitoring suite"""
        print("🔍 STARTING DATA QUALITY MONITORING")
        print("=" * 60)
        print(f"Timestamp: {self.start_time}")
        print("=" * 60)

        try:
            self.calculate_basic_metrics()
            self.calculate_data_freshness()
            self.calculate_completeness_metrics()
            self.calculate_consistency_metrics()
            self.calculate_league_specific_metrics()
            self.calculate_performance_metrics()

        except Exception as e:
            self.add_alert("ERROR", "Monitoring system error", str(e))
            print(f"❌ Monitoring error: {str(e)}")
            print(traceback.format_exc())

        self.print_monitoring_report()
        self.save_metrics_to_file()

        # Return True if system is healthy (no critical errors)
        critical_errors = [a for a in self.alerts if a["level"] == "ERROR"]
        return len(critical_errors) == 0

    def print_monitoring_report(self):
        """Print comprehensive monitoring report"""
        end_time = datetime.now()
        duration = end_time - self.start_time
        health_score = self.generate_health_score()

        print("\n" + "=" * 60)
        print("📊 DATA QUALITY MONITORING REPORT")
        print("=" * 60)

        # Health Score
        if health_score >= 90:
            health_icon = "🟢"
            health_status = "EXCELLENT"
        elif health_score >= 75:
            health_icon = "🟡"
            health_status = "GOOD"
        elif health_score >= 50:
            health_icon = "🟠"
            health_status = "POOR"
        else:
            health_icon = "🔴"
            health_status = "CRITICAL"

        print(
            f"\n{health_icon} OVERALL HEALTH SCORE: {health_score}/100 ({health_status})"
        )

        # Alert Summary
        errors = [a for a in self.alerts if a["level"] == "ERROR"]
        warnings = [a for a in self.alerts if a["level"] == "WARNING"]

        print(f"\n📈 MONITORING SUMMARY:")
        print(f"   ⏱️  Duration: {duration}")
        print(f"   📊 Metrics collected: {len(self.metrics)}")
        print(f"   ❌ Errors: {len(errors)}")
        print(f"   ⚠️  Warnings: {len(warnings)}")

        # Key Metrics
        print(f"\n📋 KEY METRICS:")
        key_metrics = [
            ("Total Players", "players_count"),
            ("Total Teams", "series_stats_count"),
            ("Total Matches", "match_scores_count"),
            ("Series Coverage", "series_stats_coverage"),
            ("Player Names", "player_name_completeness"),
            ("Match Winners", "match_winner_completeness"),
        ]

        for label, metric_key in key_metrics:
            value = self.metrics.get(metric_key, "N/A")
            if isinstance(value, (int, float)) and metric_key.endswith(
                ("_completeness", "_coverage")
            ):
                print(f"   📊 {label}: {value}%")
            elif isinstance(value, int):
                print(f"   📊 {label}: {value:,}")
            else:
                print(f"   📊 {label}: {value}")

        # Critical Issues
        if errors:
            print(f"\n❌ CRITICAL ISSUES ({len(errors)}):")
            for error in errors:
                print(f"   • {error['title']}: {error['message']}")

        # Warnings
        if warnings:
            print(f"\n⚠️  WARNINGS ({len(warnings)}):")
            for warning in warnings[:5]:  # Show first 5 warnings
                print(f"   • {warning['title']}: {warning['message']}")
            if len(warnings) > 5:
                print(f"   ... and {len(warnings) - 5} more warnings")

        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if health_score >= 90:
            print("   ✅ System is healthy - continue regular monitoring")
            print("   📈 Consider expanding monitoring coverage")
        elif health_score >= 75:
            print("   ⚠️  Address warnings to improve data quality")
            print("   🔍 Review ETL processes for improvements")
        else:
            print("   🚨 IMMEDIATE ACTION REQUIRED")
            print("   🛠️  Fix critical errors before next deployment")
            print("   📢 Alert development team")

        print(
            f"\n📊 Full metrics saved to: logs/data_quality_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

    def save_metrics_to_file(self):
        """Save metrics to JSON file for historical tracking"""
        try:
            # Ensure logs directory exists
            os.makedirs("logs", exist_ok=True)

            # Prepare data for JSON serialization
            report_data = {
                "timestamp": self.start_time.isoformat(),
                "health_score": self.generate_health_score(),
                "metrics": self.metrics,
                "alerts": [
                    {
                        "level": alert["level"],
                        "title": alert["title"],
                        "message": alert["message"],
                        "timestamp": alert["timestamp"].isoformat(),
                    }
                    for alert in self.alerts
                ],
            }

            filename = f"logs/data_quality_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            with open(filename, "w") as f:
                json.dump(report_data, f, indent=2)

            print(f"✅ Metrics saved to {filename}")

        except Exception as e:
            print(f"⚠️  Could not save metrics: {str(e)}")


def main():
    """Main entry point"""
    monitor = DataQualityMonitor()
    is_healthy = monitor.run_monitoring()

    # Exit code: 0 if healthy, 1 if issues found
    return 0 if is_healthy else 1


if __name__ == "__main__":
    sys.exit(main())
