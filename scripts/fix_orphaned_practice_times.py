#!/usr/bin/env python3
"""
Fix Orphaned Practice Times

This script handles orphaned practice times that might need to be created or fixed.
It can be used to:
1. Create practice times for teams that need them
2. Fix orphaned practice times with missing team associations
3. Validate practice time data integrity
"""

import psycopg2
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_config import parse_db_url, get_db_url
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_orphaned_practice_times():
    """Fix orphaned practice times and create missing ones"""
    print("🔧 Fixing Orphaned Practice Times")
    print("=" * 50)
    
    try:
        # Connect to database
        config = parse_db_url(get_db_url())
        conn = psycopg2.connect(**config)
        cursor = conn.cursor()
        
        # Step 1: Check current practice times status
        print("\n📊 Step 1: Current Practice Times Status")
        print("-" * 40)
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM schedule 
            WHERE home_team LIKE '%Practice%' OR away_team LIKE '%Practice%' 
            OR home_team LIKE '%practice%' OR away_team LIKE '%practice%'
        """)
        
        practice_count = cursor.fetchone()[0]
        print(f"   Practice times in schedule: {practice_count}")
        
        # Step 2: Check for orphaned practice times
        print("\n🔍 Step 2: Checking for Orphaned Practice Times")
        print("-" * 40)
        
        cursor.execute("""
            SELECT id, home_team, away_team, match_date, home_team_id, away_team_id, league_id
            FROM schedule 
            WHERE (home_team LIKE '%Practice%' OR away_team LIKE '%Practice%' 
                   OR home_team LIKE '%practice%' OR away_team LIKE '%practice%')
            AND (home_team_id IS NULL OR away_team_id IS NULL)
        """)
        
        orphaned_practices = cursor.fetchall()
        print(f"   Orphaned practice times found: {len(orphaned_practices)}")
        
        if orphaned_practices:
            print("   Orphaned practice times:")
            for practice in orphaned_practices:
                print(f"     ID {practice[0]}: {practice[1]} vs {practice[2]} on {practice[3]}")
                print(f"       home_team_id: {practice[4]}, away_team_id: {practice[5]}, league_id: {practice[6]}")
        
        # Step 3: Fix orphaned practice times by mapping to teams with users
        if orphaned_practices:
            print("\n🔧 Step 3: Fixing Orphaned Practice Times")
            print("-" * 40)
            
            fixed_count = 0
            for practice in orphaned_practices:
                practice_id, home_team, away_team, match_date, home_team_id, away_team_id, league_id = practice
                
                # Try to find matching team for practice times
                if "Tennaqua" in home_team and "22" in home_team:
                    # Map to Tennaqua - 22
                    cursor.execute("""
                        SELECT t.id FROM teams t 
                        JOIN leagues l ON t.league_id = l.id 
                        WHERE l.league_id = 'APTA_CHICAGO' AND t.team_name = 'Tennaqua - 22'
                    """)
                    team = cursor.fetchone()
                    if team:
                        cursor.execute("UPDATE schedule SET home_team_id = %s WHERE id = %s", (team[0], practice_id))
                        fixed_count += 1
                        print(f"   ✅ Fixed practice time {practice_id} → Tennaqua - 22")
                
                elif "Tennaqua" in home_team and "S2B" in home_team:
                    # Map to Tennaqua S2B
                    cursor.execute("""
                        SELECT t.id FROM teams t 
                        JOIN leagues l ON t.league_id = l.id 
                        WHERE l.league_id = 'NSTF' AND t.team_name = 'Tennaqua S2B'
                    """)
                    team = cursor.fetchone()
                    if team:
                        cursor.execute("UPDATE schedule SET home_team_id = %s WHERE id = %s", (team[0], practice_id))
                        fixed_count += 1
                        print(f"   ✅ Fixed practice time {practice_id} → Tennaqua S2B")
            
            print(f"   Total practice times fixed: {fixed_count}")
        
        # Step 4: Create practice times for teams that need them (optional)
        print("\n⏰ Step 4: Creating Practice Times for Teams (Optional)")
        print("-" * 40)
        
        # Find teams with users that don't have practice times
        cursor.execute("""
            SELECT DISTINCT t.id, t.team_name, l.league_name
            FROM teams t
            JOIN leagues l ON t.league_id = l.id
            JOIN players p ON t.id = p.team_id
            JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            WHERE NOT EXISTS (
                SELECT 1 FROM schedule s 
                WHERE s.home_team_id = t.id 
                AND (s.home_team LIKE '%Practice%' OR s.away_team LIKE '%Practice%')
            )
            AND t.team_name IN ('Tennaqua - 22', 'Tennaqua S2B')
        """)
        
        teams_needing_practice = cursor.fetchall()
        print(f"   Teams with users that need practice times: {len(teams_needing_practice)}")
        
        if teams_needing_practice:
            print("   Teams needing practice times:")
            for team in teams_needing_practice:
                print(f"     {team[1]} ({team[2]})")
            
            # Ask if user wants to create practice times
            create_practice = input("\n   Create practice times for these teams? (y/n): ").lower().strip()
            
            if create_practice == 'y':
                created_count = 0
                for team in teams_needing_practice:
                    team_id, team_name, league_name = team
                    
                    # Create a practice time for next week
                    next_week = datetime.now() + timedelta(days=7)
                    practice_date = next_week.strftime('%Y-%m-%d')
                    
                    cursor.execute("""
                        INSERT INTO schedule (
                            league_id, match_date, match_time, home_team, away_team, 
                            home_team_id, location, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        cursor.execute("SELECT id FROM leagues WHERE league_name = %s", (league_name,)).fetchone()[0],
                        practice_date,
                        '18:00:00',  # 6 PM
                        f"{team_name} Practice",
                        "Practice",
                        team_id,
                        "Club Courts",
                        datetime.now()
                    ))
                    
                    created_count += 1
                    print(f"   ✅ Created practice time for {team_name} on {practice_date}")
                
                print(f"   Total practice times created: {created_count}")
        
        # Step 5: Final validation
        print("\n✅ Step 5: Final Validation")
        print("-" * 40)
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM schedule 
            WHERE (home_team LIKE '%Practice%' OR away_team LIKE '%Practice%') 
            AND (home_team_id IS NULL OR away_team_id IS NULL)
        """)
        
        remaining_orphaned = cursor.fetchone()[0]
        print(f"   Remaining orphaned practice times: {remaining_orphaned}")
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM schedule 
            WHERE home_team LIKE '%Practice%' OR away_team LIKE '%Practice%' 
            OR home_team LIKE '%practice%' OR away_team LIKE '%practice%'
        """)
        
        total_practice = cursor.fetchone()[0]
        print(f"   Total practice times: {total_practice}")
        
        if remaining_orphaned == 0:
            print("   ✅ All practice times have valid team associations!")
        else:
            print(f"   ⚠️  {remaining_orphaned} practice times still need team associations")
        
        conn.commit()
        conn.close()
        
        return remaining_orphaned == 0
        
    except Exception as e:
        logger.error(f"Error fixing orphaned practice times: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    success = fix_orphaned_practice_times()
    if success:
        print("\n🎉 Practice times fix completed successfully!")
    else:
        print("\n❌ Practice times fix failed!")
        exit(1) 