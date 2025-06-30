#!/usr/bin/env python3
"""
Fix orphaned CITA team data for player nndz-WkMrK3didjlnUT09
This script addresses missing team records and NULL team IDs causing schedule/stats access issues.
"""

import sys
import os

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from database_config import get_db

def fix_orphaned_cita_teams():
    """Fix orphaned CITA team data by creating missing teams and updating references"""
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        print("🔧 FIXING ORPHANED CITA TEAM DATA")
        print("=" * 60)
        
        # Step 1: Get CITA league ID
        cursor.execute("SELECT id FROM leagues WHERE league_id = 'CITA'")
        cita_league = cursor.fetchone()
        
        if not cita_league:
            print("❌ CITA league not found!")
            return
            
        cita_league_id = cita_league[0]
        print(f"✅ CITA League ID: {cita_league_id}")
        
        # Step 2: Find all missing CITA teams from match_scores
        print("\n🔍 Step 1: Identifying missing CITA teams...")
        
        cursor.execute("""
            SELECT DISTINCT team_name
            FROM (
                SELECT home_team as team_name FROM match_scores 
                WHERE league_id = %s AND home_team_id IS NULL AND home_team IS NOT NULL
                UNION
                SELECT away_team as team_name FROM match_scores 
                WHERE league_id = %s AND away_team_id IS NULL AND away_team IS NOT NULL
            ) missing_teams
            WHERE team_name != 'BYE'
            ORDER BY team_name
        """, [cita_league_id, cita_league_id])
        
        missing_teams = [row[0] for row in cursor.fetchall()]
        print(f"Found {len(missing_teams)} missing CITA teams:")
        for team in missing_teams:
            print(f"   - {team}")
        
        if not missing_teams:
            print("✅ No missing teams found!")
            return
        
        # Step 3: Create missing clubs, series, and teams
        print("\n🏗️  Step 2: Creating missing clubs, series, and teams...")
        
        created_teams = {}
        
        for team_name in missing_teams:
            try:
                # Parse team name to extract club and series
                club_name, series_name = parse_cita_team_name(team_name)
                
                print(f"\n   Processing: {team_name}")
                print(f"   - Parsed Club: {club_name}")
                print(f"   - Parsed Series: {series_name}")
                
                # Create/get club
                cursor.execute("""
                    INSERT INTO clubs (name) VALUES (%s)
                    ON CONFLICT (name) DO NOTHING
                    RETURNING id
                """, [club_name])
                
                club_result = cursor.fetchone()
                if club_result:
                    club_id = club_result[0]
                    print(f"   ✅ Created club: {club_name} (ID: {club_id})")
                else:
                    cursor.execute("SELECT id FROM clubs WHERE name = %s", [club_name])
                    club_id = cursor.fetchone()[0]
                    print(f"   ✅ Found existing club: {club_name} (ID: {club_id})")
                
                # Create/get series
                cursor.execute("""
                    INSERT INTO series (name) VALUES (%s)
                    ON CONFLICT (name) DO NOTHING
                    RETURNING id
                """, [series_name])
                
                series_result = cursor.fetchone()
                if series_result:
                    series_id = series_result[0]
                    print(f"   ✅ Created series: {series_name} (ID: {series_id})")
                else:
                    cursor.execute("SELECT id FROM series WHERE name = %s", [series_name])
                    series_id = cursor.fetchone()[0]
                    print(f"   ✅ Found existing series: {series_name} (ID: {series_id})")
                
                # Create/get team
                cursor.execute("""
                    INSERT INTO teams (club_id, series_id, league_id, team_name, created_at)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT ON CONSTRAINT unique_team_name_per_league DO NOTHING
                    RETURNING id
                """, [club_id, series_id, cita_league_id, team_name])
                
                team_result = cursor.fetchone()
                if team_result:
                    team_id = team_result[0]
                    print(f"   ✅ Created team: {team_name} (ID: {team_id})")
                else:
                    cursor.execute("""
                        SELECT id FROM teams 
                        WHERE team_name = %s AND league_id = %s
                    """, [team_name, cita_league_id])
                    team_id = cursor.fetchone()[0]
                    print(f"   ✅ Found existing team: {team_name} (ID: {team_id})")
                
                created_teams[team_name] = team_id
                
                # Create club-league relationship
                cursor.execute("""
                    INSERT INTO club_leagues (club_id, league_id, created_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT ON CONSTRAINT unique_club_league DO NOTHING
                """, [club_id, cita_league_id])
                
                # Create series-league relationship
                cursor.execute("""
                    INSERT INTO series_leagues (series_id, league_id, created_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT ON CONSTRAINT unique_series_league DO NOTHING
                """, [series_id, cita_league_id])
                
            except Exception as e:
                print(f"   ❌ Error processing {team_name}: {e}")
                continue
        
        conn.commit()
        print(f"\n✅ Created {len(created_teams)} teams successfully")
        
        # Step 4: Update NULL team IDs in match_scores
        print("\n🔄 Step 3: Updating NULL team IDs in match_scores...")
        
        updated_matches = 0
        
        # Update home team IDs
        cursor.execute("""
            UPDATE match_scores 
            SET home_team_id = teams.id
            FROM teams
            JOIN leagues ON teams.league_id = leagues.id
            WHERE match_scores.home_team = teams.team_name
            AND match_scores.league_id = leagues.id
            AND leagues.league_id = 'CITA'
            AND match_scores.home_team_id IS NULL
        """)
        home_updates = cursor.rowcount
        
        # Update away team IDs
        cursor.execute("""
            UPDATE match_scores 
            SET away_team_id = teams.id
            FROM teams
            JOIN leagues ON teams.league_id = leagues.id
            WHERE match_scores.away_team = teams.team_name
            AND match_scores.league_id = leagues.id
            AND leagues.league_id = 'CITA'
            AND match_scores.away_team_id IS NULL
        """)
        away_updates = cursor.rowcount
        
        updated_matches = home_updates + away_updates
        print(f"✅ Updated {updated_matches} match records ({home_updates} home, {away_updates} away)")
        
        # Step 5: Update NULL team IDs in series_stats
        print("\n🔄 Step 4: Updating NULL team IDs in series_stats...")
        
        cursor.execute("""
            UPDATE series_stats 
            SET team_id = teams.id
            FROM teams
            JOIN leagues ON teams.league_id = leagues.id
            WHERE series_stats.team = teams.team_name
            AND series_stats.league_id = leagues.id
            AND leagues.league_id = 'CITA'
            AND series_stats.team_id IS NULL
        """)
        stats_updates = cursor.rowcount
        
        print(f"✅ Updated {stats_updates} series stats records")
        
        conn.commit()
        
        # Step 6: Verify the fix for our specific player
        print("\n🔍 Step 5: Verifying fix for player nndz-WkMrK3didjlnUT09...")
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM match_scores ms
            WHERE (ms.home_player_1_id = 'nndz-WkMrK3didjlnUT09' OR 
                   ms.home_player_2_id = 'nndz-WkMrK3didjlnUT09' OR
                   ms.away_player_1_id = 'nndz-WkMrK3didjlnUT09' OR 
                   ms.away_player_2_id = 'nndz-WkMrK3didjlnUT09')
            AND (ms.home_team_id IS NULL OR ms.away_team_id IS NULL)
        """)
        remaining_nulls = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM match_scores ms
            JOIN leagues l ON ms.league_id = l.id
            WHERE (ms.home_player_1_id = 'nndz-WkMrK3didjlnUT09' OR 
                   ms.home_player_2_id = 'nndz-WkMrK3didjlnUT09' OR
                   ms.away_player_1_id = 'nndz-WkMrK3didjlnUT09' OR 
                   ms.away_player_2_id = 'nndz-WkMrK3didjlnUT09')
            AND l.league_id = 'CITA'
            AND ms.home_team_id IS NOT NULL AND ms.away_team_id IS NOT NULL
        """)
        fixed_cita_matches = cursor.fetchone()[0]
        
        print(f"✅ Player matches with NULL team IDs remaining: {remaining_nulls}")
        print(f"✅ Player CITA matches with valid team IDs: {fixed_cita_matches}")
        
        # Step 7: Final verification - check if teams now exist
        print("\n🔍 Step 6: Final team verification...")
        
        cursor.execute("""
            SELECT DISTINCT 
                CASE 
                    WHEN ms.home_player_1_id = 'nndz-WkMrK3didjlnUT09' OR ms.home_player_2_id = 'nndz-WkMrK3didjlnUT09' THEN ms.home_team
                    ELSE ms.away_team
                END as player_team
            FROM match_scores ms
            JOIN leagues l ON ms.league_id = l.id
            WHERE (ms.home_player_1_id = 'nndz-WkMrK3didjlnUT09' OR 
                   ms.home_player_2_id = 'nndz-WkMrK3didjlnUT09' OR
                   ms.away_player_1_id = 'nndz-WkMrK3didjlnUT09' OR 
                   ms.away_player_2_id = 'nndz-WkMrK3didjlnUT09')
            AND l.league_id = 'CITA'
        """)
        
        player_cita_teams = [row[0] for row in cursor.fetchall()]
        
        for team_name in player_cita_teams:
            cursor.execute("""
                SELECT COUNT(*) FROM teams t
                JOIN leagues l ON t.league_id = l.id
                WHERE t.team_name = %s AND l.league_id = 'CITA'
            """, [team_name])
            
            team_exists = cursor.fetchone()[0] > 0
            status = "✅" if team_exists else "❌"
            print(f"   {status} {team_name}")
        
        print("\n" + "=" * 60)
        print("🎉 ORPHANED CITA TEAM FIX COMPLETE!")
        print("=" * 60)
        print(f"Teams created: {len(created_teams)}")
        print(f"Match records updated: {updated_matches}")
        print(f"Series stats updated: {stats_updates}")
        print(f"Player null team IDs remaining: {remaining_nulls}")


def parse_cita_team_name(team_name):
    """
    Parse CITA team name to extract club and series.
    Examples:
    - "College Park - East" -> ("College Park - East", "Mixed Doubles")
    - "Midtown - Palatine" -> ("Midtown - Palatine", "Mixed Doubles")
    """
    # For CITA, the team name is typically the club name
    # Series information comes from the series_stats data
    club_name = team_name.strip()
    
    # Default series for CITA teams (can be refined based on actual data)
    series_name = "Mixed Doubles"
    
    return club_name, series_name


if __name__ == "__main__":
    fix_orphaned_cita_teams() 