#!/usr/bin/env python3
"""
Populate missing team_id values in series_stats table

This script matches series_stats records to teams table based on:
- team name matching
- series name matching 
- league_id matching
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from database_utils import execute_query, execute_query_one


def populate_missing_team_ids():
    """Populate missing team_id values in series_stats table"""
    print("🔄 Populating missing team_id values in series_stats...")

    # Get all series_stats records without team_id
    missing_team_ids = execute_query("""
        SELECT id, team, series, league_id 
        FROM series_stats 
        WHERE team_id IS NULL
        ORDER BY league_id, series, team
    """)

    print(f"   Found {len(missing_team_ids)} records missing team_id")

    updated_count = 0
    not_found_count = 0

    for record in missing_team_ids:
        stats_id = record["id"]
        team_name = record["team"]
        series_name = record["series"]
        league_id = record["league_id"]

        # Try to find matching team in teams table
        # First try exact match
        team_match = execute_query_one("""
            SELECT t.id 
            FROM teams t
            JOIN series s ON t.series_id = s.id
            WHERE t.team_name = %s 
            AND s.name = %s 
            AND t.league_id = %s
        """, [team_name, series_name, league_id])

        if team_match:
            # Update series_stats with team_id
            execute_query("""
                UPDATE series_stats 
                SET team_id = %s 
                WHERE id = %s
            """, [team_match["id"], stats_id])
            updated_count += 1
            if updated_count % 50 == 0:
                print(f"   ✅ Updated {updated_count} records...")
        else:
            # Try fuzzy matching for different naming formats
            # Handle cases like "Tennaqua - 12" vs "Tennaqua 12"
            alternate_patterns = [
                team_name.replace(" - ", " "),  # "Tennaqua - 12" -> "Tennaqua 12"
                team_name.replace(" ", " - "),  # "Tennaqua 12" -> "Tennaqua - 12"
            ]
            
            found = False
            for alt_name in alternate_patterns:
                if alt_name != team_name:
                    team_match = execute_query_one("""
                        SELECT t.id 
                        FROM teams t
                        JOIN series s ON t.series_id = s.id
                        WHERE t.team_name = %s 
                        AND s.name = %s 
                        AND t.league_id = %s
                    """, [alt_name, series_name, league_id])
                    
                    if team_match:
                        execute_query("""
                            UPDATE series_stats 
                            SET team_id = %s 
                            WHERE id = %s
                        """, [team_match["id"], stats_id])
                        updated_count += 1
                        found = True
                        break
            
            if not found:
                not_found_count += 1
                if not_found_count <= 10:  # Show first 10 unmatched
                    print(f"   ⚠️  No team found for: '{team_name}' in series '{series_name}' (league {league_id})")

    print(f"   ✅ Updated {updated_count} records with team_id")
    print(f"   ⚠️  {not_found_count} records could not be matched")

    return updated_count


def verify_team_id_population():
    """Verify the team_id population results"""
    print("\n🔍 Verifying team_id population...")

    stats = execute_query_one("""
        SELECT 
            COUNT(*) as total,
            COUNT(team_id) as with_team_id,
            COUNT(*) - COUNT(team_id) as missing_team_id
        FROM series_stats
    """)

    total = stats["total"]
    with_team_id = stats["with_team_id"]
    missing = stats["missing_team_id"]
    
    print(f"   Total series_stats records: {total}")
    print(f"   Records with team_id: {with_team_id}")
    print(f"   Records missing team_id: {missing}")
    print(f"   Population rate: {(with_team_id/total*100):.1f}%")

    if missing == 0:
        print("   🎉 All series_stats records now have team_id!")
    elif missing < 50:
        print("   ✅ Good coverage - only minor gaps remaining")
    else:
        print("   ⚠️  Significant gaps remain - may need further investigation")


def main():
    """Main execution"""
    print("🚀 Starting series_stats team_id population...")
    print("=" * 60)

    try:
        # Populate missing team_ids
        updated_count = populate_missing_team_ids()

        # Verify results
        verify_team_id_population()

        print(f"\n✅ Team ID population completed! Updated {updated_count} records.")
        return True

    except Exception as e:
        print(f"\n❌ Error during team_id population: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 