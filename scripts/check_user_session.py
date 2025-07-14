#!/usr/bin/env python3
"""
Check user session data and team associations
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database_models import SessionLocal, User, UserPlayerAssociation, Player, Team
from app.services.session_service import get_session_data_for_user

def check_user_session():
    """Check user session data"""
    print("🔍 Checking User Session Data")
    print("=" * 50)
    
    with SessionLocal() as session:
        # Find the user
        user = session.query(User).filter(User.email == "rossfreedman@gmail.com").first()
        if not user:
            print("❌ User not found!")
            return
        
        print(f"✅ User found: {user.first_name} {user.last_name} (ID: {user.id})")
        
        # Get session data
        try:
            session_data = get_session_data_for_user(user.email)
            print(f"\n📋 Session Data:")
            print(f"   User ID: {session_data.get('id')}")
            print(f"   Email: {session_data.get('email')}")
            print(f"   Series: {session_data.get('series')}")
            print(f"   Club: {session_data.get('club')}")
            print(f"   Team ID: {session_data.get('team_id')}")
            print(f"   League ID: {session_data.get('league_id')}")
            
            # Check player associations
            associations = session.query(UserPlayerAssociation).filter(
                UserPlayerAssociation.user_id == user.id
            ).all()
            
            print(f"\n🔗 Player Associations ({len(associations)}):")
            for assoc in associations:
                print(f"   Tenniscores Player ID: {assoc.tenniscores_player_id}")
                
                # Get player details
                player = session.query(Player).filter(
                    Player.tenniscores_player_id == assoc.tenniscores_player_id
                ).first()
                
                if player:
                    print(f"     - Name: {player.first_name} {player.last_name}")
                    print(f"     - Team ID: {player.team_id}")
                    print(f"     - League ID: {player.league_id}")
                    print(f"     - Club ID: {player.club_id}")
                    print(f"     - Series ID: {player.series_id}")
                    
                    # Get team details
                    if player.team_id:
                        team = session.query(Team).filter(Team.id == player.team_id).first()
                        if team:
                            print(f"     - Team Name: {team.display_name}")
                else:
                    print(f"     - ❌ Player not found!")
            
        except Exception as e:
            print(f"❌ Error getting session data: {e}")

if __name__ == "__main__":
    check_user_session() 