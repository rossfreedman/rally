#!/usr/bin/env python3
"""
Comprehensive Database Analysis
Analyzes local and Railway databases to identify all data differences and patterns
"""

import json
import logging
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime
from urllib.parse import urlparse

import psycopg2

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_config import get_db

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

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


class DatabaseAnalyzer:
    """Comprehensive database analysis and comparison"""

    def __init__(self):
        self.local_conn = None
        self.railway_conn = None
        self.analysis_results = {
            "table_counts": {},
            "content_differences": {},
            "data_quality": {},
            "schema_differences": {},
            "migration_status": {},
            "recommendations": [],
            "analysis_timestamp": datetime.now().isoformat(),
        }

    def connect_databases(self):
        """Establish database connections"""
        logger.info("🔌 Connecting to databases...")
        self.local_db_context = get_db()
        self.local_conn = self.local_db_context.__enter__()
        self.railway_conn = connect_to_railway()

    def disconnect_databases(self):
        """Close database connections"""
        if hasattr(self, "local_db_context") and self.local_db_context:
            try:
                self.local_db_context.__exit__(None, None, None)
            except:
                pass
        if self.railway_conn:
            try:
                self.railway_conn.close()
            except:
                pass

    def analyze_table_counts(self):
        """Analyze and compare table counts"""
        logger.info("📊 Analyzing table counts...")

        tables = [
            "users",
            "leagues",
            "clubs",
            "players",
            "series",
            "series_stats",
            "match_scores",
            "player_availability",
            "schedule",
            "player_history",
            "user_player_associations",
            "user_instructions",
            "user_activity_logs",
        ]

        local_cursor = self.local_conn.cursor()
        railway_cursor = self.railway_conn.cursor()

        for table in tables:
            # Local count
            try:
                local_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                local_count = local_cursor.fetchone()[0]
            except Exception as e:
                local_count = f"ERROR: {e}"

            # Railway count
            try:
                railway_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                railway_count = railway_cursor.fetchone()[0]
            except Exception as e:
                railway_count = f"ERROR: {e}"

            self.analysis_results["table_counts"][table] = {
                "local": local_count,
                "railway": railway_count,
                "difference": (
                    railway_count - local_count
                    if isinstance(local_count, int) and isinstance(railway_count, int)
                    else "N/A"
                ),
                "coverage_percent": (
                    (railway_count / local_count * 100)
                    if isinstance(local_count, int)
                    and isinstance(railway_count, int)
                    and local_count > 0
                    else 0
                ),
            }

        print("\n" + "=" * 100)
        print("📊 TABLE COUNTS COMPARISON")
        print("=" * 100)
        print(
            f"{'Table':<25} {'Local':<12} {'Railway':<12} {'Difference':<12} {'Coverage':<12} {'Status':<15}"
        )
        print("-" * 100)

        for table, counts in self.analysis_results["table_counts"].items():
            local = counts["local"]
            railway = counts["railway"]
            diff = counts["difference"]
            coverage = (
                f"{counts['coverage_percent']:.1f}%"
                if isinstance(counts["coverage_percent"], (int, float))
                else "N/A"
            )

            if isinstance(local, int) and isinstance(railway, int):
                if railway == local:
                    status = "✅ MATCH"
                elif railway == 0:
                    status = "❌ EMPTY"
                elif railway < local * 0.5:
                    status = "🔴 LOW"
                elif railway < local * 0.9:
                    status = "🟡 PARTIAL"
                else:
                    status = "🟢 GOOD"
            else:
                status = "❌ ERROR"

            print(
                f"{table:<25} {str(local):<12} {str(railway):<12} {str(diff):<12} {coverage:<12} {status:<15}"
            )

    def analyze_content_differences(self):
        """Analyze content differences in key tables"""
        logger.info("🔍 Analyzing content differences...")

        key_tables = ["leagues", "clubs", "series", "players"]

        for table in key_tables:
            logger.info(f"  📋 Analyzing {table}...")

            local_cursor = self.local_conn.cursor()
            railway_cursor = self.railway_conn.cursor()

            table_analysis = {
                "local_sample": [],
                "railway_sample": [],
                "unique_to_local": [],
                "unique_to_railway": [],
                "common_count": 0,
            }

            try:
                # Get sample data
                local_cursor.execute(f"SELECT * FROM {table} LIMIT 5")
                local_columns = [desc[0] for desc in local_cursor.description]
                local_sample = local_cursor.fetchall()
                table_analysis["local_sample"] = [
                    dict(zip(local_columns, row)) for row in local_sample
                ]

                railway_cursor.execute(f"SELECT * FROM {table} LIMIT 5")
                railway_columns = [desc[0] for desc in railway_cursor.description]
                railway_sample = railway_cursor.fetchall()
                table_analysis["railway_sample"] = [
                    dict(zip(railway_columns, row)) for row in railway_sample
                ]

                # For clubs and series, analyze unique entries
                if table in ["clubs", "series"]:
                    # Get all names
                    local_cursor.execute(f"SELECT name FROM {table}")
                    local_names = {
                        row[0].strip().lower() for row in local_cursor.fetchall()
                    }

                    railway_cursor.execute(f"SELECT name FROM {table}")
                    railway_names = {
                        row[0].strip().lower() for row in railway_cursor.fetchall()
                    }

                    table_analysis["unique_to_local"] = list(
                        local_names - railway_names
                    )
                    table_analysis["unique_to_railway"] = list(
                        railway_names - local_names
                    )
                    table_analysis["common_count"] = len(local_names & railway_names)

            except Exception as e:
                table_analysis["error"] = str(e)

            self.analysis_results["content_differences"][table] = table_analysis

    def analyze_league_distribution(self):
        """Analyze league distribution patterns"""
        logger.info("🏆 Analyzing league distribution...")

        local_cursor = self.local_conn.cursor()
        railway_cursor = self.railway_conn.cursor()

        league_analysis = {}

        # Get league distributions
        for db_name, cursor in [("local", local_cursor), ("railway", railway_cursor)]:
            try:
                cursor.execute(
                    """
                    SELECT l.league_name, COUNT(p.id) as player_count, COUNT(DISTINCT p.club_id) as club_count
                    FROM players p
                    JOIN leagues l ON p.league_id = l.id
                    GROUP BY l.id, l.league_name
                    ORDER BY player_count DESC
                """
                )

                league_analysis[db_name] = [
                    {"league": row[0], "players": row[1], "clubs": row[2]}
                    for row in cursor.fetchall()
                ]
            except Exception as e:
                league_analysis[db_name] = f"ERROR: {e}"

        self.analysis_results["data_quality"]["league_distribution"] = league_analysis

        print(f"\n🏆 LEAGUE DISTRIBUTION ANALYSIS")
        print("=" * 80)

        for db_name, data in league_analysis.items():
            print(f"\n📋 {db_name.upper()} DATABASE:")
            if isinstance(data, list):
                for league_info in data:
                    print(
                        f"  • {league_info['league']}: {league_info['players']} players, {league_info['clubs']} clubs"
                    )
            else:
                print(f"  ❌ {data}")

    def analyze_club_series_relationships(self):
        """Analyze club-series relationships"""
        logger.info("🔗 Analyzing club-series relationships...")

        relationship_analysis = {}

        for db_name, conn in [
            ("local", self.local_conn),
            ("railway", self.railway_conn),
        ]:
            cursor = conn.cursor()

            try:
                # Get club-series combinations
                cursor.execute(
                    """
                    SELECT c.name as club_name, s.name as series_name, COUNT(p.id) as player_count
                    FROM players p
                    JOIN clubs c ON p.club_id = c.id
                    JOIN series s ON p.series_id = s.id
                    GROUP BY c.name, s.name
                    HAVING COUNT(p.id) > 5
                    ORDER BY player_count DESC
                    LIMIT 20
                """
                )

                relationship_analysis[db_name] = [
                    {"club": row[0], "series": row[1], "players": row[2]}
                    for row in cursor.fetchall()
                ]
            except Exception as e:
                relationship_analysis[db_name] = f"ERROR: {e}"

        self.analysis_results["data_quality"][
            "club_series_relationships"
        ] = relationship_analysis

    def analyze_data_quality_issues(self):
        """Analyze data quality issues"""
        logger.info("🔬 Analyzing data quality issues...")

        quality_issues = {}

        for db_name, conn in [
            ("local", self.local_conn),
            ("railway", self.railway_conn),
        ]:
            cursor = conn.cursor()
            db_issues = {}

            try:
                # Check for NULL values in key fields
                cursor.execute(
                    "SELECT COUNT(*) FROM players WHERE first_name IS NULL OR first_name = ''"
                )
                db_issues["players_missing_first_name"] = cursor.fetchone()[0]

                cursor.execute(
                    "SELECT COUNT(*) FROM players WHERE last_name IS NULL OR last_name = ''"
                )
                db_issues["players_missing_last_name"] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM players WHERE club_id IS NULL")
                db_issues["players_missing_club"] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM players WHERE series_id IS NULL")
                db_issues["players_missing_series"] = cursor.fetchone()[0]

                # Check for duplicate names
                cursor.execute(
                    """
                    SELECT first_name, last_name, COUNT(*) 
                    FROM players 
                    GROUP BY first_name, last_name 
                    HAVING COUNT(*) > 1
                    ORDER BY COUNT(*) DESC
                    LIMIT 10
                """
                )
                db_issues["duplicate_player_names"] = cursor.fetchall()

                # Check for orphaned relationships
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM players p 
                    LEFT JOIN clubs c ON p.club_id = c.id 
                    WHERE p.club_id IS NOT NULL AND c.id IS NULL
                """
                )
                db_issues["orphaned_club_references"] = cursor.fetchone()[0]

            except Exception as e:
                db_issues["error"] = str(e)

            quality_issues[db_name] = db_issues

        self.analysis_results["data_quality"]["quality_issues"] = quality_issues

        print(f"\n🔬 DATA QUALITY ANALYSIS")
        print("=" * 80)

        for db_name, issues in quality_issues.items():
            print(f"\n📋 {db_name.upper()} DATABASE:")
            if "error" in issues:
                print(f"  ❌ {issues['error']}")
            else:
                print(
                    f"  • Players missing first name: {issues['players_missing_first_name']}"
                )
                print(
                    f"  • Players missing last name: {issues['players_missing_last_name']}"
                )
                print(f"  • Players missing club: {issues['players_missing_club']}")
                print(f"  • Players missing series: {issues['players_missing_series']}")
                print(
                    f"  • Orphaned club references: {issues['orphaned_club_references']}"
                )

                if issues["duplicate_player_names"]:
                    print(f"  • Top duplicate names:")
                    for name_info in issues["duplicate_player_names"][:5]:
                        print(
                            f"    - {name_info[0]} {name_info[1]}: {name_info[2]} instances"
                        )

    def analyze_migration_status(self):
        """Analyze migration effectiveness"""
        logger.info("📈 Analyzing migration status...")

        migration_stats = {}

        # Calculate migration rates by category
        local_cursor = self.local_conn.cursor()
        railway_cursor = self.railway_conn.cursor()

        # By league
        for league_id, league_name in [
            (1, "APTA Chicago"),
            (2, "APTA National"),
            (3, "NSFT"),
        ]:
            local_cursor.execute(
                "SELECT COUNT(*) FROM players WHERE league_id = %s", (league_id,)
            )
            local_count = local_cursor.fetchone()[0]

            railway_cursor.execute(
                "SELECT COUNT(*) FROM players WHERE league_id = %s", (league_id,)
            )
            railway_count = railway_cursor.fetchone()[0]

            migration_stats[league_name] = {
                "local": local_count,
                "railway": railway_count,
                "migration_rate": (
                    (railway_count / local_count * 100) if local_count > 0 else 0
                ),
            }

        # Skip club size analysis for now due to complex query
        # Focus on league-based migration analysis which is more important

        self.analysis_results["migration_status"] = migration_stats

        print(f"\n📈 MIGRATION STATUS BY LEAGUE")
        print("=" * 80)

        for league, stats in migration_stats.items():
            rate = stats["migration_rate"]
            status = (
                "🟢 EXCELLENT"
                if rate > 90
                else "🟡 GOOD" if rate > 70 else "🔴 NEEDS WORK"
            )
            print(
                f"  • {league}: {stats['railway']}/{stats['local']} ({rate:.1f}%) {status}"
            )

    def generate_recommendations(self):
        """Generate actionable recommendations"""
        logger.info("💡 Generating recommendations...")

        recommendations = []

        # Analyze table counts for recommendations
        table_counts = self.analysis_results["table_counts"]

        # Check for empty or low-coverage tables
        for table, counts in table_counts.items():
            if isinstance(counts["coverage_percent"], (int, float)):
                coverage = counts["coverage_percent"]
                if (
                    coverage == 0
                    and isinstance(counts["local"], int)
                    and counts["local"] > 0
                ):
                    recommendations.append(
                        {
                            "priority": "HIGH",
                            "category": "missing_data",
                            "title": f"Migrate {table} data",
                            "description": f'{table} has {counts["local"]} records locally but 0 in Railway',
                            "impact": f'{counts["local"]} records',
                        }
                    )
                elif (
                    coverage < 50
                    and isinstance(counts["local"], int)
                    and counts["local"] > 100
                ):
                    recommendations.append(
                        {
                            "priority": "MEDIUM",
                            "category": "incomplete_migration",
                            "title": f"Complete {table} migration",
                            "description": f"{table} only has {coverage:.1f}% coverage",
                            "impact": f'{counts["local"] - counts["railway"]} missing records',
                        }
                    )

        # Check for unique entities
        content_diffs = self.analysis_results["content_differences"]
        for table, analysis in content_diffs.items():
            if "unique_to_local" in analysis and analysis["unique_to_local"]:
                count = len(analysis["unique_to_local"])
                recommendations.append(
                    {
                        "priority": "MEDIUM",
                        "category": "missing_entities",
                        "title": f"Add missing {table} to Railway",
                        "description": f"{count} {table} exist locally but not in Railway",
                        "impact": f"{count} {table}",
                        "examples": analysis["unique_to_local"][:5],
                    }
                )

        self.analysis_results["recommendations"] = recommendations

        print(f"\n💡 RECOMMENDATIONS")
        print("=" * 80)

        for i, rec in enumerate(recommendations[:10], 1):
            print(f"{i}. [{rec['priority']}] {rec['title']}")
            print(f"   {rec['description']}")
            print(f"   Impact: {rec['impact']}")
            if "examples" in rec:
                print(f"   Examples: {', '.join(rec['examples'])}")
            print()

    def save_analysis_report(self, filename="comprehensive_database_analysis.json"):
        """Save comprehensive analysis report"""
        filepath = os.path.join("scripts", filename)

        # Convert any datetime objects to strings for JSON serialization
        def convert_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj

        with open(filepath, "w") as f:
            json.dump(self.analysis_results, f, indent=2, default=convert_datetime)

        logger.info(f"📄 Analysis report saved to {filepath}")
        return filepath

    def print_executive_summary(self):
        """Print executive summary"""
        table_counts = self.analysis_results["table_counts"]

        print("\n" + "=" * 100)
        print("📋 EXECUTIVE SUMMARY")
        print("=" * 100)

        # Overall migration status
        total_local = sum(
            counts["local"]
            for counts in table_counts.values()
            if isinstance(counts["local"], int)
        )
        total_railway = sum(
            counts["railway"]
            for counts in table_counts.values()
            if isinstance(counts["railway"], int)
        )
        overall_coverage = (total_railway / total_local * 100) if total_local > 0 else 0

        print(f"🎯 OVERALL DATABASE STATUS:")
        print(f"  • Total records in local: {total_local:,}")
        print(f"  • Total records in Railway: {total_railway:,}")
        print(f"  • Overall coverage: {overall_coverage:.1f}%")
        print(f"  • Migration gap: {total_local - total_railway:,} records")

        # Key metrics
        players_local = table_counts.get("players", {}).get("local", 0)
        players_railway = table_counts.get("players", {}).get("railway", 0)
        player_coverage = (
            (players_railway / players_local * 100) if players_local > 0 else 0
        )

        print(f"\n🏃 PLAYER MIGRATION STATUS:")
        print(
            f"  • Players migrated: {players_railway:,}/{players_local:,} ({player_coverage:.1f}%)"
        )

        # Critical issues
        critical_issues = []
        for table, counts in table_counts.items():
            if (
                isinstance(counts["coverage_percent"], (int, float))
                and counts["coverage_percent"] == 0
                and isinstance(counts["local"], int)
                and counts["local"] > 0
            ):
                critical_issues.append(f"{table} ({counts['local']} records)")

        if critical_issues:
            print(f"\n❌ CRITICAL GAPS:")
            for issue in critical_issues:
                print(f"  • {issue}")

        # Success metrics
        complete_tables = [
            table
            for table, counts in table_counts.items()
            if isinstance(counts["coverage_percent"], (int, float))
            and counts["coverage_percent"] == 100
        ]

        if complete_tables:
            print(f"\n✅ COMPLETE MIGRATIONS:")
            for table in complete_tables:
                count = table_counts[table]["local"]
                print(f"  • {table} ({count:,} records)")


def main():
    """Main analysis function"""
    logger.info("🔍 COMPREHENSIVE DATABASE ANALYSIS")
    logger.info("=" * 100)

    analyzer = DatabaseAnalyzer()

    try:
        analyzer.connect_databases()

        # Perform comprehensive analysis
        analyzer.analyze_table_counts()
        analyzer.analyze_content_differences()
        analyzer.analyze_league_distribution()
        analyzer.analyze_club_series_relationships()
        analyzer.analyze_data_quality_issues()
        analyzer.analyze_migration_status()
        analyzer.generate_recommendations()

        # Save and summarize
        report_path = analyzer.save_analysis_report()
        analyzer.print_executive_summary()

        logger.info(f"\n✅ COMPREHENSIVE ANALYSIS COMPLETE!")
        logger.info(f"📄 Detailed report: {report_path}")

        return True

    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        return False

    finally:
        analyzer.disconnect_databases()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
