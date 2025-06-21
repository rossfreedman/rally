#!/usr/bin/env python3
"""
Script to populate activity_log table with test data for dashboard demonstration
This creates realistic activity patterns for the Activity Monitoring Dashboard
"""

import sys
import os
import uuid
import random
from datetime import datetime, timedelta

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database_utils import execute_query, execute_update, execute_query_one

def get_sample_users():
    """Get existing users from the database"""
    try:
        users = execute_query("SELECT id, email, first_name, last_name FROM users LIMIT 10")
        print(f"Found {len(users)} users in database")
        return users
    except Exception as e:
        print(f"Error getting users: {e}")
        return []

def get_sample_players():
    """Get existing players from the database"""
    try:
        players = execute_query("""
            SELECT p.id, p.first_name, p.last_name, p.team_id, t.team_name, c.name as club_name
            FROM players p
            LEFT JOIN teams t ON p.team_id = t.id
            LEFT JOIN clubs c ON p.club_id = c.id
            LIMIT 20
        """)
        print(f"Found {len(players)} players in database")
        return players
    except Exception as e:
        print(f"Error getting players: {e}")
        return []

def get_sample_teams():
    """Get existing teams from the database"""
    try:
        teams = execute_query("""
            SELECT t.id, t.team_name, c.name as club_name, s.name as series_name
            FROM teams t
            JOIN clubs c ON t.club_id = c.id
            JOIN series s ON t.series_id = s.id
            LIMIT 10
        """)
        print(f"Found {len(teams)} teams in database")
        return teams
    except Exception as e:
        print(f"Error getting teams: {e}")
        return []

