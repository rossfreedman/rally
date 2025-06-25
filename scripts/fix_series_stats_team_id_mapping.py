#!/usr/bin/env python3
"""
Fix series_stats team_id mapping with comprehensive pattern matching

This script handles various naming conventions between series_stats and teams tables:
- "Tennaqua 10" + "Division 10" -> "Tennaqua - 10 (Division 10)" + "Division 10"
- Standard team name variations
- Excludes BYE teams and other invalid entries
"""

import os
import sys
import re

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from database_utils import execute_query, execute_query_one


def clean_bye_teams():
    """Remove BYE teams from series_stats as they're not real teams"""
    print("🧹 Cleaning BYE teams from series_stats...")
    
    bye_count = execute_query_one("SELECT COUNT(*) as count FROM series_stats WHERE team LIKE 'BYE%'")["count"]
    if bye_count > 0:
        execute_query("DELETE FROM series_stats WHERE team LIKE 'BYE%'")
        print(f"   ✅ Removed {bye_count} BYE team records")
    else:
        print("   ✅ No BYE teams to remove")


def find_team_match(stats_team_name, stats_series_name, league_id):
    """Find matching team using various pattern matching strategies"""
    
    # Strategy 1: Exact match
    exact_match = execute_query_one("""
        SELECT t.id 
        FROM teams t
        JOIN series s ON t.series_id = s.id
        WHERE t.team_name = %s AND s.name = %s AND t.league_id = %s
    """, [stats_team_name, stats_series_name, league_id])
    
    if exact_match:
        return exact_match["id"]
    
    # Strategy 2: Handle Tennaqua naming patterns
    # "Tennaqua 10" + "Division 10" -> "Tennaqua - 10 (Division 10)" + "Division 10"
    if stats_team_name.startswith("Tennaqua ") and stats_series_name.startswith("Division "):
        division_num = stats_series_name.replace("Division ", "")
        expected_team_name = f"Tennaqua - {division_num} (Division {division_num})"
        
        tennaqua_match = execute_query_one("""
            SELECT t.id 
            FROM teams t
            JOIN series s ON t.series_id = s.id
            WHERE t.team_name = %s AND s.name = %s AND t.league_id = %s
        """, [expected_team_name, stats_series_name, league_id])
        
        if tennaqua_match:
            return tennaqua_match["id"]
    
    # Strategy 3: Handle standard club naming patterns
    # "ClubName 12" + "Division 12" -> "ClubName - 12" + "Chicago 12"
    match = re.match(r"^(.+?)\s+(\d+)$", stats_team_name)
    if match and stats_series_name.startswith("Division "):
        club_name = match.group(1)
        number = match.group(2)
        
        # Try with dash format and Chicago series
        alt_team_name = f"{club_name} - {number}"
        alt_series_name = f"Chicago {number}"
        
        alt_match = execute_query_one("""
            SELECT t.id 
            FROM teams t
            JOIN series s ON t.series_id = s.id
            WHERE t.team_name = %s AND s.name = %s AND t.league_id = %s
        """, [alt_team_name, alt_series_name, league_id])
        
        if alt_match:
            return alt_match["id"]
    
    # Strategy 4: Handle dash variations
    # "Team - 12" <-> "Team 12"
    alternate_patterns = [
        stats_team_name.replace(" - ", " "),  # "Team - 12" -> "Team 12"
        stats_team_name.replace(" ", " - "),  # "Team 12" -> "Team - 12"
    ]
    
    for alt_name in alternate_patterns:
        if alt_name != stats_team_name:
            alt_match = execute_query_one("""
                SELECT t.id 
                FROM teams t
                JOIN series s ON t.series_id = s.id
                WHERE t.team_name = %s AND s.name = %s AND t.league_id = %s
            """, [alt_name, stats_series_name, league_id])
            
            if alt_match:
                return alt_match["id"]
    
    return None


