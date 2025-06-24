#!/usr/bin/env python3
"""
Fix Team Mapping Crisis

This script addresses the root cause of team assignment issues:
missing team_format_mappings between match data team names and teams table names.

The script will:
1. Identify teams in match data that don't exist in teams table
2. Find potential mappings to existing teams
3. Create team_format_mappings entries to resolve the crisis
4. Validate the fix by re-running team assignments
"""

import sys
import os
from collections import defaultdict

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db
from database_utils import execute_query, execute_query_one

def analyze_missing_teams():
    """Identify teams in match data that don't exist in teams table"""
    print("=" * 80)
    print("ANALYZING MISSING TEAM MAPPINGS")
    print("=" * 80)
    
    # Get teams from match data that don't exist in teams table
    missing_teams_query = """
        WITH match_teams AS (
            SELECT home_team as team_name, COUNT(*) as home_matches FROM match_scores GROUP BY home_team
            UNION ALL
            SELECT away_team as team_name, COUNT(*) as away_matches FROM match_scores GROUP BY away_team
        ),
        team_usage AS (
            SELECT team_name, SUM(home_matches) as total_matches FROM match_teams GROUP BY team_name
        ),
        existing_teams AS (
            SELECT DISTINCT team_name FROM teams
        ),
        existing_mappings AS (
            SELECT DISTINCT user_input_format FROM team_format_mappings WHERE is_active = TRUE
        )
        SELECT 
            tu.team_name as missing_team,
            tu.total_matches
        FROM team_usage tu
        WHERE tu.team_name NOT IN (SELECT team_name FROM existing_teams)
        AND tu.team_name NOT IN (SELECT user_input_format FROM existing_mappings)
        ORDER BY tu.total_matches DESC
    """
    
    missing_teams = execute_query(missing_teams_query)
    
    print(f"Found {len(missing_teams)} teams in match data with no team record or mapping:")
    print("-" * 60)
    
    for i, team in enumerate(missing_teams[:15]):
        print(f"  {i+1:2d}. {team['missing_team']:<35} ({team['total_matches']:>4} matches)")
    
    if len(missing_teams) > 15:
        print(f"  ... and {len(missing_teams) - 15} more teams")
    
    return missing_teams

def find_potential_mappings(missing_teams):
    """Find potential mappings for missing teams based on similar names"""
    print(f"\n" + "=" * 80)
    print("FINDING POTENTIAL TEAM MAPPINGS")
    print("=" * 80)
    
    # Get all existing team names for fuzzy matching
    existing_teams_query = "SELECT DISTINCT team_name FROM teams ORDER BY team_name"
    existing_teams = [row['team_name'] for row in execute_query(existing_teams_query)]
    
    potential_mappings = []
    
    for missing_team in missing_teams:
        missing_name = missing_team['missing_team']
        match_count = missing_team['total_matches']
        
        # Look for similar team names
        candidates = []
        
        for existing_name in existing_teams:
            # Check for patterns like:
            # "Wilmette 16b" -> "Wilmette 16a"
            # "Lifesport - Libertyville" -> "Lifesport-Lshire"
            # "Glenbrook Racquet Club" -> "Glenbrook RC"
            
            similarity_score = calculate_team_similarity(missing_name, existing_name)
            
            if similarity_score > 0.6:  # 60% similarity threshold
                candidates.append({
                    'existing_team': existing_name,
                    'similarity': similarity_score,
                    'missing_team': missing_name,
                    'match_count': match_count
                })
        
        # Sort by highest similarity
        candidates.sort(key=lambda x: x['similarity'], reverse=True)
        
        if candidates:
            best_match = candidates[0]
            potential_mappings.append(best_match)
            
            print(f"  {missing_name:<35} -> {best_match['existing_team']:<35} ({best_match['similarity']:.1%} similar, {match_count} matches)")
        else:
            print(f"  {missing_name:<35} -> ❌ NO MATCH FOUND ({match_count} matches)")
    
    return potential_mappings

