#!/usr/bin/env python3
"""
Comprehensive test script for the new ETL data preservation system.

This script tests the backup and restore functionality for:
1. Polls with precise team context
2. Captain messages with precise team context  
3. Practice times with precise team context
4. User associations and availability data
5. League contexts

The script creates test data, runs the backup/restore process, and validates results.
"""

import sys
import os
import psycopg2
from datetime import datetime, timedelta
import json

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from data.etl.database_import.import_all_jsons_to_database import ComprehensiveETL
import psycopg2
from database_config import get_db_url, parse_db_url

def create_test_data(conn):
    """Create test data for the ETL preservation system"""
    print("🧪 Creating test data for ETL preservation system...")
    
    cursor = conn.cursor()
    
    # Use existing leagues (they already exist in the database)
    print("   Using existing leagues: APTA_CHICAGO and NSTF")
    
    # Use existing clubs (they already exist in the database)
    print("   Using existing clubs: Tennaqua and Glenbrook RC")
    
    # Create test series
    cursor.execute("""
        INSERT INTO series (name, display_name) VALUES 
        ('Test Series 22', 'Test Series 22'),
        ('Test Series 2B', 'Test Series 2B')
    """)
    
    # Create test teams
    cursor.execute("""
        INSERT INTO teams (team_name, team_alias, league_id, club_id, series_id, display_name) VALUES 
        ('Test Chicago 22 @ Tennaqua', 'TestChicago22', 
         (SELECT id FROM leagues WHERE league_id = 'APTA_CHICAGO'),
         (SELECT id FROM clubs WHERE name = 'Tennaqua'),
         (SELECT id FROM series WHERE name = 'Test Series 22'),
         'Test Chicago 22 @ Tennaqua'),
        ('Test Series 2B @ Tennaqua', 'TestSeries2B',
         (SELECT id FROM leagues WHERE league_id = 'NSTF'),
         (SELECT id FROM clubs WHERE name = 'Tennaqua'),
         (SELECT id FROM series WHERE name = 'Test Series 2B'),
         'Test Series 2B @ Tennaqua')

    """)
    
    # Create test users
    cursor.execute("""
        INSERT INTO users (email, first_name, last_name, password_hash, league_context) VALUES 
        ('test.captain@example.com', 'Test', 'Captain', 'hash', 
         (SELECT id FROM leagues WHERE league_id = 'APTA_CHICAGO')),
        ('test.user@example.com', 'Test', 'User', 'hash',
         (SELECT id FROM leagues WHERE league_id = 'NSTF'))

    """)
    
    # Create test players
    cursor.execute("""
        INSERT INTO players (tenniscores_player_id, first_name, last_name, team_id, league_id, club_id, series_id, is_active) VALUES 
        ('test-player-1', 'Test', 'Captain', 
         (SELECT id FROM teams WHERE team_name = 'Test Chicago 22 @ Tennaqua'),
         (SELECT id FROM leagues WHERE league_id = 'APTA_CHICAGO'),
         (SELECT id FROM clubs WHERE name = 'Tennaqua'),
         (SELECT id FROM series WHERE name = 'Test Series 22'), true),
        ('test-player-2', 'Test', 'User',
         (SELECT id FROM teams WHERE team_name = 'Test Series 2B @ Tennaqua'),
         (SELECT id FROM leagues WHERE league_id = 'NSTF'),
         (SELECT id FROM clubs WHERE name = 'Tennaqua'),
         (SELECT id FROM series WHERE name = 'Test Series 2B'), true)

    """)
    
    # Create test user associations
    cursor.execute("""
        INSERT INTO user_player_associations (user_id, tenniscores_player_id) VALUES 
        ((SELECT id FROM users WHERE email = 'test.captain@example.com'), 'test-player-1'),
        ((SELECT id FROM users WHERE email = 'test.user@example.com'), 'test-player-2')

    """)
    
    # Create test polls
    cursor.execute("""
        INSERT INTO polls (question, created_by, team_id, created_at) VALUES 
        ('Test poll for Chicago 22', 
         (SELECT id FROM users WHERE email = 'test.captain@example.com'),
         (SELECT id FROM teams WHERE team_name = 'Test Chicago 22 @ Tennaqua'),
         NOW()),
        ('Test poll for Series 2B',
         (SELECT id FROM users WHERE email = 'test.user@example.com'),
         (SELECT id FROM teams WHERE team_name = 'Test Series 2B @ Tennaqua'),
         NOW())
    """)
    
    # Create test captain messages
    cursor.execute("""
        INSERT INTO captain_messages (message, captain_user_id, team_id, created_at) VALUES 
        ('Test captain message for Chicago 22',
         (SELECT id FROM users WHERE email = 'test.captain@example.com'),
         (SELECT id FROM teams WHERE team_name = 'Test Chicago 22 @ Tennaqua'),
         NOW()),
        ('Test captain message for Series 2B',
         (SELECT id FROM users WHERE email = 'test.user@example.com'),
         (SELECT id FROM teams WHERE team_name = 'Test Series 2B @ Tennaqua'),
         NOW())
    """)
    
    # Create test practice times
    cursor.execute("""
        INSERT INTO schedule (league_id, match_date, match_time, home_team, away_team, home_team_id, location) VALUES 
        ((SELECT id FROM leagues WHERE league_id = 'APTA_CHICAGO'),
         '2025-01-20', '18:00', 'Chicago 22 Practice', 'Practice',
         (SELECT id FROM teams WHERE team_name = 'Test Chicago 22 @ Tennaqua'),
         'Tennaqua Courts'),
        ((SELECT id FROM leagues WHERE league_id = 'NSTF'),
         '2025-01-21', '19:00', 'Series 2B Practice', 'Practice',
         (SELECT id FROM teams WHERE team_name = 'Test Series 2B @ Tennaqua'),
         'Tennaqua Courts')
    """)
    
    # Create test availability
    cursor.execute("""
        INSERT INTO player_availability (user_id, match_date, availability_status, notes, series_id, player_name) VALUES 
        ((SELECT id FROM users WHERE email = 'test.captain@example.com'),
         '2025-01-20 00:00:00 UTC', 1, 'Available for practice',
         (SELECT id FROM series WHERE name = 'Test Series 22'), 'Test Captain'),
        ((SELECT id FROM users WHERE email = 'test.user@example.com'),
         '2025-01-21 00:00:00 UTC', 1, 'Available for practice',
         (SELECT id FROM series WHERE name = 'Test Series 2B'), 'Test User')
    """)
    
    conn.commit()
    print("✅ Test data created successfully")

