#!/usr/bin/env python3
"""
Update Application Queries for tenniscores_player_id Schema
==========================================================

This script updates all application code to use the new UserPlayerAssociation schema
that uses tenniscores_player_id + league_id instead of player_id.
"""

import os
import re
import sys
from pathlib import Path

def update_file_content(file_path, updates):
    """Update a file with multiple search/replace operations"""
    print(f"🔧 Updating {file_path}...")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    changes_made = 0
    
    for old_pattern, new_pattern, description in updates:
        if old_pattern in content:
            content = content.replace(old_pattern, new_pattern)
            changes_made += 1
            print(f"   ✅ {description}")
    
    if changes_made > 0:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"   💾 Saved {changes_made} changes to {file_path}")
    else:
        print(f"   ℹ️  No changes needed in {file_path}")
    
    return changes_made

def update_api_routes():
    """Update app/routes/api_routes.py"""
    file_path = "app/routes/api_routes.py"
    
    updates = [
        # Update primary association queries
        (
            """primary_association = db_session.query(UserPlayerAssociation).filter(
                UserPlayerAssociation.user_id == user_record.id,
                UserPlayerAssociation.is_primary == True
            ).first()""",
            """primary_association = db_session.query(UserPlayerAssociation).filter(
                UserPlayerAssociation.user_id == user_record.id,
                UserPlayerAssociation.is_primary == True
            ).first()""",
            "Primary association query (no change needed - still uses user_id)"
        ),
        
        # Update association existence checks - these need player lookups
        (
            """existing = db_session.query(UserPlayerAssociation).filter(
                UserPlayerAssociation.user_id == user_record.id,
                UserPlayerAssociation.player_id == player_record.id
            ).first()""",
            """existing = db_session.query(UserPlayerAssociation).filter(
                UserPlayerAssociation.user_id == user_record.id,
                UserPlayerAssociation.tenniscores_player_id == player_record.tenniscores_player_id,
                UserPlayerAssociation.league_id == player_record.league_id
            ).first()""",
            "Association existence check - updated to use tenniscores_player_id + league_id"
        ),
        
        # Update association creation
        (
            """association = UserPlayerAssociation(
                user_id=user_record.id,
                player_id=player_record.id,
                is_primary=is_primary
            )""",
            """association = UserPlayerAssociation(
                user_id=user_record.id,
                tenniscores_player_id=player_record.tenniscores_player_id,
                league_id=player_record.league_id,
                is_primary=is_primary
            )""",
            "Association creation - updated to use tenniscores_player_id + league_id"
        ),
        
        # Update bulk primary flag reset
        (
            """db_session.query(UserPlayerAssociation).filter(
                UserPlayerAssociation.user_id == user_record.id,
                UserPlayerAssociation.is_primary == True
            ).update({UserPlayerAssociation.is_primary: False})""",
            """db_session.query(UserPlayerAssociation).filter(
                UserPlayerAssociation.user_id == user_record.id,
                UserPlayerAssociation.is_primary == True
            ).update({UserPlayerAssociation.is_primary: False})""",
            "Bulk primary flag reset (no change needed - still uses user_id)"
        ),
        
        # Update user associations query
        (
            """associations = db_session.query(UserPlayerAssociation).filter(
                UserPlayerAssociation.user_id == user_record.id
            ).all()""",
            """associations = db_session.query(UserPlayerAssociation).filter(
                UserPlayerAssociation.user_id == user_record.id
            ).all()""",
            "User associations query (no change needed - still uses user_id)"
        )
    ]
    
    return update_file_content(file_path, updates)

