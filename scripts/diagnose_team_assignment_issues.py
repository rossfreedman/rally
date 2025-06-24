#!/usr/bin/env python3
"""
Comprehensive Team Assignment Issues Diagnostic

This script identifies all players who may be affected by team assignment
issues similar to Rob Werman's case, where their assigned team doesn't
match their actual match participation.
"""

import sys
import os
from collections import defaultdict

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db
from database_utils import execute_query, execute_query_one

def diagnose_team_assignment_issues():
    """Comprehensive diagnosis of team assignment problems"""
    print("=" * 80)
    print("COMPREHENSIVE TEAM ASSIGNMENT ISSUES DIAGNOSTIC")
    print("=" * 80)
    
    issues = {
        'mismatched_assignments': [],
        'single_player_teams': [],
        'orphaned_teams': [],
        'missing_assignments': [],
        'zero_match_players': [],
        'cross_team_players': []
    }
    
    # 1. Find teams with suspiciously low player counts
    print("1. Checking for teams with very few players...")
    
    low_player_teams_query = """
        SELECT t.id, t.team_name, t.team_alias, l.league_id,
               COUNT(p.id) as player_count,
               c.name as club_name, s.name as series_name
        FROM teams t
        LEFT JOIN players p ON t.id = p.team_id AND p.is_active = TRUE
        LEFT JOIN clubs c ON t.club_id = c.id
        LEFT JOIN series s ON t.series_id = s.id
        LEFT JOIN leagues l ON t.league_id = l.id
        GROUP BY t.id, t.team_name, t.team_alias, l.league_id, c.name, s.name
        HAVING COUNT(p.id) <= 2
        ORDER BY COUNT(p.id), t.team_name
    """
    
    low_player_teams = execute_query(low_player_teams_query)
    
    for team in low_player_teams:
        if team['player_count'] == 0:
            issues['orphaned_teams'].append(team)
        else:
            issues['single_player_teams'].append(team)
    
    print(f"   Found {len(issues['single_player_teams'])} teams with 1-2 players")
    print(f"   Found {len(issues['orphaned_teams'])} teams with 0 players")
    
    # 2. Find players with no team assignment
    print("\n2. Checking for players with missing team assignments...")
    
    missing_assignment_query = """
        SELECT p.id, p.first_name, p.last_name, p.tenniscores_player_id,
               c.name as club_name, s.name as series_name, l.league_id
        FROM players p
        LEFT JOIN clubs c ON p.club_id = c.id
        LEFT JOIN series s ON p.series_id = s.id
        LEFT JOIN leagues l ON p.league_id = l.id
        WHERE p.team_id IS NULL AND p.is_active = TRUE
        ORDER BY c.name, s.name, p.last_name, p.first_name
    """
    
    missing_assignments = execute_query(missing_assignment_query)
    issues['missing_assignments'] = missing_assignments
    
    print(f"   Found {len(missing_assignments)} players with no team assignment")
    
    # 3. Find players whose assigned team doesn't match their match participation
    print("\n3. Checking for players with mismatched team assignments...")
    
    # This is complex - we need to compare assigned team vs actual match teams
    mismatched_query = """
        WITH player_match_teams AS (
            SELECT 
                CASE 
                    WHEN ms.home_player_1_id = p.tenniscores_player_id THEN ms.home_team
                    WHEN ms.home_player_2_id = p.tenniscores_player_id THEN ms.home_team
                    WHEN ms.away_player_1_id = p.tenniscores_player_id THEN ms.away_team
                    WHEN ms.away_player_2_id = p.tenniscores_player_id THEN ms.away_team
                END as match_team,
                p.tenniscores_player_id,
                p.first_name,
                p.last_name,
                t.team_name as assigned_team,
                p.team_id,
                COUNT(*) as match_count
            FROM players p
            LEFT JOIN teams t ON p.team_id = t.id
            JOIN match_scores ms ON (
                ms.home_player_1_id = p.tenniscores_player_id OR
                ms.home_player_2_id = p.tenniscores_player_id OR
                ms.away_player_1_id = p.tenniscores_player_id OR
                ms.away_player_2_id = p.tenniscores_player_id
            )
            WHERE p.is_active = TRUE
            GROUP BY p.tenniscores_player_id, p.first_name, p.last_name, 
                     t.team_name, p.team_id, match_team
        ),
        player_primary_teams AS (
            SELECT 
                tenniscores_player_id,
                first_name,
                last_name,
                assigned_team,
                team_id,
                match_team as primary_match_team,
                match_count,
                ROW_NUMBER() OVER (
                    PARTITION BY tenniscores_player_id 
                    ORDER BY match_count DESC
                ) as rn
            FROM player_match_teams
        )
        SELECT *
        FROM player_primary_teams
        WHERE rn = 1 
        AND assigned_team IS NOT NULL 
        AND assigned_team != primary_match_team
        ORDER BY last_name, first_name
    """
    
    mismatched_players = execute_query(mismatched_query)
    issues['mismatched_assignments'] = mismatched_players
    
    print(f"   Found {len(mismatched_players)} players with mismatched team assignments")
    
    # 4. Find players with 0 matches for their assigned team
    print("\n4. Checking for players with 0 matches for their assigned team...")
    
    zero_match_query = """
        WITH player_match_counts AS (
            SELECT p.id, p.first_name, p.last_name, p.tenniscores_player_id,
                   t.team_name as assigned_team, p.team_id,
                   (
                       SELECT COUNT(*)
                       FROM match_scores ms
                       WHERE (
                           ms.home_player_1_id = p.tenniscores_player_id OR
                           ms.home_player_2_id = p.tenniscores_player_id OR
                           ms.away_player_1_id = p.tenniscores_player_id OR
                           ms.away_player_2_id = p.tenniscores_player_id
                       )
                       AND (ms.home_team = t.team_name OR ms.away_team = t.team_name)
                   ) as matches_for_assigned_team,
                   (
                       SELECT COUNT(*)
                       FROM match_scores ms
                       WHERE (
                           ms.home_player_1_id = p.tenniscores_player_id OR
                           ms.home_player_2_id = p.tenniscores_player_id OR
                           ms.away_player_1_id = p.tenniscores_player_id OR
                           ms.away_player_2_id = p.tenniscores_player_id
                       )
                   ) as total_matches
            FROM players p
            JOIN teams t ON p.team_id = t.id
            WHERE p.is_active = TRUE
        )
        SELECT *
        FROM player_match_counts
        WHERE matches_for_assigned_team = 0 AND total_matches > 0
        ORDER BY total_matches DESC, last_name, first_name
    """
    
    zero_match_players = execute_query(zero_match_query)
    issues['zero_match_players'] = zero_match_players
    
    print(f"   Found {len(zero_match_players)} players with 0 matches for their assigned team (but matches for other teams)")
    
    # 5. Find players playing for multiple teams
    print("\n5. Checking for players playing across multiple teams...")
    
    cross_team_query = """
        WITH player_teams AS (
            SELECT 
                p.tenniscores_player_id,
                p.first_name,
                p.last_name,
                t.team_name as assigned_team,
                CASE 
                    WHEN ms.home_player_1_id = p.tenniscores_player_id THEN ms.home_team
                    WHEN ms.home_player_2_id = p.tenniscores_player_id THEN ms.home_team
                    WHEN ms.away_player_1_id = p.tenniscores_player_id THEN ms.away_team
                    WHEN ms.away_player_2_id = p.tenniscores_player_id THEN ms.away_team
                END as match_team,
                COUNT(*) as match_count
            FROM players p
            LEFT JOIN teams t ON p.team_id = t.id
            JOIN match_scores ms ON (
                ms.home_player_1_id = p.tenniscores_player_id OR
                ms.home_player_2_id = p.tenniscores_player_id OR
                ms.away_player_1_id = p.tenniscores_player_id OR
                ms.away_player_2_id = p.tenniscores_player_id
            )
            WHERE p.is_active = TRUE
            GROUP BY p.tenniscores_player_id, p.first_name, p.last_name, 
                     t.team_name, match_team
        )
        SELECT 
            tenniscores_player_id,
            first_name,
            last_name,
            assigned_team,
            COUNT(DISTINCT match_team) as teams_played_for,
            ARRAY_AGG(DISTINCT match_team ORDER BY match_team) as all_teams,
            SUM(match_count) as total_matches
        FROM player_teams
        GROUP BY tenniscores_player_id, first_name, last_name, assigned_team
        HAVING COUNT(DISTINCT match_team) > 1
        ORDER BY teams_played_for DESC, total_matches DESC
    """
    
    cross_team_players = execute_query(cross_team_query)
    issues['cross_team_players'] = cross_team_players
    
    print(f"   Found {len(cross_team_players)} players who have played for multiple teams")
    
    # Generate detailed report
    print("\n" + "=" * 80)
    print("DETAILED ISSUE REPORT")
    print("=" * 80)
    
    # Report 1: Single/Few Player Teams
    if issues['single_player_teams']:
        print(f"\n🚨 TEAMS WITH VERY FEW PLAYERS ({len(issues['single_player_teams'])} teams)")
        print("-" * 60)
        for team in issues['single_player_teams']:
            print(f"   {team['team_name']} ({team['club_name']} - {team['series_name']})")
            print(f"      Players: {team['player_count']} | League: {team['league_id']}")
            
            # Get the actual players on this team
            players_query = """
                SELECT first_name, last_name, tenniscores_player_id
                FROM players 
                WHERE team_id = %s AND is_active = TRUE
            """
            team_players = execute_query(players_query, [team['id']])
            for player in team_players:
                print(f"      - {player['first_name']} {player['last_name']} ({player['tenniscores_player_id']})")
    
    # Report 2: Orphaned Teams
    if issues['orphaned_teams']:
        print(f"\n🏚️  ORPHANED TEAMS (0 players) ({len(issues['orphaned_teams'])} teams)")
        print("-" * 60)
        for team in issues['orphaned_teams']:
            print(f"   {team['team_name']} ({team['club_name']} - {team['series_name']})")
            print(f"      League: {team['league_id']}")
    
    # Report 3: Missing Team Assignments
    if issues['missing_assignments']:
        print(f"\n❓ PLAYERS WITH NO TEAM ASSIGNMENT ({len(issues['missing_assignments'])} players)")
        print("-" * 60)
        for player in issues['missing_assignments'][:10]:  # Show first 10
            print(f"   {player['first_name']} {player['last_name']}")
            print(f"      Club: {player['club_name']} | Series: {player['series_name']} | League: {player['league_id']}")
        if len(issues['missing_assignments']) > 10:
            print(f"   ... and {len(issues['missing_assignments']) - 10} more")
    
    # Report 4: Mismatched Assignments (like Rob's case)
    if issues['mismatched_assignments']:
        print(f"\n🔀 PLAYERS WITH MISMATCHED TEAM ASSIGNMENTS ({len(issues['mismatched_assignments'])} players)")
        print("-" * 60)
        for player in issues['mismatched_assignments']:
            print(f"   {player['first_name']} {player['last_name']}")
            print(f"      Assigned to: {player['assigned_team']}")
            print(f"      Actually plays for: {player['primary_match_team']} ({player['match_count']} matches)")
    
    # Report 5: Zero Matches for Assigned Team
    if issues['zero_match_players']:
        print(f"\n🚫 PLAYERS WITH 0 MATCHES FOR THEIR ASSIGNED TEAM ({len(issues['zero_match_players'])} players)")
        print("-" * 60)
        for player in issues['zero_match_players'][:10]:  # Show first 10
            print(f"   {player['first_name']} {player['last_name']}")
            print(f"      Assigned to: {player['assigned_team']} (0 matches)")
            print(f"      Total matches for other teams: {player['total_matches']}")
        if len(issues['zero_match_players']) > 10:
            print(f"   ... and {len(issues['zero_match_players']) - 10} more")
    
    # Report 6: Cross-Team Players
    if issues['cross_team_players']:
        print(f"\n🏓 PLAYERS WHO PLAY FOR MULTIPLE TEAMS ({len(issues['cross_team_players'])} players)")
        print("-" * 60)
        for player in issues['cross_team_players'][:10]:  # Show first 10
            print(f"   {player['first_name']} {player['last_name']}")
            print(f"      Assigned to: {player['assigned_team']}")
            print(f"      Plays for {player['teams_played_for']} teams: {', '.join(player['all_teams'])}")
            print(f"      Total matches: {player['total_matches']}")
        if len(issues['cross_team_players']) > 10:
            print(f"   ... and {len(issues['cross_team_players']) - 10} more")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    total_issues = (
        len(issues['single_player_teams']) +
        len(issues['orphaned_teams']) + 
        len(issues['missing_assignments']) +
        len(issues['mismatched_assignments']) +
        len(issues['zero_match_players']) +
        len(issues['cross_team_players'])
    )
    
    print(f"🚨 Total Issues Found: {total_issues}")
    print(f"   - Teams with 1-2 players: {len(issues['single_player_teams'])}")
    print(f"   - Orphaned teams (0 players): {len(issues['orphaned_teams'])}")
    print(f"   - Players with no team: {len(issues['missing_assignments'])}")
    print(f"   - Mismatched assignments: {len(issues['mismatched_assignments'])}")
    print(f"   - Zero matches for assigned team: {len(issues['zero_match_players'])}")
    print(f"   - Cross-team players: {len(issues['cross_team_players'])}")
    
    if total_issues > 0:
        print(f"\n💡 RECOMMENDATIONS:")
        print(f"   1. Focus on mismatched assignments first (like Rob's case)")
        print(f"   2. Review single-player teams - they may need consolidation")
        print(f"   3. Assign teams to players with missing assignments")
        print(f"   4. Consider running team assignment reconciliation")
        print(f"\n🔧 To fix these issues, you can run targeted scripts or the comprehensive fix")
    else:
        print(f"\n✅ No major team assignment issues found!")
    
    print("=" * 80)
    
    return issues

if __name__ == "__main__":
    diagnose_team_assignment_issues() 