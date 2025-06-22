#!/usr/bin/env python3
"""
Script to fix Ross Freedman's missing tenniscores_player_id in the database.
This addresses the issue where the user analysis page shows "No analysis data available".
"""

import os
import sys

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query


def fix_ross_player_id():
    """Update Ross Freedman's tenniscores_player_id in the database"""

    # Ross Freedman's correct player_id from the player_history.json file
    player_id = "nndz-WkMrK3didjlnUT09"
    email = "rossfreedman@gmail.com"

    try:
        # First, check current state - tenniscores_player_id is now in players table
        current_user = execute_query(
            "SELECT first_name, last_name, email FROM users WHERE email = %(email)s",
            {"email": email},
        )

        if not current_user:
            print(f"❌ User with email {email} not found!")
            return False

        user = current_user[0]
        player_name = f"{user['first_name']} {user['last_name']}"
        print(f"📋 Current user data:")
        print(f"   Name: {player_name}")
        print(f"   Email: {user['email']}")

        # Check if player record exists in players table
        player_record = execute_query(
            "SELECT tenniscores_player_id FROM players WHERE CONCAT(first_name, ' ', last_name) = %(player_name)s",
            {"player_name": player_name},
        )

        if player_record:
            current_player_id = player_record[0]["tenniscores_player_id"]
            print(f"   Current player_id in players table: {current_player_id}")

            if current_player_id == player_id:
                print(f"✅ Player ID is already correct!")
                return True
            else:
                # Update the tenniscores_player_id in players table
                execute_query(
                    "UPDATE players SET tenniscores_player_id = %(player_id)s WHERE CONCAT(first_name, ' ', last_name) = %(player_name)s",
                    {"player_id": player_id, "player_name": player_name},
                )
        else:
            print(f"❌ No player record found for {player_name} in players table!")
            return False

        # Verify the update
        updated_player = execute_query(
            "SELECT tenniscores_player_id FROM players WHERE CONCAT(first_name, ' ', last_name) = %(player_name)s",
            {"player_name": player_name},
        )[0]

        print(f"✅ Updated player data:")
        print(f"   Name: {player_name}")
        print(f"   New player_id: {updated_player['tenniscores_player_id']}")

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