def update_auth_service():
    """Update app/services/auth_service_refactored.py"""
    file_path = "app/services/auth_service_refactored.py"
    
    updates = [
        # Update association existence checks
        (
            """existing = db_session.query(UserPlayerAssociation).filter(
                UserPlayerAssociation.user_id == new_user.id,
                UserPlayerAssociation.player_id == player.id
            ).first()""",
            """existing = db_session.query(UserPlayerAssociation).filter(
                UserPlayerAssociation.user_id == new_user.id,
                UserPlayerAssociation.tenniscores_player_id == player.tenniscores_player_id,
                UserPlayerAssociation.league_id == player.league_id
            ).first()""",
            "Association existence check in registration - updated to use tenniscores_player_id + league_id"
        ),
        
        # Update association creation in registration
        (
            """association = UserPlayerAssociation(
                user_id=new_user.id,
                player_id=player.id,
                is_primary=is_primary
            )""",
            """association = UserPlayerAssociation(
                user_id=new_user.id,
                tenniscores_player_id=player.tenniscores_player_id,
                league_id=player.league_id,
                is_primary=is_primary
            )""",
            "Association creation in registration - updated to use tenniscores_player_id + league_id"
        ),
        
        # Update specific user-player association queries
        (
            """existing = db_session.query(UserPlayerAssociation).filter(
                UserPlayerAssociation.user_id == user_id,
                UserPlayerAssociation.player_id == player_id
            ).first()""",
            """# Need to get player details first for new schema
            player_record = db_session.query(Player).filter(Player.id == player_id).first()
            if not player_record:
                return {'success': False, 'message': f'Player with ID {player_id} not found'}
            
            existing = db_session.query(UserPlayerAssociation).filter(
                UserPlayerAssociation.user_id == user_id,
                UserPlayerAssociation.tenniscores_player_id == player_record.tenniscores_player_id,
                UserPlayerAssociation.league_id == player_record.league_id
            ).first()""",
            "User-player association query - updated to use player lookup first"
        ),
        
        # Update association creation in add_player_association
        (
            """association = UserPlayerAssociation(
                user_id=user_id,
                player_id=player_id,
                is_primary=is_primary
            )""",
            """association = UserPlayerAssociation(
                user_id=user_id,
                tenniscores_player_id=player_record.tenniscores_player_id,
                league_id=player_record.league_id,
                is_primary=is_primary
            )""",
            "Association creation in add_player_association - updated to use tenniscores_player_id + league_id"
        )
    ]
    
    return update_file_content(file_path, updates)

def create_helper_functions():
    """Create helper functions for common association operations"""
    helper_code = '''
# Helper functions for UserPlayerAssociation operations with new schema
def find_user_player_association(db_session, user_id, player_record):
    """Find association using the new schema"""
    return db_session.query(UserPlayerAssociation).filter(
        UserPlayerAssociation.user_id == user_id,
        UserPlayerAssociation.tenniscores_player_id == player_record.tenniscores_player_id,
        UserPlayerAssociation.league_id == player_record.league_id
    ).first()

def create_user_player_association(user_id, player_record, is_primary=False):
    """Create association using the new schema"""
    return UserPlayerAssociation(
        user_id=user_id,
        tenniscores_player_id=player_record.tenniscores_player_id,
        league_id=player_record.league_id,
        is_primary=is_primary
    )

def get_user_associated_players(db_session, user_id):
    """Get all players associated with a user using the new schema"""
    associations = db_session.query(UserPlayerAssociation).filter(
        UserPlayerAssociation.user_id == user_id
    ).all()
    
    players = []
    for assoc in associations:
        player = db_session.query(Player).filter(
            Player.tenniscores_player_id == assoc.tenniscores_player_id,
            Player.league_id == assoc.league_id
        ).first()
        if player:
            players.append(player)
    
    return players
'''
    
    with open("app/utils/association_helpers.py", "w") as f:
        f.write(helper_code)
    
    print("✅ Created helper functions in app/utils/association_helpers.py")

def main():
    """Update all application code for the new schema"""
    print("🔄 UPDATING APPLICATION CODE FOR TENNISCORES_PLAYER_ID SCHEMA")
    print("=" * 70)
    
    total_changes = 0
    
    # Update main application files
    total_changes += update_api_routes()
    total_changes += update_auth_service()
    
    # Create helper functions
    create_helper_functions()
    
    print("\n" + "=" * 70)
    print(f"✅ COMPLETED: Made {total_changes} total changes")
    print("\n📝 MANUAL UPDATES NEEDED:")
    print("   1. Review all updated queries for correctness")
    print("   2. Add imports for helper functions where needed:")
    print("      from app.utils.association_helpers import find_user_player_association")
    print("   3. Test all user authentication and player association flows")
    print("   4. Update any remaining direct SQL queries in the codebase")
    
    print("\n⚠️  IMPORTANT: Run migration script BEFORE deploying these code changes!")

if __name__ == "__main__":
    main() 