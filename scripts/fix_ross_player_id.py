#!/usr/bin/env python3
"""
Script to fix Ross Freedman's missing tenniscores_player_id in the database.
This addresses the issue where the user analysis page shows "No analysis data available".
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query

def fix_ross_player_id():
    """Update Ross Freedman's tenniscores_player_id in the database"""
    
    # Ross Freedman's correct player_id from the player_history.json file
    player_id = "nndz-WkMrK3didjlnUT09"
    email = "rossfreedman@gmail.com"
    
    try:
        # First, check current state
        current_user = execute_query(
            "SELECT first_name, last_name, email, tenniscores_player_id FROM users WHERE email = %(email)s",
            {'email': email}
        )
        
        if not current_user:
            print(f"❌ User with email {email} not found!")
            return False
            
        user = current_user[0]
        print(f"📋 Current user data:")
        print(f"   Name: {user['first_name']} {user['last_name']}")
        print(f"   Email: {user['email']}")
        print(f"   Current player_id: {user['tenniscores_player_id']}")
        
        # Update the tenniscores_player_id
        execute_query(
            "UPDATE users SET tenniscores_player_id = %(player_id)s WHERE email = %(email)s",
            {'player_id': player_id, 'email': email}
        )
        
        # Verify the update
        updated_user = execute_query(
            "SELECT first_name, last_name, email, tenniscores_player_id FROM users WHERE email = %(email)s",
            {'email': email}
        )[0]
        
        print(f"✅ Updated user data:")
        print(f"   Name: {updated_user['first_name']} {updated_user['last_name']}")
        print(f"   Email: {updated_user['email']}")
        print(f"   New player_id: {updated_user['tenniscores_player_id']}")
        
        print(f"🎉 Successfully updated Ross Freedman's player_id!")
        return True
        
    except Exception as e:
        print(f"❌ Error updating player_id: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔧 Fixing Ross Freedman's missing tenniscores_player_id...")
    success = fix_ross_player_id()
    
    if success:
        print("\n✅ Player analysis should now work correctly!")
        print("💡 Try accessing http://127.0.0.1:8080/mobile/analyze-me again")
    else:
        print("\n❌ Failed to fix the issue. Please check the error messages above.") 