def create_activity_entries():
    """Create sample activity log entries"""
    
    print("Getting sample data from database...")
    users = get_sample_users()
    players = get_sample_players()
    teams = get_sample_teams()
    
    if not users:
        print("No users found in database. Please ensure you have users registered.")
        return
    
    # Define activity types and their descriptions
    activity_types = [
        ('login', 'User logged into Rally app'),
        ('logout', 'User logged out of Rally app'),
        ('page_visit', 'User visited a page'),
        ('match_created', 'Match result was created'),
        ('poll_response', 'User responded to team poll'),
        ('availability_update', 'Player updated availability status'),
        ('dashboard_access', 'Admin accessed activity dashboard'),
        ('admin_action', 'Admin performed system action'),
        ('data_update', 'Data was updated in system'),
        ('team_email', 'Team email was sent'),
        ('lineup_update', 'Team lineup was updated'),
        ('score_submitted', 'Match score was submitted')
    ]
    
    # Generate activities for the last 30 days
    print("Generating activity entries...")
    activities_created = 0
    
    for day_offset in range(30):
        # Calculate date (30 days ago to today)
        activity_date = datetime.now() - timedelta(days=day_offset)
        
        # Generate 5-25 activities per day (more recent days have more activity)
        num_activities = random.randint(5, 25) if day_offset < 7 else random.randint(2, 15)
        
        for _ in range(num_activities):
            # Random time during the day
            hour = random.randint(8, 22)  # Activities between 8 AM and 10 PM
            minute = random.randint(0, 59)
            timestamp = activity_date.replace(hour=hour, minute=minute, second=random.randint(0, 59))
            
            # Select random activity type
            action_type, base_description = random.choice(activity_types)
            
            # Select random user
            user = random.choice(users) if users else None
            
            # Select random player (70% chance)
            player = random.choice(players) if players and random.random() < 0.7 else None
            
            # Select random team (50% chance)
            team = random.choice(teams) if teams and random.random() < 0.5 else None
            
            # Create more specific descriptions based on context
            if action_type == 'login':
                action_description = f"User {user['first_name']} {user['last_name']} logged in"
            elif action_type == 'match_created':
                action_description = f"Match result created for {team['team_name'] if team else 'team'}"
            elif action_type == 'poll_response':
                action_description = f"{player['first_name']} {player['last_name']} responded to team poll" if player else "Team poll response received"
            elif action_type == 'availability_update':
                statuses = ['available', 'unavailable', 'maybe']
                status = random.choice(statuses)
                action_description = f"{player['first_name']} {player['last_name']} marked as {status}" if player else f"Availability updated to {status}"
            elif action_type == 'page_visit':
                pages = ['lineup', 'schedule', 'team_stats', 'availability', 'matches', 'improve']
                page = random.choice(pages)
                action_description = f"Visited {page} page"
            elif action_type == 'admin_action':
                actions = ['user management', 'data import', 'system backup', 'league update']
                admin_action = random.choice(actions)
                action_description = f"Admin performed {admin_action}"
            else:
                action_description = base_description
            
            # Create related IDs for some activity types
            related_id = None
            related_type = None
            if action_type in ['match_created', 'score_submitted']:
                related_id = str(random.randint(1000, 9999))
                related_type = 'match'
            elif action_type == 'poll_response':
                related_id = str(random.randint(100, 999))
                related_type = 'poll'
            
            # Create extra data (optional JSON)
            extra_data = None
            if action_type == 'page_visit':
                extra_data = f'{{"page": "{random.choice(["lineup", "schedule", "availability"])}", "duration": {random.randint(30, 300)}}}'
            elif action_type == 'match_created':
                extra_data = f'{{"home_score": {random.randint(0, 6)}, "away_score": {random.randint(0, 6)}}}'
            
            # Insert activity log entry
            try:
                execute_update("""
                    INSERT INTO activity_log (
                        id, action_type, action_description, user_id, player_id, team_id,
                        related_id, related_type, ip_address, user_agent, extra_data, timestamp
                    ) VALUES (
                        %(id)s, %(action_type)s, %(action_description)s, %(user_id)s, %(player_id)s, %(team_id)s,
                        %(related_id)s, %(related_type)s, %(ip_address)s, %(user_agent)s, %(extra_data)s, %(timestamp)s
                    )
                """, {
                    'id': str(uuid.uuid4()),
                    'action_type': action_type,
                    'action_description': action_description,
                    'user_id': user['id'] if user else None,
                    'player_id': player['id'] if player else None,
                    'team_id': team['id'] if team else None,
                    'related_id': related_id,
                    'related_type': related_type,
                    'ip_address': f"192.168.1.{random.randint(1, 255)}",
                    'user_agent': random.choice([
                        'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)',
                        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                        'Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)'
                    ]),
                    'extra_data': extra_data,
                    'timestamp': timestamp
                })
                activities_created += 1
                
                if activities_created % 50 == 0:
                    print(f"Created {activities_created} activity entries...")
                    
            except Exception as e:
                print(f"Error inserting activity: {e}")
                continue
    
    print(f"\nSuccessfully created {activities_created} activity log entries!")
    
    # Show some statistics
    try:
        total_count = execute_query_one("SELECT COUNT(*) as count FROM activity_log")['count']
        today_count = execute_query_one("""
            SELECT COUNT(*) as count FROM activity_log 
            WHERE DATE(timestamp) = CURRENT_DATE
        """)['count']
        
        print(f"Total activities in database: {total_count}")
        print(f"Activities created today: {today_count}")
        
        # Show activity types breakdown
        print("\nActivity types breakdown:")
        activity_breakdown = execute_query("""
            SELECT action_type, COUNT(*) as count 
            FROM activity_log 
            GROUP BY action_type 
            ORDER BY count DESC
        """)
        
        for item in activity_breakdown:
            print(f"  {item['action_type']}: {item['count']}")
            
    except Exception as e:
        print(f"Error getting statistics: {e}")

def clear_existing_test_data():
    """Clear existing test activity data"""
    try:
        print("Clearing existing activity log data...")
        result = execute_update("DELETE FROM activity_log")
        print("Existing activity data cleared.")
    except Exception as e:
        print(f"Error clearing existing data: {e}")

def main():
    """Main function"""
    print("=== Rally Activity Log Test Data Population ===")
    print()
    
    # Ask user if they want to clear existing data
    while True:
        clear_choice = input("Do you want to clear existing activity data first? (y/n): ").lower()
        if clear_choice in ['y', 'yes']:
            clear_existing_test_data()
            break
        elif clear_choice in ['n', 'no']:
            break
        else:
            print("Please enter 'y' or 'n'")
    
    # Create activity entries
    create_activity_entries()
    
    print("\n=== Test data population complete! ===")
    print("You can now test the Activity Dashboard at: /admin/dashboard")

if __name__ == "__main__":
    main() 