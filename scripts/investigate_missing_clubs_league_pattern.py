#!/usr/bin/env python3
"""
Investigate Missing Clubs League Pattern
Specifically checking if missing clubs are related to Series 2B and NSFT league
"""

import json
import logging
import os
import sys
from collections import Counter, defaultdict
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


def analyze_leagues():
    """Analyze league distribution in both databases"""
    logger.info("🔍 Analyzing league patterns...")

    with get_db() as local_conn:
        railway_conn = connect_to_railway()

        local_cursor = local_conn.cursor()
        railway_cursor = railway_conn.cursor()

        print("\n" + "=" * 80)
        print("🏆 LEAGUE ANALYSIS")
        print("=" * 80)

        # Check leagues table
        print("\n📋 LEAGUES COMPARISON:")
        local_cursor.execute("SELECT * FROM leagues ORDER BY id")
        local_leagues = local_cursor.fetchall()

        railway_cursor.execute("SELECT * FROM leagues ORDER BY id")
        railway_leagues = railway_cursor.fetchall()

        print(f"LOCAL LEAGUES ({len(local_leagues)}):")
        for league in local_leagues:
            print(f"  • ID {league[0]}: {league[1]} - {league[2]}")

        print(f"\nRAILWAY LEAGUES ({len(railway_leagues)}):")
        for league in railway_leagues:
            print(f"  • ID {league[0]}: {league[1]} - {league[2]}")

        railway_conn.close()
        return local_leagues, railway_leagues


def analyze_missing_clubs_by_league():
    """Analyze missing clubs by their league associations"""
    logger.info("🏢 Analyzing missing clubs by league...")

    with get_db() as local_conn:
        railway_conn = connect_to_railway()

        local_cursor = local_conn.cursor()
        railway_cursor = railway_conn.cursor()

        # Get missing club IDs from our previous analysis
        missing_club_ids = [94, 91, 10, 93, 45, 44, 92, 97, 26, 47, 48, 27]

        print("\n" + "=" * 80)
        print("🏢 MISSING CLUBS LEAGUE ANALYSIS")
        print("=" * 80)

        # Analyze each missing club's league associations
        club_league_data = {}

        for club_id in missing_club_ids:
            # Get club info
            local_cursor.execute("SELECT id, name FROM clubs WHERE id = %s", (club_id,))
            club_info = local_cursor.fetchone()

            if club_info:
                club_name = club_info[1]

                # Get players from this club and their leagues/series
                local_cursor.execute(
                    """
                    SELECT p.league_id, l.league_name, p.series_id, s.name as series_name, COUNT(*) as player_count
                    FROM players p
                    LEFT JOIN leagues l ON p.league_id = l.id
                    LEFT JOIN series s ON p.series_id = s.id
                    WHERE p.club_id = %s
                    GROUP BY p.league_id, l.league_name, p.series_id, s.name
                    ORDER BY player_count DESC
                """,
                    (club_id,),
                )

                league_series_data = local_cursor.fetchall()
                club_league_data[club_id] = {
                    "name": club_name,
                    "league_series": league_series_data,
                }

                print(f"\n🏌️ {club_name} (ID: {club_id}):")
                for (
                    league_id,
                    league_name,
                    series_id,
                    series_name,
                    count,
                ) in league_series_data:
                    print(
                        f"  • League {league_id} ({league_name}) - Series {series_id} ({series_name}): {count} players"
                    )

        railway_conn.close()
        return club_league_data


def analyze_series_2b_pattern():
    """Specifically analyze Series 2B pattern"""
    logger.info("🎯 Analyzing Series 2B pattern...")

    with get_db() as local_conn:
        local_cursor = local_conn.cursor()

        print("\n" + "=" * 80)
        print("🎯 SERIES 2B INVESTIGATION")
        print("=" * 80)

        # Find Series 2B
        local_cursor.execute("SELECT id, name FROM series WHERE name ILIKE '%2B%'")
        series_2b = local_cursor.fetchall()

        print(f"\nSERIES 2B MATCHES:")
        for series_id, series_name in series_2b:
            print(f"  • Series {series_id}: {series_name}")

            # Get clubs associated with Series 2B
            local_cursor.execute(
                """
                SELECT c.id, c.name, COUNT(p.id) as player_count
                FROM players p
                JOIN clubs c ON p.club_id = c.id
                WHERE p.series_id = %s
                GROUP BY c.id, c.name
                ORDER BY player_count DESC
            """,
                (series_id,),
            )

            clubs_in_series_2b = local_cursor.fetchall()
            print(f"    Clubs in {series_name}:")
            for club_id, club_name, player_count in clubs_in_series_2b:
                status = (
                    "❌ MISSING"
                    if club_id in [94, 91, 10, 93, 45, 44, 92, 97, 26, 47, 48, 27]
                    else "✅ MAPPED"
                )
                print(
                    f"      • {club_name} (ID: {club_id}): {player_count} players - {status}"
                )


