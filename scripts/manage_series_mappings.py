#!/usr/bin/env python3

"""
Series Mappings Management Tool

This script helps with:
1. Analyzing series naming patterns for new leagues
2. Adding new series mappings
3. Managing existing mappings

Usage:
    python scripts/manage_series_mappings.py analyze LEAGUE_ID
    python scripts/manage_series_mappings.py add LEAGUE_ID "User Series" "DB Series"
    python scripts/manage_series_mappings.py list LEAGUE_ID
    python scripts/manage_series_mappings.py auto-add LEAGUE_ID
"""

import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re

from database_utils import execute_query, execute_query_one
from utils.series_mapping_service import get_series_mapper


def analyze_league_patterns(league_id):
    """Analyze series naming patterns for a league"""
    print(f"🔍 ANALYZING SERIES PATTERNS FOR {league_id}")
    print("=" * 60)

    mapper = get_series_mapper()
    patterns = mapper.auto_detect_mapping_pattern(league_id)

    if "error" in patterns:
        print(f"❌ Error: {patterns['error']}")
        return

    print(f"📊 Found {patterns['series_count']} series in {league_id}")
    print(f"\n📋 Naming Patterns:")
    for pattern in patterns["naming_patterns"]:
        print(f"  - {pattern}")

    # Check for existing mappings
    existing_mappings = mapper.get_all_mappings_for_league(league_id)
    print(f"\n🗂️  Existing Mappings ({len(existing_mappings)}):")
    if existing_mappings:
        for mapping in existing_mappings:
            print(
                f"  '{mapping['user_series_name']}' -> '{mapping['database_series_name']}'"
            )
    else:
        print("  No existing mappings found")

    # Suggest potential mappings based on patterns
    print(f"\n💡 Mapping Suggestions:")
    suggest_mappings_for_league(league_id)


def suggest_mappings_for_league(league_id):
    """Suggest potential series mappings based on common patterns"""

    # Get all series names for the league
    query = """
        SELECT DISTINCT s.name as series_name
        FROM series s
        JOIN series_leagues sl ON s.id = sl.series_id
        JOIN leagues l ON sl.league_id = l.id
        WHERE l.league_id = %s
        ORDER BY s.name
    """

    try:
        series_data = execute_query(query, [league_id])

        for series in series_data:
            name = series["series_name"]
            suggestions = []

            # Pattern-based suggestions
            if re.match(r"^S\d+[A-Z]*$", name):  # S1, S2A, S2B
                # Suggest long form
                if name.startswith("S") and len(name) > 1:
                    long_form = f"Series {name[1:]}"
                    suggestions.append(long_form)

            elif re.match(r"^Series \d+[A-Z]*$", name):  # Series 1, Series 2A
                # Suggest short form
                short_form = f"S{name.replace('Series ', '')}"
                suggestions.append(short_form)
                # Suggest division form
                division_form = f"Division {name.replace('Series ', '')}"
                suggestions.append(division_form)

            elif re.match(r"^Division \d+[A-Z]*$", name):  # Division 1, Division 2A
                # Suggest series form
                series_form = f"Series {name.replace('Division ', '')}"
                suggestions.append(series_form)

            elif re.match(r"^Chicago \d+", name):  # Chicago 30, Chicago 4.0
                # These might not need mapping
                suggestions.append("Likely no mapping needed")

            if suggestions:
                print(f"  '{name}' <- potential user formats: {', '.join(suggestions)}")

    except Exception as e:
        print(f"❌ Error getting series data: {e}")


def add_mapping(league_id, user_series, db_series):
    """Add a new series mapping"""
    print(f"➕ ADDING MAPPING FOR {league_id}")
    print(f"   '{user_series}' -> '{db_series}'")

    mapper = get_series_mapper()
    success = mapper.add_mapping(league_id, user_series, db_series)

    if success:
        print("✅ Mapping added successfully")
    else:
        print("❌ Failed to add mapping")


