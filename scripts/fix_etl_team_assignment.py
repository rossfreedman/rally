#!/usr/bin/env python3
"""
Fix ETL Team Assignment Logic

This script identifies and fixes the root cause of missing team_id assignments
in the ETL process, specifically the series name mismatch issue.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one

def analyze_team_assignment_issues():
    """Analyze current team assignment issues"""
    print("🔍 Analyzing Team Assignment Issues")
    print("=" * 60)
    
    # Find players with missing team_id
    missing_team_query = """
        SELECT 
            p.tenniscores_player_id,
            p.first_name,
            p.last_name,
            p.club_id,
            p.series_id,
            p.league_id,
            c.name as club_name,
            s.name as series_name,
            l.league_name,
            t.id as team_id,
            t.team_name,
            t.team_alias
        FROM players p
        LEFT JOIN clubs c ON p.club_id = c.id
        LEFT JOIN series s ON p.series_id = s.id
        LEFT JOIN leagues l ON p.league_id = l.id
        LEFT JOIN teams t ON p.team_id = t.id
        WHERE p.team_id IS NULL
        AND p.is_active = TRUE
        ORDER BY l.league_name, c.name, s.name
    """
    
    missing_teams = execute_query(missing_team_query)
    
    print(f"Found {len(missing_teams)} players with missing team_id:")
    print()
    
    for player in missing_teams:
        print(f"Player: {player['first_name']} {player['last_name']} ({player['tenniscores_player_id']})")
        print(f"  Club: {player['club_name']}")
        print(f"  Series: {player['series_name']}")
        print(f"  League: {player['league_name']}")
        print(f"  Current team_id: {player['team_id']}")
        print()
    
    return missing_teams

def find_matching_teams():
    """Find teams that should match players with missing team_id"""
    print("🔍 Finding Matching Teams")
    print("=" * 60)
    
    # Find teams that exist but aren't assigned to players
    matching_query = """
        SELECT 
            p.tenniscores_player_id,
            p.first_name,
            p.last_name,
            p.club_id,
            p.series_id,
            p.league_id,
            c.name as club_name,
            s.name as series_name,
            l.league_name,
            t.id as potential_team_id,
            t.team_name,
            t.team_alias,
            t.series_id as team_series_id,
            ts.name as team_series_name
        FROM players p
        LEFT JOIN clubs c ON p.club_id = c.id
        LEFT JOIN series s ON p.series_id = s.id
        LEFT JOIN leagues l ON p.league_id = l.id
        LEFT JOIN teams t ON (
            t.club_id = p.club_id AND 
            t.league_id = p.league_id
        )
        LEFT JOIN series ts ON t.series_id = ts.id
        WHERE p.team_id IS NULL
        AND p.is_active = TRUE
        AND t.id IS NOT NULL
        ORDER BY l.league_name, c.name, s.name
    """
    
    potential_matches = execute_query(matching_query)
    
    print(f"Found {len(potential_matches)} potential team matches:")
    print()
    
    for match in potential_matches:
        print(f"Player: {match['first_name']} {match['last_name']}")
        print(f"  Player Series: '{match['series_name']}'")
        print(f"  Team Series: '{match['team_series_name']}'")
        print(f"  Team Name: {match['team_name']}")
        print(f"  Team Alias: {match['team_alias']}")
        print(f"  Potential Team ID: {match['potential_team_id']}")
        print()
    
    return potential_matches

def fix_team_assignments():
    """Fix team assignments using improved matching logic"""
    print("🔧 Fixing Team Assignments")
    print("=" * 60)
    
    # Use the same fallback logic as mobile my-team page
    fix_query = """
        UPDATE players 
        SET team_id = t.id, updated_at = CURRENT_TIMESTAMP
        FROM teams t
        JOIN clubs c ON t.club_id = c.id
        JOIN series s ON t.series_id = s.id
        WHERE players.team_id IS NULL
        AND players.is_active = TRUE
        AND players.club_id = t.club_id
        AND players.league_id = t.league_id
        AND (
            -- Match by series name directly
            players.series_id = t.series_id
            OR
            -- Match by team_alias (fallback for NSTF)
            (t.team_alias IS NOT NULL AND t.team_alias = s.name)
            OR
            -- Match by series name variations
            (s.name LIKE 'S%' AND players.series_id IN (
                SELECT id FROM series WHERE name = 'Series ' || SUBSTRING(s.name, 2)
            ))
            OR
            (s.name LIKE 'Series %' AND t.series_id IN (
                SELECT id FROM series WHERE name = 'S' || SUBSTRING(s.name, 8)
            ))
        )
    """
    
    result = execute_query(fix_query)
    print(f"Updated {result} player records with team assignments")
    
    return result

def validate_fixes():
    """Validate that the fixes worked"""
    print("✅ Validating Fixes")
    print("=" * 60)
    
    # Check remaining players without team_id
    remaining_query = """
        SELECT COUNT(*) as count
        FROM players 
        WHERE team_id IS NULL AND is_active = TRUE
    """
    
    remaining = execute_query_one(remaining_query)
    print(f"Players still without team_id: {remaining['count']}")
    
    if remaining['count'] > 0:
        # Show details of remaining issues
        details_query = """
            SELECT 
                p.first_name,
                p.last_name,
                c.name as club,
                s.name as series,
                l.league_name
            FROM players p
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            LEFT JOIN leagues l ON p.league_id = l.id
            WHERE p.team_id IS NULL AND p.is_active = TRUE
            ORDER BY l.league_name, c.name, s.name
        """
        
        details = execute_query(details_query)
        print("\nRemaining players without team assignments:")
        for player in details:
            print(f"  - {player['first_name']} {player['last_name']} ({player['club']} - {player['series']} - {player['league_name']})")
    
    return remaining['count'] == 0

def create_etl_enhancement_patch():
    """Create a patch for the ETL import process"""
    print("📝 Creating ETL Enhancement Patch")
    print("=" * 60)
    
    patch_content = '''
# ETL Enhancement Patch - Fix Team Assignment Logic
# Apply to data/etl/database_import/import_all_jsons_to_database.py

## Problem
The current ETL team assignment logic fails when series names don't match exactly:
- Player series: "Series 2B" 
- Team series: "S2B"
- JOIN fails: t.series_id = s.id returns NULL

## Solution
Replace the problematic JOIN in import_players() around line 2265:

### OLD CODE (problematic):
```sql
LEFT JOIN teams t ON t.club_id = c.id AND t.series_id = s.id AND t.league_id = l.id
```

### NEW CODE (enhanced):
```sql
LEFT JOIN teams t ON (
    t.club_id = c.id AND 
    t.league_id = l.id AND
    (
        -- Direct series match
        t.series_id = s.id
        OR
        -- NSTF fallback: match team_alias to series name
        (t.team_alias IS NOT NULL AND t.team_alias = s.name)
        OR
        -- Series name variations (S2B ↔ Series 2B)
        (s.name LIKE 'S%%' AND t.series_id IN (
            SELECT id FROM series WHERE name = 'Series ' || SUBSTRING(s.name, 2)
        ))
        OR
        (s.name LIKE 'Series %%' AND t.series_id IN (
            SELECT id FROM series WHERE name = 'S' || SUBSTRING(s.name, 8)
        ))
    )
)
```

## Implementation Steps
1. Update the JOIN logic in import_players() method
2. Add validation to ensure team_id is assigned
3. Add logging for failed team assignments
4. Test with NSTF data to verify fixes

## Expected Results
- All players should have team_id assigned during ETL
- Captain messages API will work correctly
- No more "Team ID not found" errors
'''
    
    with open('ETL_TEAM_ASSIGNMENT_PATCH.md', 'w') as f:
        f.write(patch_content)
    
    print("✅ Created ETL_TEAM_ASSIGNMENT_PATCH.md")
    print("   Apply this patch to prevent future team assignment issues")

def main():
    """Main function to run the complete fix process"""
    print("🚀 Starting Team Assignment Fix Process")
    print("=" * 60)
    
    # Step 1: Analyze current issues
    missing_teams = analyze_team_assignment_issues()
    
    if not missing_teams:
        print("✅ No players found with missing team_id - no fixes needed!")
        return
    
    # Step 2: Find potential matches
    potential_matches = find_matching_teams()
    
    # Step 3: Fix assignments
    fixed_count = fix_team_assignments()
    
    # Step 4: Validate fixes
    success = validate_fixes()
    
    # Step 5: Create ETL patch
    create_etl_enhancement_patch()
    
    print("\n🎉 Team Assignment Fix Process Complete!")
    print(f"   Fixed {fixed_count} player records")
    print(f"   Success: {'✅' if success else '❌'}")
    
    if success:
        print("   All players now have team assignments!")
    else:
        print("   Some players still need manual team assignment")

if __name__ == "__main__":
    main() 