def populate_team_ids():
    """Populate missing team_id values using comprehensive pattern matching"""
    print("🔄 Populating missing team_id values with advanced pattern matching...")

    # Get all series_stats records without team_id (excluding BYE teams)
    missing_team_ids = execute_query("""
        SELECT id, team, series, league_id 
        FROM series_stats 
        WHERE team_id IS NULL AND team NOT LIKE 'BYE%'
        ORDER BY league_id, series, team
    """)

    print(f"   Found {len(missing_team_ids)} records missing team_id")

    updated_count = 0
    not_found_count = 0
    not_found_teams = []

    for record in missing_team_ids:
        stats_id = record["id"]
        team_name = record["team"]
        series_name = record["series"]
        league_id = record["league_id"]

        # Find matching team using comprehensive strategies
        team_id = find_team_match(team_name, series_name, league_id)

        if team_id:
            # Update series_stats with team_id
            execute_query("""
                UPDATE series_stats 
                SET team_id = %s 
                WHERE id = %s
            """, [team_id, stats_id])
            updated_count += 1
            
            if updated_count % 50 == 0:
                print(f"   ✅ Updated {updated_count} records...")
        else:
            not_found_count += 1
            not_found_teams.append(f"{team_name} | {series_name} (League {league_id})")

    print(f"   ✅ Updated {updated_count} records with team_id")
    print(f"   ⚠️  {not_found_count} records could not be matched")
    
    # Show first 10 unmatched for debugging
    if not_found_teams:
        print("   First 10 unmatched teams:")
        for team in not_found_teams[:10]:
            print(f"     {team}")

    return updated_count


def verify_tennaqua_coverage():
    """Verify Tennaqua team coverage specifically"""
    print("\n🔍 Verifying Tennaqua team coverage...")
    
    tennaqua_stats = execute_query_one("""
        SELECT 
            COUNT(*) as total,
            COUNT(team_id) as with_team_id
        FROM series_stats 
        WHERE team LIKE '%Tennaqua%'
    """)
    
    total = tennaqua_stats["total"]
    with_id = tennaqua_stats["with_team_id"]
    missing = total - with_id
    
    print(f"   Tennaqua teams - Total: {total}, With team_id: {with_id}, Missing: {missing}")
    print(f"   Coverage: {(with_id/total*100):.1f}%")
    
    if missing > 0:
        print("   Remaining unmatched Tennaqua teams:")
        unmatched = execute_query("""
            SELECT team, series FROM series_stats 
            WHERE team LIKE '%Tennaqua%' AND team_id IS NULL 
            LIMIT 5
        """)
        for team in unmatched:
            print(f"     {team['team']} | {team['series']}")


def verify_overall_coverage():
    """Verify overall team_id coverage"""
    print("\n📊 Overall coverage verification...")
    
    stats = execute_query_one("""
        SELECT 
            COUNT(*) as total,
            COUNT(team_id) as with_team_id
        FROM series_stats
        WHERE team NOT LIKE 'BYE%'
    """)
    
    total = stats["total"]
    with_id = stats["with_team_id"]
    missing = total - with_id
    
    print(f"   Total series_stats records (excluding BYE): {total}")
    print(f"   Records with team_id: {with_id}")
    print(f"   Records missing team_id: {missing}")
    print(f"   Coverage: {(with_id/total*100):.1f}%")
    
    if missing == 0:
        print("   🎉 Perfect coverage achieved!")
    elif missing < 50:
        print("   ✅ Excellent coverage - minor gaps remaining")
    else:
        print("   ⚠️  Significant gaps remain - may need further investigation")


def main():
    """Main execution"""
    print("🚀 Starting comprehensive series_stats team_id mapping...")
    print("=" * 70)

    try:
        # Step 1: Clean BYE teams
        clean_bye_teams()

        # Step 2: Populate missing team_ids with advanced matching
        updated_count = populate_team_ids()

        # Step 3: Verify Tennaqua coverage specifically
        verify_tennaqua_coverage()

        # Step 4: Verify overall coverage
        verify_overall_coverage()

        print(f"\n✅ Team ID mapping completed! Updated {updated_count} records.")
        return True

    except Exception as e:
        print(f"\n❌ Error during team_id mapping: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 