def validate_backup_data(conn):
    """Validate that backup data was created correctly"""
    print("🔍 Validating backup data...")
    
    cursor = conn.cursor()
    
    # Check polls backup
    cursor.execute("SELECT COUNT(*) FROM polls_backup")
    polls_count = cursor.fetchone()[0]
    print(f"   📊 Polls backed up: {polls_count}")
    
    # Check captain messages backup
    cursor.execute("SELECT COUNT(*) FROM captain_messages_backup")
    messages_count = cursor.fetchone()[0]
    print(f"   💬 Captain messages backed up: {messages_count}")
    
    # Check practice times backup
    cursor.execute("SELECT COUNT(*) FROM practice_times_backup")
    practice_count = cursor.fetchone()[0]
    print(f"   ⏰ Practice times backed up: {practice_count}")
    
    # Check team mapping backup
    cursor.execute("SELECT COUNT(*) FROM team_mapping_backup")
    teams_count = cursor.fetchone()[0]
    print(f"   🏆 Teams backed up for mapping: {teams_count}")
    
    # Check user associations backup
    cursor.execute("SELECT COUNT(*) FROM user_player_associations_backup")
    associations_count = cursor.fetchone()[0]
    print(f"   👥 User associations backed up: {associations_count}")
    
    # Check league contexts backup
    cursor.execute("SELECT COUNT(*) FROM user_league_contexts_backup")
    contexts_count = cursor.fetchone()[0]
    print(f"   🏆 League contexts backed up: {contexts_count}")
    
    # Check availability backup
    cursor.execute("SELECT COUNT(*) FROM player_availability_backup")
    availability_count = cursor.fetchone()[0]
    print(f"   📅 Availability records backed up: {availability_count}")
    
    return {
        'polls': polls_count,
        'messages': messages_count,
        'practice': practice_count,
        'teams': teams_count,
        'associations': associations_count,
        'contexts': contexts_count,
        'availability': availability_count
    }

