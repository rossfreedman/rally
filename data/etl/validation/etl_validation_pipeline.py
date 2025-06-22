#!/usr/bin/env python3
"""
ETL Validation Pipeline
======================

Comprehensive validation script that runs after ETL import to verify:
- Data completeness and quality
- User-facing feature functionality
- Critical data relationships
- Statistical accuracy

Run this after every ETL import to ensure system reliability.
"""

import os
import sys
import traceback
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../.."))

from database_utils import execute_query, execute_query_one


class ETLValidator:
    def __init__(self):
        self.validation_results = []
        self.errors = []
        self.warnings = []
        self.start_time = datetime.now()

    def log_result(
        self,
        test_name: str,
        status: str,
        details: str = "",
        expected: Any = None,
        actual: Any = None,
    ):
        """Log validation result"""
        result = {
            "test": test_name,
            "status": status,  # PASS, FAIL, WARNING
            "details": details,
            "expected": expected,
            "actual": actual,
            "timestamp": datetime.now(),
        }
        self.validation_results.append(result)

        if status == "FAIL":
            self.errors.append(result)
        elif status == "WARNING":
            self.warnings.append(result)

        # Print real-time results
        icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{icon} {test_name}: {status}")
        if details:
            print(f"   {details}")
        if expected is not None and actual is not None:
            print(f"   Expected: {expected}, Actual: {actual}")

    def validate_table_completeness(self):
        """Validate that all critical tables have reasonable data"""
        print("\n🔍 VALIDATING TABLE COMPLETENESS")
        print("=" * 50)

        critical_tables = {
            "leagues": {"min_records": 3, "description": "League definitions"},
            "clubs": {"min_records": 50, "description": "Club records"},
            "series": {"min_records": 10, "description": "Series definitions"},
            "teams": {"min_records": 100, "description": "Team records"},
            "players": {"min_records": 500, "description": "Player records"},
            "match_scores": {"min_records": 1000, "description": "Match results"},
            "series_stats": {"min_records": 100, "description": "Team standings"},
            "schedule": {"min_records": 100, "description": "Game schedules"},
        }

        for table_name, requirements in critical_tables.items():
            try:
                count_result = execute_query_one(
                    f"SELECT COUNT(*) as count FROM {table_name}"
                )
                actual_count = count_result["count"] if count_result else 0
                min_expected = requirements["min_records"]

                if actual_count >= min_expected:
                    self.log_result(
                        f"Table {table_name} completeness",
                        "PASS",
                        f"{requirements['description']}: {actual_count:,} records",
                        f">= {min_expected:,}",
                        f"{actual_count:,}",
                    )
                elif actual_count > 0:
                    self.log_result(
                        f"Table {table_name} completeness",
                        "WARNING",
                        f"{requirements['description']}: Low record count",
                        f">= {min_expected:,}",
                        f"{actual_count:,}",
                    )
                else:
                    self.log_result(
                        f"Table {table_name} completeness",
                        "FAIL",
                        f"{requirements['description']}: No data found",
                        f">= {min_expected:,}",
                        "0",
                    )

            except Exception as e:
                self.log_result(
                    f"Table {table_name} accessibility",
                    "FAIL",
                    f"Cannot access table: {str(e)}",
                )

    def validate_data_relationships(self):
        """Validate foreign key relationships and data consistency"""
        print("\n🔗 VALIDATING DATA RELATIONSHIPS")
        print("=" * 50)

        # Check players have valid league, club, series references
        orphaned_players = execute_query_one(
            """
            SELECT COUNT(*) as count FROM players p
            LEFT JOIN leagues l ON p.league_id = l.id
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE l.id IS NULL OR c.id IS NULL OR s.id IS NULL
        """
        )

        if orphaned_players["count"] == 0:
            self.log_result(
                "Player foreign key integrity",
                "PASS",
                "All players have valid league/club/series references",
            )
        else:
            self.log_result(
                "Player foreign key integrity",
                "FAIL",
                f"{orphaned_players['count']} players have invalid references",
            )

        # Check match_scores have corresponding teams
        orphaned_matches = execute_query_one(
            """
            SELECT COUNT(*) as count FROM match_scores m
            WHERE (m.home_team IS NULL OR m.away_team IS NULL)
            OR (m.home_team = '' OR m.away_team = '')
        """
        )

        if orphaned_matches["count"] == 0:
            self.log_result(
                "Match team references", "PASS", "All matches have valid team names"
            )
        else:
            self.log_result(
                "Match team references",
                "WARNING",
                f"{orphaned_matches['count']} matches missing team data",
            )

        # Check series_stats coverage vs actual teams in matches
        teams_in_matches = execute_query_one(
            """
            SELECT COUNT(DISTINCT COALESCE(home_team, away_team)) as count
            FROM (
                SELECT home_team, NULL as away_team FROM match_scores WHERE home_team IS NOT NULL
                UNION ALL
                SELECT NULL as home_team, away_team FROM match_scores WHERE away_team IS NOT NULL
            ) all_teams
            WHERE COALESCE(home_team, away_team) IS NOT NULL
        """
        )

        teams_in_stats = execute_query_one("SELECT COUNT(*) as count FROM series_stats")

        coverage = (
            (teams_in_stats["count"] / teams_in_matches["count"] * 100)
            if teams_in_matches["count"] > 0
            else 0
        )

        if coverage >= 95:
            self.log_result(
                "Series stats coverage",
                "PASS",
                f"{coverage:.1f}% of teams have statistics",
            )
        elif coverage >= 85:
            self.log_result(
                "Series stats coverage",
                "WARNING",
                f"Only {coverage:.1f}% coverage",
                ">= 95%",
                f"{coverage:.1f}%",
            )
        else:
            self.log_result(
                "Series stats coverage",
                "FAIL",
                f"Poor coverage: {coverage:.1f}%",
                ">= 95%",
                f"{coverage:.1f}%",
            )

    def validate_statistical_accuracy(self):
        """Validate that calculated statistics match actual data"""
        print("\n📊 VALIDATING STATISTICAL ACCURACY")
        print("=" * 50)

        # Check that series_stats points align with match wins
        mismatched_points = execute_query(
            """
            SELECT s.team, s.points, s.matches_won,
                   COUNT(CASE WHEN ((m.home_team = s.team AND m.winner = 'home') OR 
                                   (m.away_team = s.team AND m.winner = 'away')) THEN 1 END) as actual_wins
            FROM series_stats s
            LEFT JOIN match_scores m ON (m.home_team = s.team OR m.away_team = s.team)
            WHERE s.league_id IS NOT NULL
            GROUP BY s.team, s.points, s.matches_won
            HAVING s.matches_won != COUNT(CASE WHEN ((m.home_team = s.team AND m.winner = 'home') OR 
                                                    (m.away_team = s.team AND m.winner = 'away')) THEN 1 END)
            LIMIT 5
        """
        )

        if not mismatched_points:
            self.log_result(
                "Match win calculations",
                "PASS",
                "Series stats match actual match results",
            )
        else:
            details = f"{len(mismatched_points)} teams have mismatched win counts"
            self.log_result("Match win calculations", "WARNING", details)
            for team in mismatched_points[:3]:
                print(
                    f"   {team['team']}: Stats={team['matches_won']}, Actual={team['actual_wins']}"
                )

        # Check for teams with wins but zero points
        zero_point_winners = execute_query_one(
            """
            SELECT COUNT(*) as count FROM series_stats 
            WHERE matches_won > 0 AND points = 0
        """
        )

        if zero_point_winners["count"] == 0:
            self.log_result(
                "Points calculation", "PASS", "Teams with wins have appropriate points"
            )
        else:
            self.log_result(
                "Points calculation",
                "WARNING",
                f"{zero_point_winners['count']} teams have wins but zero points",
            )

    def validate_user_features(self):
        """Test that critical user-facing features have required data"""
        print("\n👤 VALIDATING USER FEATURES")
        print("=" * 50)

        # Test my-series page data availability
        try:
            # Check if we can get series standings for major leagues
            major_leagues = ["CNSWPL", "APTA_CHICAGO", "NSTF"]

            for league_id in major_leagues:
                league_teams = execute_query_one(
                    """
                    SELECT COUNT(*) as count FROM series_stats s
                    JOIN leagues l ON s.league_id = l.id
                    WHERE l.league_id = %s
                """,
                    [league_id],
                )

                if league_teams and league_teams["count"] > 10:
                    self.log_result(
                        f"My-series data ({league_id})",
                        "PASS",
                        f"{league_teams['count']} teams available",
                    )
                elif league_teams and league_teams["count"] > 0:
                    self.log_result(
                        f"My-series data ({league_id})",
                        "WARNING",
                        f"Only {league_teams['count']} teams",
                        "> 10",
                        league_teams["count"],
                    )
                else:
                    self.log_result(
                        f"My-series data ({league_id})",
                        "FAIL",
                        "No series data available",
                    )

        except Exception as e:
            self.log_result(
                "My-series feature", "FAIL", f"Cannot test series data: {str(e)}"
            )

        # Test availability system
        try:
            recent_matches = execute_query_one(
                """
                SELECT COUNT(*) as count FROM match_scores 
                WHERE match_date >= CURRENT_DATE - INTERVAL '30 days'
            """
            )

            if recent_matches and recent_matches["count"] > 50:
                self.log_result(
                    "Availability system data",
                    "PASS",
                    f"{recent_matches['count']} recent matches for availability",
                )
            elif recent_matches and recent_matches["count"] > 0:
                self.log_result(
                    "Availability system data",
                    "WARNING",
                    f"Only {recent_matches['count']} recent matches",
                )
            else:
                self.log_result(
                    "Availability system data", "WARNING", "No recent matches found"
                )

        except Exception as e:
            self.log_result(
                "Availability feature",
                "FAIL",
                f"Cannot test availability data: {str(e)}",
            )

    def validate_league_consistency(self):
        """Validate consistency within and across leagues"""
        print("\n🏆 VALIDATING LEAGUE CONSISTENCY")
        print("=" * 50)

        # Check series naming consistency within leagues
        try:
            inconsistent_series = execute_query(
                """
                SELECT l.league_id, s.series, COUNT(*) as team_count
                FROM series_stats s
                JOIN leagues l ON s.league_id = l.id
                WHERE l.league_id = 'CNSWPL'
                GROUP BY l.league_id, s.series
                HAVING COUNT(*) < 5
                ORDER BY team_count ASC
            """
            )

            if not inconsistent_series:
                self.log_result(
                    "CNSWPL series consistency",
                    "PASS",
                    "All series have reasonable team counts",
                )
            else:
                small_series = [
                    f"{row['series']} ({row['team_count']} teams)"
                    for row in inconsistent_series
                ]
                self.log_result(
                    "CNSWPL series consistency",
                    "WARNING",
                    f"Small series found: {', '.join(small_series[:3])}",
                )

        except Exception as e:
            self.log_result(
                "League consistency check", "FAIL", f"Cannot validate: {str(e)}"
            )

        # Check for duplicate team names within leagues
        try:
            duplicates = execute_query(
                """
                SELECT s.team, l.league_id, COUNT(*) as duplicate_count
                FROM series_stats s
                JOIN leagues l ON s.league_id = l.id
                GROUP BY s.team, l.league_id
                HAVING COUNT(*) > 1
            """
            )

            if not duplicates:
                self.log_result(
                    "Team name uniqueness", "PASS", "No duplicate team names found"
                )
            else:
                dup_teams = [
                    f"{row['team']} in {row['league_id']}" for row in duplicates[:3]
                ]
                self.log_result(
                    "Team name uniqueness",
                    "WARNING",
                    f"Duplicates found: {', '.join(dup_teams)}",
                )

        except Exception as e:
            self.log_result(
                "Duplicate check", "FAIL", f"Cannot check duplicates: {str(e)}"
            )

    def run_comprehensive_validation(self):
        """Run all validation checks"""
        print("🚀 STARTING ETL VALIDATION PIPELINE")
        print("=" * 60)
        print(f"Timestamp: {self.start_time}")
        print("=" * 60)

        try:
            self.validate_table_completeness()
            self.validate_data_relationships()
            self.validate_statistical_accuracy()
            self.validate_user_features()
            self.validate_league_consistency()

        except Exception as e:
            self.log_result("Validation pipeline", "FAIL", f"Pipeline error: {str(e)}")
            print(f"❌ Pipeline error: {str(e)}")
            print(traceback.format_exc())

        self.print_summary()
        return len(self.errors) == 0

    def print_summary(self):
        """Print validation summary"""
        end_time = datetime.now()
        duration = end_time - self.start_time

        print("\n" + "=" * 60)
        print("📋 VALIDATION SUMMARY")
        print("=" * 60)

        total_tests = len(self.validation_results)
        passed = len([r for r in self.validation_results if r["status"] == "PASS"])
        failed = len(self.errors)
        warnings = len(self.warnings)

        print(f"⏱️  Duration: {duration}")
        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed}")
        print(f"⚠️  Warnings: {warnings}")
        print(f"❌ Failed: {failed}")

        if failed == 0 and warnings == 0:
            print(f"\n🎉 ALL VALIDATIONS PASSED! ETL import is successful.")
        elif failed == 0:
            print(f"\n✅ ETL validation passed with {warnings} warnings to review.")
        else:
            print(f"\n🚨 ETL validation FAILED! {failed} critical issues found.")

        if self.errors:
            print("\n❌ CRITICAL ISSUES:")
            for error in self.errors:
                print(f"   • {error['test']}: {error['details']}")

        if self.warnings:
            print("\n⚠️  WARNINGS TO REVIEW:")
            for warning in self.warnings[:5]:  # Show first 5 warnings
                print(f"   • {warning['test']}: {warning['details']}")
            if len(self.warnings) > 5:
                print(f"   ... and {len(self.warnings) - 5} more warnings")

        print("\n📈 NEXT STEPS:")
        if failed > 0:
            print("   1. Fix critical issues before deploying")
            print("   2. Consider rolling back to previous data state")
            print("   3. Review ETL process for root causes")
        elif warnings > 0:
            print("   1. Review warnings for potential improvements")
            print("   2. Monitor affected features")
            print("   3. Consider data quality improvements")
        else:
            print("   1. Deploy with confidence!")
            print("   2. Monitor system performance")
            print("   3. Continue regular validation")


def main():
    """Main entry point"""
    validator = ETLValidator()
    success = validator.run_comprehensive_validation()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