def calculate_team_similarity(name1, name2):
    """Calculate similarity between team names using multiple heuristics"""
    name1_lower = name1.lower()
    name2_lower = name2.lower()
    
    # Exact match
    if name1_lower == name2_lower:
        return 1.0
    
    # Check for common patterns
    score = 0.0
    
    # Club name similarity (extract main club name)
    club1 = extract_club_name(name1_lower)
    club2 = extract_club_name(name2_lower)
    
    if club1 and club2:
        if club1 == club2:
            score += 0.7  # Same club
        elif club1 in club2 or club2 in club1:
            score += 0.5  # Partial club match
    
    # Division/number similarity
    num1 = extract_team_number(name1_lower)
    num2 = extract_team_number(name2_lower)
    
    if num1 and num2:
        if num1 == num2:
            score += 0.3  # Same number/division
        elif abs(int(num1) - int(num2)) <= 1:
            score += 0.1  # Adjacent numbers
    
    # Check for "a" vs "b" pattern (16a vs 16b)
    if name1_lower.replace('b', 'a') == name2_lower or name2_lower.replace('b', 'a') == name1_lower:
        score += 0.8
    
    return min(score, 1.0)

def extract_club_name(team_name):
    """Extract main club name from team name"""
    # Remove common suffixes and numbers
    import re
    
    # Common patterns to remove
    patterns = [
        r'\s*-?\s*\d+[ab]?$',  # Remove trailing numbers/divisions
        r'\s*pd\s*(i|ii)?\s*-?\s*\d*$',  # Remove PD divisions
        r'\s*s\d+[ab]?$',  # Remove S1, S2A patterns
        r'\s*division\s*\d+$',  # Remove "Division X"
        r'\s*\([^)]+\)$',  # Remove parenthetical
    ]
    
    clean_name = team_name.lower()
    for pattern in patterns:
        clean_name = re.sub(pattern, '', clean_name, flags=re.IGNORECASE)
    
    return clean_name.strip()

def extract_team_number(team_name):
    """Extract team number/division from team name"""
    import re
    
    # Look for numbers at the end
    match = re.search(r'(\d+)[ab]?$', team_name)
    if match:
        return match.group(1)
    
    return None

def create_team_mappings(potential_mappings, league_id="APTA_CHICAGO"):
    """Create team_format_mappings entries for the potential mappings"""
    print(f"\n" + "=" * 80)
    print("CREATING TEAM FORMAT MAPPINGS")
    print("=" * 80)
    
    if not potential_mappings:
        print("No potential mappings found to create.")
        return 0
    
    print(f"Ready to create {len(potential_mappings)} team format mappings...")
    print(f"Using league_id: {league_id}")
    print()
    
    # Show preview
    print("Preview of mappings to create:")
    for i, mapping in enumerate(potential_mappings[:10]):
        print(f"  {i+1}. {mapping['missing_team']} -> {mapping['existing_team']} ({mapping['similarity']:.1%})")
    
    if len(potential_mappings) > 10:
        print(f"  ... and {len(potential_mappings) - 10} more")
    
    response = input(f"\nProceed with creating {len(potential_mappings)} mappings? (yes/no): ").lower().strip()
    
    if response not in ['yes', 'y']:
        print("❌ Cancelled - no mappings created.")
        return 0
    
    created_count = 0
    
    for mapping in potential_mappings:
        try:
            # Create mapping entry
            insert_query = """
                INSERT INTO team_format_mappings 
                (league_id, user_input_format, database_series_format, mapping_type, description, is_active)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (league_id, user_input_format) DO UPDATE SET
                database_series_format = EXCLUDED.database_series_format,
                description = EXCLUDED.description,
                updated_at = CURRENT_TIMESTAMP
            """
            
            description = f"Auto-mapped: {mapping['similarity']:.1%} similarity, {mapping['match_count']} matches"
            
            execute_query(insert_query, [
                league_id,
                mapping['missing_team'],
                mapping['existing_team'],
                'team_mapping',
                description,
                True
            ])
            
            print(f"  ✅ Created: {mapping['missing_team']} -> {mapping['existing_team']}")
            created_count += 1
            
        except Exception as e:
            print(f"  ❌ Failed: {mapping['missing_team']} - {e}")
    
    print(f"\n🎉 Successfully created {created_count} team format mappings!")
    return created_count