def validate_restored_data(conn):
    """Validate that data was restored correctly"""
    print("🔍 Validating restored data...")
    
    cursor = conn.cursor()
    
    # Check polls restoration
    cursor.execute("""
        SELECT COUNT(*) FROM polls p
        JOIN teams t ON p.team_id = t.id
        WHERE p.team_id IS NOT NULL
    """)
    polls_restored = cursor.fetchone()[0]
    print(f"   📊 Polls with valid team_id: {polls_restored}")
    
    # Check captain messages restoration
    cursor.execute("""
        SELECT COUNT(*) FROM captain_messages cm
        JOIN teams t ON cm.team_id = t.id
        WHERE cm.team_id IS NOT NULL
    """)
    messages_restored = cursor.fetchone()[0]
    print(f"   💬 Captain messages with valid team_id: {messages_restored}")
    
    # Check practice times restoration
    cursor.execute("""
        SELECT COUNT(*) FROM schedule s
        JOIN teams t ON s.home_team_id = t.id
        WHERE s.home_team LIKE '%Practice%' AND s.home_team_id IS NOT NULL
    """)
    practice_restored = cursor.fetchone()[0]
    print(f"   ⏰ Practice times with valid team_id: {practice_restored}")
    
    # Check for orphaned data
    cursor.execute("SELECT COUNT(*) FROM polls WHERE team_id IS NULL")
    orphaned_polls = cursor.fetchone()[0]
    print(f"   ⚠️  Orphaned polls: {orphaned_polls}")
    
    cursor.execute("SELECT COUNT(*) FROM captain_messages WHERE team_id IS NULL")
    orphaned_messages = cursor.fetchone()[0]
    print(f"   ⚠️  Orphaned captain messages: {orphaned_messages}")
    
    cursor.execute("SELECT COUNT(*) FROM schedule WHERE home_team LIKE '%Practice%' AND home_team_id IS NULL")
    orphaned_practice = cursor.fetchone()[0]
    print(f"   ⚠️  Orphaned practice times: {orphaned_practice}")
    
    return {
        'polls_restored': polls_restored,
        'messages_restored': messages_restored,
        'practice_restored': practice_restored,
        'orphaned_polls': orphaned_polls,
        'orphaned_messages': orphaned_messages,
        'orphaned_practice': orphaned_practice
    }

def cleanup_test_data(conn):
    """Clean up test data"""
    print("🧹 Cleaning up test data...")
    
    cursor = conn.cursor()
    
    # Delete test data in reverse dependency order
    cursor.execute("DELETE FROM player_availability WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test.%@example.com')")
    cursor.execute("DELETE FROM schedule WHERE home_team LIKE '%Practice%'")
    cursor.execute("DELETE FROM captain_messages WHERE captain_user_id IN (SELECT id FROM users WHERE email LIKE 'test.%@example.com')")
    cursor.execute("DELETE FROM polls WHERE created_by IN (SELECT id FROM users WHERE email LIKE 'test.%@example.com')")
    cursor.execute("DELETE FROM user_player_associations WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test.%@example.com')")
    cursor.execute("DELETE FROM players WHERE tenniscores_player_id LIKE 'test-player-%'")
    cursor.execute("DELETE FROM users WHERE email LIKE 'test.%@example.com'")
    cursor.execute("DELETE FROM teams WHERE team_name LIKE '%Test%'")
    cursor.execute("DELETE FROM series WHERE name IN ('Test Series 22', 'Test Series 2B')")
    # Don't delete clubs as they are real data
    # Don't delete leagues as they are real data
    
    conn.commit()
    print("✅ Test data cleaned up")

