#!/usr/bin/env python3
"""
Team ID Orphans Diagnostic Script
=================================

This script comprehensively diagnoses orphaned team_id references across
the Rally database that are causing issues with:
1. Captain notifications not showing
2. Practice times missing team references
3. Team polls not displaying

Usage: python scripts/diagnose_team_id_orphans.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from database_config import get_db
from datetime import datetime

def main():
    print("🔍 TEAM ID ORPHANS DIAGNOSTIC")
    print("=" * 60)
    print(f"📅 Diagnostic run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Step 1: Check Polls Orphans
        print("📊 STEP 1: POLLS ORPHAN ANALYSIS")
        print("-" * 40)
        
        # Count total polls
        cursor.execute("SELECT COUNT(*) FROM polls")
        total_polls = cursor.fetchone()[0]
        print(f"Total polls in database: {total_polls}")
        
        # Count polls with team_id
        cursor.execute("SELECT COUNT(*) FROM polls WHERE team_id IS NOT NULL")
        polls_with_team = cursor.fetchone()[0]
        print(f"Polls with team_id: {polls_with_team}")
        
        # Count orphaned polls (team_id points to non-existent team)
        cursor.execute("""
            SELECT COUNT(*) FROM polls p
            LEFT JOIN teams t ON p.team_id = t.id
            WHERE p.team_id IS NOT NULL AND t.id IS NULL
        """)
        orphaned_polls = cursor.fetchone()[0]
        print(f"🚨 ORPHANED polls: {orphaned_polls}")
        
        if orphaned_polls > 0:
            print("\n   📋 ORPHANED POLLS DETAILS:")
            cursor.execute("""
                SELECT p.id, p.team_id, p.question, p.created_at, u.first_name, u.last_name
                FROM polls p
                LEFT JOIN teams t ON p.team_id = t.id
                LEFT JOIN users u ON p.created_by = u.id
                WHERE p.team_id IS NOT NULL AND t.id IS NULL
                ORDER BY p.created_at DESC
                LIMIT 10
            """)
            orphaned_details = cursor.fetchall()
            for poll_id, team_id, question, created_at, first_name, last_name in orphaned_details:
                print(f"   • Poll {poll_id}: team_id={team_id} | \"{question[:50]}...\" | {first_name} {last_name} | {created_at.strftime('%m/%d/%Y')}")
        
        print()
        
        # Step 2: Check Captain Messages Orphans
        print("💬 STEP 2: CAPTAIN MESSAGES ORPHAN ANALYSIS")
        print("-" * 40)
        
        # Count total captain messages
        cursor.execute("SELECT COUNT(*) FROM captain_messages")
        total_messages = cursor.fetchone()[0]
        print(f"Total captain messages: {total_messages}")
        
        # Count orphaned captain messages
        cursor.execute("""
            SELECT COUNT(*) FROM captain_messages cm
            LEFT JOIN teams t ON cm.team_id = t.id
            WHERE cm.team_id IS NOT NULL AND t.id IS NULL
        """)
        orphaned_messages = cursor.fetchone()[0]
        print(f"🚨 ORPHANED captain messages: {orphaned_messages}")
        
        if orphaned_messages > 0:
            print("\n   📋 ORPHANED CAPTAIN MESSAGES DETAILS:")
            cursor.execute("""
                SELECT cm.id, cm.team_id, cm.message, cm.created_at, u.first_name, u.last_name
                FROM captain_messages cm
                LEFT JOIN teams t ON cm.team_id = t.id
                LEFT JOIN users u ON cm.captain_user_id = u.id
                WHERE cm.team_id IS NOT NULL AND t.id IS NULL
                ORDER BY cm.created_at DESC
                LIMIT 10
            """)
            orphaned_details = cursor.fetchall()
            for msg_id, team_id, message, created_at, first_name, last_name in orphaned_details:
                print(f"   • Message {msg_id}: team_id={team_id} | \"{message[:50]}...\" | {first_name} {last_name} | {created_at.strftime('%m/%d/%Y')}")
        
        print()
        
        # Step 3: Check Practice Times Orphans
        print("⏰ STEP 3: PRACTICE TIMES ORPHAN ANALYSIS")
        print("-" * 40)
        
        # Count total practice times
        cursor.execute("""
            SELECT COUNT(*) FROM schedule 
            WHERE home_team LIKE '%Practice%' OR home_team LIKE '%practice%'
        """)
        total_practice = cursor.fetchone()[0]
        print(f"Total practice times: {total_practice}")
        
        # Count practice times with team_id
        cursor.execute("""
            SELECT COUNT(*) FROM schedule 
            WHERE (home_team LIKE '%Practice%' OR home_team LIKE '%practice%')
            AND home_team_id IS NOT NULL
        """)
        practice_with_team = cursor.fetchone()[0]
        print(f"Practice times with team_id: {practice_with_team}")
        
        # Count orphaned practice times
        cursor.execute("""
            SELECT COUNT(*) FROM schedule s
            LEFT JOIN teams t ON s.home_team_id = t.id
            WHERE (s.home_team LIKE '%Practice%' OR s.home_team LIKE '%practice%')
            AND s.home_team_id IS NOT NULL AND t.id IS NULL
        """)
        orphaned_practice = cursor.fetchone()[0]
        print(f"🚨 ORPHANED practice times: {orphaned_practice}")
        
        if orphaned_practice > 0:
            print("\n   📋 ORPHANED PRACTICE TIMES DETAILS:")
            cursor.execute("""
                SELECT s.id, s.home_team_id, s.home_team, s.match_date, s.match_time
                FROM schedule s
                LEFT JOIN teams t ON s.home_team_id = t.id
                WHERE (s.home_team LIKE '%Practice%' OR s.home_team LIKE '%practice%')
                AND s.home_team_id IS NOT NULL AND t.id IS NULL
                ORDER BY s.match_date DESC
                LIMIT 10
            """)
            orphaned_details = cursor.fetchall()
            for sched_id, team_id, home_team, match_date, match_time in orphaned_details:
                print(f"   • Schedule {sched_id}: team_id={team_id} | \"{home_team}\" | {match_date} {match_time}")
        
        print()
        
        # Step 4: Available Teams Analysis
        print("🏆 STEP 4: AVAILABLE TEAMS ANALYSIS")
        print("-" * 40)
        
        # Count current teams
        cursor.execute("SELECT COUNT(*) FROM teams")
        total_teams = cursor.fetchone()[0]
        print(f"Total teams in database: {total_teams}")
        
        # Show teams that have users (most relevant for fixing orphans)
        cursor.execute("""
            SELECT t.id, t.team_name, t.team_alias, l.league_id, COUNT(DISTINCT u.id) as user_count
            FROM teams t
            JOIN leagues l ON t.league_id = l.id
            JOIN players p ON t.id = p.team_id
            JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            JOIN users u ON upa.user_id = u.id
            GROUP BY t.id, t.team_name, t.team_alias, l.league_id
            HAVING COUNT(DISTINCT u.id) > 0
            ORDER BY user_count DESC, t.team_name
            LIMIT 15
        """)
        teams_with_users = cursor.fetchall()
        print(f"Teams with active users: {len(teams_with_users)}")
        print("\n   📋 TOP TEAMS WITH USERS:")
        for team_id, team_name, team_alias, league_id, user_count in teams_with_users:
            alias_display = f" ({team_alias})" if team_alias else ""
            print(f"   • Team {team_id}: {team_name}{alias_display} | {league_id} | {user_count} users")
        
        print()
        
        # Step 5: Summary and Recommendations
        print("📊 SUMMARY & IMPACT ANALYSIS")
        print("-" * 40)
        
        total_orphans = orphaned_polls + orphaned_messages + orphaned_practice
        print(f"🚨 Total orphaned records: {total_orphans}")
        print(f"   • Orphaned polls: {orphaned_polls}")
        print(f"   • Orphaned captain messages: {orphaned_messages}")
        print(f"   • Orphaned practice times: {orphaned_practice}")
        
        print()
        print("💥 USER IMPACT:")
        if orphaned_polls > 0:
            print(f"   • {orphaned_polls} polls are invisible to users")
        if orphaned_messages > 0:
            print(f"   • {orphaned_messages} captain notifications are not showing")
        if orphaned_practice > 0:
            print(f"   • {orphaned_practice} practice times missing team context")
        
        if total_orphans == 0:
            print("   ✅ No orphaned records found - system is healthy!")
        
        print()
        print("🔧 RECOMMENDED ACTIONS:")
        if total_orphans > 0:
            print("   1. Run: python scripts/fix_team_id_orphans.py")
            print("   2. Verify fix: python scripts/diagnose_team_id_orphans.py")
            print("   3. Test user functionality (polls, notifications, practice times)")
            print("   4. Improve ETL team ID preservation to prevent future issues")
        else:
            print("   • System is healthy - no action needed")
            print("   • Monitor ETL imports to ensure team ID preservation works")
        
        print()
        print("=" * 60)
        print("🏁 DIAGNOSTIC COMPLETE")

if __name__ == "__main__":
    main() 