def analyze_nsft_league_pattern():
    """Specifically analyze NSFT league pattern"""
    logger.info("🏁 Analyzing NSFT league pattern...")

    with get_db() as local_conn:
        local_cursor = local_conn.cursor()

        print("\n" + "=" * 80)
        print("🏁 NSFT LEAGUE INVESTIGATION")
        print("=" * 80)

        # Find NSFT league
        local_cursor.execute(
            "SELECT id, league_id, league_name FROM leagues WHERE league_name ILIKE '%NSFT%' OR league_id ILIKE '%NSFT%'"
        )
        nsft_leagues = local_cursor.fetchall()

        if nsft_leagues:
            print(f"\nNSFT LEAGUE MATCHES:")
            for league_id, league_code, league_name in nsft_leagues:
                print(f"  • League {league_id}: {league_code} - {league_name}")

                # Get clubs associated with NSFT league
                local_cursor.execute(
                    """
                    SELECT c.id, c.name, COUNT(p.id) as player_count
                    FROM players p
                    JOIN clubs c ON p.club_id = c.id
                    WHERE p.league_id = %s
                    GROUP BY c.id, c.name
                    ORDER BY player_count DESC
                """,
                    (league_id,),
                )

                clubs_in_nsft = local_cursor.fetchall()
                print(f"    Clubs in {league_name}:")
                for club_id, club_name, player_count in clubs_in_nsft:
                    status = (
                        "❌ MISSING"
                        if club_id in [94, 91, 10, 93, 45, 44, 92, 97, 26, 47, 48, 27]
                        else "✅ MAPPED"
                    )
                    print(
                        f"      • {club_name} (ID: {club_id}): {player_count} players - {status}"
                    )
        else:
            print("\n⚠️  No explicit NSFT league found. Checking for League ID 3...")

            # Check League ID 3 (which was common in our data)
            local_cursor.execute(
                "SELECT id, league_id, league_name FROM leagues WHERE id = 3"
            )
            league_3 = local_cursor.fetchone()

            if league_3:
                print(f"  • League 3: {league_3[1]} - {league_3[2]}")

                # Get clubs associated with League 3
                local_cursor.execute(
                    """
                    SELECT c.id, c.name, COUNT(p.id) as player_count
                    FROM players p
                    JOIN clubs c ON p.club_id = c.id
                    WHERE p.league_id = 3
                    GROUP BY c.id, c.name
                    ORDER BY player_count DESC
                """
                )

                clubs_in_league_3 = local_cursor.fetchall()
                print(f"    Clubs in League 3:")
                total_missing = 0
                total_mapped = 0

                for club_id, club_name, player_count in clubs_in_league_3:
                    if club_id in [94, 91, 10, 93, 45, 44, 92, 97, 26, 47, 48, 27]:
                        status = "❌ MISSING"
                        total_missing += player_count
                    else:
                        status = "✅ MAPPED"
                        total_mapped += player_count
                    print(
                        f"      • {club_name} (ID: {club_id}): {player_count} players - {status}"
                    )

                print(f"\n📊 LEAGUE 3 SUMMARY:")
                print(f"  • Missing clubs: {total_missing} players")
                print(f"  • Mapped clubs: {total_mapped} players")
                print(
                    f"  • Missing percentage: {(total_missing / (total_missing + total_mapped) * 100):.1f}%"
                )


def cross_reference_with_railway():
    """Cross-reference missing patterns with Railway data"""
    logger.info("🔄 Cross-referencing with Railway...")

    with get_db() as local_conn:
        railway_conn = connect_to_railway()

        local_cursor = local_conn.cursor()
        railway_cursor = railway_conn.cursor()

        print("\n" + "=" * 80)
        print("🔄 RAILWAY CROSS-REFERENCE")
        print("=" * 80)

        # Check what Series 2B equivalent exists in Railway
        railway_cursor.execute(
            "SELECT id, name FROM series WHERE name ILIKE '%2B%' ORDER BY name"
        )
        railway_series_2b = railway_cursor.fetchall()

        print(f"\nRAILWAY SERIES 2B MATCHES:")
        if railway_series_2b:
            for series_id, series_name in railway_series_2b:
                print(f"  • Series {series_id}: {series_name}")
        else:
            print("  ⚠️  No Series 2B found in Railway")

        # Check Railway league distribution
        railway_cursor.execute(
            """
            SELECT p.league_id, l.league_name, COUNT(DISTINCT p.club_id) as club_count, COUNT(p.id) as player_count
            FROM players p
            LEFT JOIN leagues l ON p.league_id = l.id
            GROUP BY p.league_id, l.league_name
            ORDER BY player_count DESC
        """
        )

        railway_league_dist = railway_cursor.fetchall()

        print(f"\nRAILWAY LEAGUE DISTRIBUTION:")
        for league_id, league_name, club_count, player_count in railway_league_dist:
            print(
                f"  • League {league_id} ({league_name}): {club_count} clubs, {player_count} players"
            )

        railway_conn.close()


def main():
    """Main investigation function"""
    logger.info("🔍 INVESTIGATING MISSING CLUBS LEAGUE PATTERN")
    logger.info("=" * 80)

    # Step 1: Analyze leagues
    local_leagues, railway_leagues = analyze_leagues()

    # Step 2: Analyze missing clubs by league
    club_league_data = analyze_missing_clubs_by_league()

    # Step 3: Investigate Series 2B pattern
    analyze_series_2b_pattern()

    # Step 4: Investigate NSFT league pattern
    analyze_nsft_league_pattern()

    # Step 5: Cross-reference with Railway
    cross_reference_with_railway()

    print("\n" + "=" * 80)
    print("🎯 INVESTIGATION COMPLETE")
    print("=" * 80)
    print("Review the analysis above to confirm if missing clubs are")
    print("predominantly Series 2B / NSFT league related.")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