def main():
    """Main test function"""
    print("🧪 Starting comprehensive ETL data preservation test...")
    
    try:
        # Get database connection
        url = get_db_url()
        db_params = parse_db_url(url)
        conn = psycopg2.connect(**db_params)
        
        # Create test data
        create_test_data(conn)
        
        # Initialize ETL system
        etl = ComprehensiveETL()
        
        # Test backup system
        print("\n🛡️  Testing backup system...")
        backup_results = etl.backup_user_data_and_team_mappings(conn)
        backup_validation = validate_backup_data(conn)
        
        # Simulate ETL process by clearing and recreating teams
        print("\n🔄 Simulating ETL process...")
        cursor = conn.cursor()
        
        # Clear teams (this would happen during ETL)
        # First delete dependent data
        cursor.execute("DELETE FROM player_history WHERE player_id IN (SELECT id FROM players WHERE team_id IN (SELECT id FROM teams))")
        cursor.execute("DELETE FROM players WHERE team_id IN (SELECT id FROM teams)")
        cursor.execute("DELETE FROM polls WHERE team_id IN (SELECT id FROM teams)")
        cursor.execute("DELETE FROM captain_messages WHERE team_id IN (SELECT id FROM teams)")
        cursor.execute("DELETE FROM schedule WHERE home_team_id IN (SELECT id FROM teams) OR away_team_id IN (SELECT id FROM teams)")
        cursor.execute("DELETE FROM series_stats WHERE team_id IN (SELECT id FROM teams)")
        cursor.execute("DELETE FROM match_scores WHERE home_team_id IN (SELECT id FROM teams) OR away_team_id IN (SELECT id FROM teams)")
        cursor.execute("DELETE FROM teams")
        conn.commit()
        
        # Recreate teams (this would happen during ETL)
        cursor.execute("""
            INSERT INTO teams (team_name, team_alias, league_id, club_id, series_id, display_name) VALUES 
            ('Test Chicago 22 @ Tennaqua', 'TestChicago22', 
             (SELECT id FROM leagues WHERE league_id = 'APTA_CHICAGO'),
             (SELECT id FROM clubs WHERE name = 'Tennaqua'),
             (SELECT id FROM series WHERE name = 'Test Series 22'),
             'Test Chicago 22 @ Tennaqua'),
            ('Test Series 2B @ Tennaqua', 'TestSeries2B',
             (SELECT id FROM leagues WHERE league_id = 'NSTF'),
             (SELECT id FROM clubs WHERE name = 'Tennaqua'),
             (SELECT id FROM series WHERE name = 'Test Series 2B'),
             'Test Series 2B @ Tennaqua')
        """)
        conn.commit()
        
        # Test restore system
        print("\n🔄 Testing restore system...")
        restore_results = etl.restore_user_data_with_team_mappings(conn)
        restore_validation = validate_restored_data(conn)
        
        # Print results
        print("\n📊 Test Results:")
        print(f"   Backup Results: {json.dumps(backup_results, indent=2)}")
        print(f"   Restore Results: {json.dumps(restore_results, indent=2)}")
        print(f"   Backup Validation: {json.dumps(backup_validation, indent=2)}")
        print(f"   Restore Validation: {json.dumps(restore_validation, indent=2)}")
        
        # Check for success
        success = (
            restore_validation['orphaned_polls'] == 0 and
            restore_validation['orphaned_messages'] == 0 and
            restore_validation['orphaned_practice'] == 0 and
            restore_validation['polls_restored'] > 0 and
            restore_validation['messages_restored'] > 0 and
            restore_validation['practice_restored'] > 0
        )
        
        if success:
            print("\n✅ ETL data preservation test PASSED!")
        else:
            print("\n❌ ETL data preservation test FAILED!")
            return False
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        return False
    
    finally:
        # Clean up test data
        try:
            cleanup_test_data(conn)
            conn.close()
        except:
            pass
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 