def list_mappings(league_id):
    """List all mappings for a league"""
    print(f"📋 SERIES MAPPINGS FOR {league_id}")
    print("=" * 60)

    mapper = get_series_mapper()
    mappings = mapper.get_all_mappings_for_league(league_id)

    if not mappings:
        print("No mappings found for this league")
        return

    print(f"Found {len(mappings)} mappings:")
    for mapping in mappings:
        created = (
            mapping["created_at"].strftime("%Y-%m-%d")
            if mapping["created_at"]
            else "Unknown"
        )
        print(
            f"  '{mapping['user_series_name']}' -> '{mapping['database_series_name']}' (added: {created})"
        )


def auto_add_common_mappings(league_id):
    """Automatically add common mappings based on detected patterns"""
    print(f"🤖 AUTO-ADDING COMMON MAPPINGS FOR {league_id}")
    print("=" * 60)

    # Get all series names for the league
    query = """
        SELECT DISTINCT s.name as series_name
        FROM series s
        JOIN series_leagues sl ON s.id = sl.series_id
        JOIN leagues l ON sl.league_id = l.id
        WHERE l.league_id = %s
        ORDER BY s.name
    """

    try:
        series_data = execute_query(query, [league_id])
        mapper = get_series_mapper()
        added_count = 0

        for series in series_data:
            name = series["series_name"]

            # Auto-add based on common patterns
            if re.match(r"^S\d+[A-Z]*$", name) and len(name) > 1:
                # S1 -> Series 1, S2A -> Series 2A
                long_form = f"Series {name[1:]}"
                if mapper.add_mapping(league_id, long_form, name):
                    added_count += 1
                    print(f"  ✅ Added: '{long_form}' -> '{name}'")

            elif re.match(r"^Series \d+[A-Z]*$", name):
                # Series 1 -> S1, Series 2A -> S2A
                suffix = name.replace("Series ", "")
                short_form = f"S{suffix}"
                if mapper.add_mapping(league_id, name, name):  # Identity mapping
                    pass  # Don't count identity mappings
                # Also add division mapping
                division_form = f"Division {suffix}"
                if mapper.add_mapping(league_id, division_form, name):
                    added_count += 1
                    print(f"  ✅ Added: '{division_form}' -> '{name}'")

        print(f"\n🎉 Auto-added {added_count} mappings for {league_id}")

    except Exception as e:
        print(f"❌ Error in auto-add: {e}")


def show_usage():
    """Show usage information"""
    print("Series Mappings Management Tool")
    print("=" * 40)
    print("Usage:")
    print("  python scripts/manage_series_mappings.py analyze LEAGUE_ID")
    print(
        "  python scripts/manage_series_mappings.py add LEAGUE_ID 'User Series' 'DB Series'"
    )
    print("  python scripts/manage_series_mappings.py list LEAGUE_ID")
    print("  python scripts/manage_series_mappings.py auto-add LEAGUE_ID")
    print("")
    print("Examples:")
    print("  python scripts/manage_series_mappings.py analyze CITA")
    print("  python scripts/manage_series_mappings.py add NSTF 'Series 2B' 'S2B'")
    print("  python scripts/manage_series_mappings.py list CNSWPL")
    print("  python scripts/manage_series_mappings.py auto-add CITA")


def main():
    if len(sys.argv) < 2:
        show_usage()
        return

    command = sys.argv[1].lower()

    if command == "analyze":
        if len(sys.argv) != 3:
            print("Usage: analyze LEAGUE_ID")
            return
        analyze_league_patterns(sys.argv[2])

    elif command == "add":
        if len(sys.argv) != 5:
            print("Usage: add LEAGUE_ID 'User Series' 'DB Series'")
            return
        add_mapping(sys.argv[2], sys.argv[3], sys.argv[4])

    elif command == "list":
        if len(sys.argv) != 3:
            print("Usage: list LEAGUE_ID")
            return
        list_mappings(sys.argv[2])

    elif command == "auto-add":
        if len(sys.argv) != 3:
            print("Usage: auto-add LEAGUE_ID")
            return
        auto_add_common_mappings(sys.argv[2])

    else:
        print(f"Unknown command: {command}")
        show_usage()


if __name__ == "__main__":
    main()
