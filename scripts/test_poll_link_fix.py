#!/usr/bin/env python3

"""
Test script for poll link fix
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one

def test_poll_link_fix():
    """Test that poll notifications generate correct links"""
    
    print("=== Testing Poll Link Fix ===")
    
    try:
        # Test 1: Check if polls table exists and has data
        print("\n1. Checking polls table...")
        
        polls_check = execute_query_one("""
            SELECT COUNT(*) as poll_count
            FROM polls
        """)
        
        poll_count = polls_check["poll_count"] if polls_check else 0
        print(f"   Found {poll_count} polls in database")
        
        if poll_count == 0:
            print("   ⚠️  No polls found - creating test poll...")
            
            # Create a test poll
            from database_utils import execute_update
            test_poll_query = """
                INSERT INTO polls (question, team_id, created_by, created_at)
                VALUES (%s, %s, %s, NOW())
                RETURNING id
            """
            
            # Get a sample team and user
            team_result = execute_query_one("SELECT id FROM teams LIMIT 1")
            user_result = execute_query_one("SELECT id FROM users LIMIT 1")
            
            if team_result and user_result:
                poll_id = execute_update(test_poll_query, [
                    "Test poll question for link testing",
                    team_result["id"],
                    user_result["id"]
                ])
                print(f"   ✅ Created test poll with ID: {poll_id}")
                
                # Create test choices
                choices_query = """
                    INSERT INTO poll_choices (poll_id, choice_text)
                    VALUES (%s, %s), (%s, %s)
                """
                execute_update(choices_query, [
                    poll_id, "Choice 1",
                    poll_id, "Choice 2"
                ])
                print("   ✅ Created test poll choices")
            else:
                print("   ❌ Could not create test poll - no teams or users found")
                return False
        else:
            print("   ✅ Polls exist in database")
        
        # Test 2: Test the poll notifications function
        print("\n2. Testing poll notifications function...")
        
        # Import the function
        from app.routes.api_routes import get_team_poll_notifications
        
        # Get a team ID that has polls
        team_result = execute_query_one("""
            SELECT team_id 
            FROM polls 
            WHERE team_id IS NOT NULL 
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        if not team_result:
            print("   ❌ No teams with polls found in database")
            return False
        
        team_id = team_result["team_id"]
        print(f"   Using team ID: {team_id}")
        
        # Test the function with dummy parameters
        notifications = get_team_poll_notifications(
            user_id=1,  # Dummy user ID
            player_id="test",  # Dummy player ID
            league_id=1,  # Dummy league ID
            team_id=team_id
        )
        
        print(f"   Generated {len(notifications)} notifications")
        
        # Check the link format
        for notification in notifications:
            if notification.get("type") == "team" and "poll" in notification.get("id", ""):
                link = notification.get("cta", {}).get("href", "")
                print(f"   Poll notification link: {link}")
                
                # Verify the link format is correct
                if link.startswith("/mobile/polls/"):
                    print("   ✅ Link format is correct!")
                    return True
                else:
                    print(f"   ❌ Link format is incorrect: {link}")
                    return False
        
        print("   ⚠️  No poll notifications found")
        return False
        
    except Exception as e:
        print(f"   ❌ Error testing poll link fix: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_poll_link_fix()
    if success:
        print("\n✅ Poll link fix test passed!")
    else:
        print("\n❌ Poll link fix test failed!")
        sys.exit(1) 