def test_mappings_effectiveness():
    """Test how many team assignment issues the new mappings resolve"""
    print(f"\n" + "=" * 80)
    print("TESTING MAPPING EFFECTIVENESS")
    print("=" * 80)
    
    # Create an updated team assignment function that uses mappings
    test_query = """
        WITH mapped_teams AS (
            SELECT 
                CASE 
                    WHEN ms.home_player_1_id = p.tenniscores_player_id THEN 
                        COALESCE(tfm.database_series_format, ms.home_team)
                    WHEN ms.home_player_2_id = p.tenniscores_player_id THEN 
                        COALESCE(tfm.database_series_format, ms.home_team)
                    WHEN ms.away_player_1_id = p.tenniscores_player_id THEN 
                        COALESCE(tfm_away.database_series_format, ms.away_team)
                    WHEN ms.away_player_2_id = p.tenniscores_player_id THEN 
                        COALESCE(tfm_away.database_series_format, ms.away_team)
                END as mapped_team,
                p.tenniscores_player_id,
                p.first_name || ' ' || p.last_name as player_name,
                t.team_name as current_team,
                COUNT(*) as match_count
            FROM players p
            LEFT JOIN teams t ON p.team_id = t.id
            JOIN match_scores ms ON (
                ms.home_player_1_id = p.tenniscores_player_id OR
                ms.home_player_2_id = p.tenniscores_player_id OR
                ms.away_player_1_id = p.tenniscores_player_id OR
                ms.away_player_2_id = p.tenniscores_player_id
            )
            LEFT JOIN team_format_mappings tfm ON tfm.user_input_format = ms.home_team AND tfm.is_active = TRUE
            LEFT JOIN team_format_mappings tfm_away ON tfm_away.user_input_format = ms.away_team AND tfm_away.is_active = TRUE
            WHERE p.is_active = TRUE
            GROUP BY p.tenniscores_player_id, player_name, current_team, mapped_team
        ),
        resolvable_assignments AS (
            SELECT 
                mt.tenniscores_player_id,
                mt.player_name,
                mt.current_team,
                mt.mapped_team,
                mt.match_count,
                teams.id as target_team_id,
                ROW_NUMBER() OVER (
                    PARTITION BY mt.tenniscores_player_id 
                    ORDER BY mt.match_count DESC
                ) as team_rank
            FROM mapped_teams mt
            JOIN teams ON teams.team_name = mt.mapped_team
        )
        SELECT COUNT(*) as resolvable_count
        FROM resolvable_assignments
        WHERE team_rank = 1 
        AND (current_team IS NULL OR current_team != mapped_team)
    """
    
    result = execute_query_one(test_query)
    resolvable_count = result['resolvable_count'] if result else 0
    
    print(f"📊 Team Assignment Resolvability Test:")
    print(f"   Players with resolvable team assignments: {resolvable_count}")
    
    return resolvable_count

def main():
    """Execute the complete team mapping fix"""
    print("🔧 TEAM MAPPING CRISIS FIX")
    print("This script fixes the root cause of team assignment issues\n")
    
    # Step 1: Analyze missing teams
    missing_teams = analyze_missing_teams()
    
    if not missing_teams:
        print("✅ No missing teams found - all team names are properly mapped!")
        return
    
    # Step 2: Find potential mappings
    potential_mappings = find_potential_mappings(missing_teams)
    
    if not potential_mappings:
        print("❌ No potential mappings found - teams may need to be created manually")
        return
    
    # Step 3: Create mappings
    created_count = create_team_mappings(potential_mappings)
    
    if created_count > 0:
        # Step 4: Test effectiveness
        resolvable_count = test_mappings_effectiveness()
        
        print(f"\n🎉 TEAM MAPPING FIX COMPLETE!")
        print(f"   Created {created_count} team format mappings")
        print(f"   {resolvable_count} player assignments now resolvable")
        print(f"   Re-run team assignment tools to apply the fixes")
    
    print(f"\n📋 Next Steps:")
    print(f"   1. Run: python scripts/validate_etl_results.py --fix-high-confidence")
    print(f"   2. Run: python scripts/test_etl_team_assignment_system.py")
    print(f"   3. Check Rob Werman's track-byes-courts page")

if __name__ == "__main__":
    main() 