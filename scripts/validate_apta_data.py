#!/usr/bin/env python3
"""
Comprehensive APTA_CHICAGO Data Validation Script

This script validates data integrity at each step of the import process
to catch issues early and ensure data consistency.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database_config import get_db

def validate_apta_data():
    """Comprehensive validation of APTA_CHICAGO data."""
    print("🔍 APTA_CHICAGO Data Validation")
    print("=" * 50)
    
    league_id = 4783  # APTA_CHICAGO league ID
    issues_found = []
    
    try:
        with get_db() as db:
            cursor = db.cursor()
            
            # 1. Validate League Exists
            print("1. Validating League...")
            cursor.execute('SELECT id, league_name FROM leagues WHERE id = %s', (league_id,))
            league = cursor.fetchone()
            if league:
                print(f"   ✅ League found: {league[1]} (ID: {league[0]})")
            else:
                issues_found.append("League not found")
                print(f"   ❌ League not found")
            
            # 2. Validate Clubs
            print("\n2. Validating Clubs...")
            cursor.execute('SELECT COUNT(DISTINCT c.id) FROM clubs c JOIN teams t ON c.id = t.club_id WHERE t.league_id = %s', (league_id,))
            club_count = cursor.fetchone()[0]
            print(f"   📊 Total clubs: {club_count}")
            
            if club_count == 0:
                issues_found.append("No clubs found")
                print(f"   ❌ No clubs found")
            else:
                # Check for clubs with missing names
                cursor.execute('''
                    SELECT COUNT(DISTINCT c.id) FROM clubs c 
                    JOIN teams t ON c.id = t.club_id 
                    WHERE t.league_id = %s 
                    AND (c.name IS NULL OR c.name = '')
                ''', (league_id,))
                empty_clubs = cursor.fetchone()[0]
                if empty_clubs > 0:
                    issues_found.append(f"{empty_clubs} clubs with empty names")
                    print(f"   ⚠️  {empty_clubs} clubs with empty names")
                else:
                    print(f"   ✅ All clubs have names")
            
            # 3. Validate Series
            print("\n3. Validating Series...")
            cursor.execute('SELECT COUNT(*) FROM series WHERE league_id = %s', (league_id,))
            series_count = cursor.fetchone()[0]
            print(f"   📊 Total series: {series_count}")
            
            if series_count == 0:
                issues_found.append("No series found")
                print(f"   ❌ No series found")
            else:
                # Check for generic series (only flag truly generic ones like "Series SW")
                cursor.execute('SELECT name FROM series WHERE league_id = %s AND name = %s', 
                             (league_id, 'Series SW'))
                generic_series = cursor.fetchall()
                if generic_series:
                    issues_found.append(f"Generic series found: {[s[0] for s in generic_series]}")
                    print(f"   ❌ Generic series found: {[s[0] for s in generic_series]}")
                else:
                    print(f"   ✅ No generic series found")
                
                # Check SW series
                cursor.execute('SELECT COUNT(*) FROM series WHERE league_id = %s AND name LIKE %s', (league_id, '%SW%'))
                sw_series_count = cursor.fetchone()[0]
                print(f"   📊 SW series: {sw_series_count}")
                
                # Show all series
                cursor.execute('SELECT name FROM series WHERE league_id = %s ORDER BY name', (league_id,))
                all_series = cursor.fetchall()
                print(f"   📋 All series: {[s[0] for s in all_series]}")
            
            # 4. Validate Teams
            print("\n4. Validating Teams...")
            cursor.execute('SELECT COUNT(*) FROM teams WHERE league_id = %s', (league_id,))
            team_count = cursor.fetchone()[0]
            print(f"   📊 Total teams: {team_count}")
            
            if team_count == 0:
                issues_found.append("No teams found")
                print(f"   ❌ No teams found")
            else:
                # Check for teams with missing club/series assignments
                cursor.execute('''
                    SELECT COUNT(*) FROM teams t 
                    WHERE t.league_id = %s 
                    AND (t.club_id IS NULL OR t.series_id IS NULL)
                ''', (league_id,))
                incomplete_teams = cursor.fetchone()[0]
                if incomplete_teams > 0:
                    issues_found.append(f"{incomplete_teams} teams with missing club/series assignments")
                    print(f"   ⚠️  {incomplete_teams} teams with missing club/series assignments")
                else:
                    print(f"   ✅ All teams have club and series assignments")
                
                # Check for duplicate teams (same club + series)
                cursor.execute('''
                    SELECT club_id, series_id, COUNT(*) as count
                    FROM teams 
                    WHERE league_id = %s
                    GROUP BY club_id, series_id
                    HAVING COUNT(*) > 1
                ''', (league_id,))
                duplicates = cursor.fetchall()
                if duplicates:
                    issues_found.append(f"Duplicate teams found: {len(duplicates)} club/series combinations")
                    print(f"   ❌ Duplicate teams found: {len(duplicates)} club/series combinations")
                    for club_id, series_id, count in duplicates:
                        print(f"      Club {club_id}, Series {series_id}: {count} teams")
                else:
                    print(f"   ✅ No duplicate teams found")
            
            # 5. Validate Players
            print("\n5. Validating Players...")
            cursor.execute('SELECT COUNT(*) FROM players WHERE league_id = %s', (league_id,))
            player_count = cursor.fetchone()[0]
            print(f"   📊 Total players: {player_count}")
            
            if player_count == 0:
                issues_found.append("No players found")
                print(f"   ❌ No players found")
            else:
                # Check for players with missing team assignments
                cursor.execute('SELECT COUNT(*) FROM players WHERE league_id = %s AND team_id IS NULL', (league_id,))
                unassigned_players = cursor.fetchone()[0]
                if unassigned_players > 0:
                    issues_found.append(f"{unassigned_players} players without team assignments")
                    print(f"   ⚠️  {unassigned_players} players without team assignments")
                else:
                    print(f"   ✅ All players have team assignments")
                
                # Check for players in generic series (only flag truly generic ones like "Series SW")
                cursor.execute('''
                    SELECT COUNT(*) FROM players p 
                    JOIN series s ON p.series_id = s.id 
                    WHERE p.league_id = %s 
                    AND s.name = %s
                ''', (league_id, 'Series SW'))
                generic_players = cursor.fetchone()[0]
                if generic_players > 0:
                    issues_found.append(f"{generic_players} players in generic series")
                    print(f"   ❌ {generic_players} players in generic series")
                else:
                    print(f"   ✅ No players in generic series")
                
                # Check SW players
                cursor.execute('''
                    SELECT COUNT(*) FROM players p 
                    JOIN series s ON p.series_id = s.id 
                    WHERE p.league_id = %s 
                    AND s.name LIKE %s
                ''', (league_id, '%SW%'))
                sw_players = cursor.fetchone()[0]
                print(f"   📊 SW players: {sw_players}")
            
            # 6. Validate Schedules
            print("\n6. Validating Schedules...")
            cursor.execute('SELECT COUNT(*) FROM schedule WHERE league_id = %s', (league_id,))
            schedule_count = cursor.fetchone()[0]
            print(f"   📊 Total schedules: {schedule_count}")
            
            if schedule_count == 0:
                print(f"   ℹ️  No schedules found (may not be imported yet)")
            else:
                # Check for schedules with missing team assignments
                cursor.execute('''
                    SELECT COUNT(*) FROM schedule s 
                    WHERE s.league_id = %s 
                    AND (s.home_team_id IS NULL OR s.away_team_id IS NULL)
                ''', (league_id,))
                incomplete_schedules = cursor.fetchone()[0]
                if incomplete_schedules > 0:
                    issues_found.append(f"{incomplete_schedules} schedules with missing team assignments")
                    print(f"   ⚠️  {incomplete_schedules} schedules with missing team assignments")
                else:
                    print(f"   ✅ All schedules have team assignments")
                
                # Check for self-matches
                cursor.execute('''
                    SELECT COUNT(*) FROM schedule s 
                    WHERE s.league_id = %s 
                    AND s.home_team_id = s.away_team_id
                ''', (league_id,))
                self_matches = cursor.fetchone()[0]
                if self_matches > 0:
                    issues_found.append(f"{self_matches} self-matches found")
                    print(f"   ⚠️  {self_matches} self-matches found")
                else:
                    print(f"   ✅ No self-matches found")
            
            # 7. Data Consistency Checks
            print("\n7. Data Consistency Checks...")
            
            # Check if all players have valid team references
            cursor.execute('''
                SELECT COUNT(*) FROM players p 
                LEFT JOIN teams t ON p.team_id = t.id 
                WHERE p.league_id = %s 
                AND t.id IS NULL
            ''', (league_id,))
            orphaned_players = cursor.fetchone()[0]
            if orphaned_players > 0:
                issues_found.append(f"{orphaned_players} players with invalid team references")
                print(f"   ❌ {orphaned_players} players with invalid team references")
            else:
                print(f"   ✅ All players have valid team references")
            
            # Check if all teams have valid club/series references
            cursor.execute('''
                SELECT COUNT(*) FROM teams t 
                LEFT JOIN clubs c ON t.club_id = c.id 
                LEFT JOIN series s ON t.series_id = s.id 
                WHERE t.league_id = %s 
                AND (c.id IS NULL OR s.id IS NULL)
            ''', (league_id,))
            orphaned_teams = cursor.fetchone()[0]
            if orphaned_teams > 0:
                issues_found.append(f"{orphaned_teams} teams with invalid club/series references")
                print(f"   ❌ {orphaned_teams} teams with invalid club/series references")
            else:
                print(f"   ✅ All teams have valid club/series references")
            
            # Summary
            print("\n" + "=" * 50)
            print("🎯 VALIDATION SUMMARY")
            print("=" * 50)
            
            if issues_found:
                print(f"❌ {len(issues_found)} issues found:")
                for i, issue in enumerate(issues_found, 1):
                    print(f"   {i}. {issue}")
                return False
            else:
                print("✅ All validations passed! Data looks good.")
                return True
                
    except Exception as e:
        print(f"❌ Validation failed with error: {e}")
        return False

if __name__ == "__main__":
    validate_apta_data()
