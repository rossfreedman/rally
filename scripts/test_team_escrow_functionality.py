#!/usr/bin/env python3
"""
Test script to verify team ID functionality in lineup escrow
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database_models import SessionLocal, LineupEscrow, Team, Player
from app.services.lineup_escrow_service import LineupEscrowService

def test_team_escrow_functionality():
    """Test the new team ID functionality in lineup escrow"""
    
    print("🧪 Testing Team ID Functionality in Lineup Escrow")
    print("=" * 60)
    
    try:
        with SessionLocal() as db_session:
            escrow_service = LineupEscrowService(db_session)
            
            # Test 1: Check if team ID columns exist
            print("\n✅ Test 1: Checking database schema...")
            escrow = db_session.query(LineupEscrow).first()
            if hasattr(escrow, 'initiator_team_id') and hasattr(escrow, 'recipient_team_id'):
                print("   ✅ Team ID columns exist in database")
            else:
                print("   ❌ Team ID columns missing from database")
                return
            
            # Test 2: Get some sample teams
            print("\n✅ Test 2: Getting sample teams...")
            teams = db_session.query(Team).limit(3).all()
            if teams:
                print(f"   ✅ Found {len(teams)} sample teams")
                for team in teams:
                    print(f"      - {team.display_name} (ID: {team.id})")
            else:
                print("   ❌ No teams found in database")
                return
            
            # Test 3: Get some sample players
            print("\n✅ Test 3: Getting sample players...")
            players = db_session.query(Player).limit(3).all()
            if players:
                print(f"   ✅ Found {len(players)} sample players")
                for player in players:
                    team_name = "No Team"
                    if player.team_id:
                        team = db_session.query(Team).filter(Team.id == player.team_id).first()
                        if team:
                            team_name = team.display_name
                    print(f"      - {player.first_name} {player.last_name} -> {team_name}")
            else:
                print("   ❌ No players found in database")
                return
            
            # Test 4: Test player search functionality
            print("\n✅ Test 4: Testing player search...")
            if players:
                test_player = players[0]
                search_name = f"{test_player.first_name} {test_player.last_name}"
                print(f"   🔍 Searching for: {search_name}")
                
                # Simulate the search logic
                name_parts = search_name.split()
                if len(name_parts) >= 2:
                    first_name = name_parts[0]
                    last_name = name_parts[-1]
                    
                    found_players = db_session.query(Player).filter(
                        (Player.first_name.ilike(f"%{first_name}%") & Player.last_name.ilike(f"%{last_name}%")) |
                        (Player.first_name.ilike(f"%{last_name}%") & Player.last_name.ilike(f"%{first_name}%"))
                    ).all()
                    
                    if found_players:
                        print(f"   ✅ Found {len(found_players)} players matching search")
                        for player in found_players:
                            if player.team_id:
                                team = db_session.query(Team).filter(Team.id == player.team_id).first()
                                if team:
                                    print(f"      - {player.first_name} {player.last_name} -> {team.display_name}")
                    else:
                        print("   ❌ No players found matching search")
            
            # Test 5: Test escrow creation with team IDs
            print("\n✅ Test 5: Testing escrow creation with team IDs...")
            if teams and len(teams) >= 2:
                initiator_team = teams[0]
                recipient_team = teams[1]
                
                print(f"   🏠 Initiator Team: {initiator_team.display_name} (ID: {initiator_team.id})")
                print(f"   🏠 Recipient Team: {recipient_team.display_name} (ID: {recipient_team.id})")
                
                # Create a test escrow with team IDs
                result = escrow_service.create_escrow_session(
                    initiator_user_id=915,  # Use existing user ID
                    recipient_name=recipient_team.display_name,
                    recipient_contact="test@example.com",
                    contact_type="email",
                    initiator_lineup="Test lineup data",
                    subject="Test Escrow",
                    message_body="Test message",
                    initiator_team_id=initiator_team.id,
                    recipient_team_id=recipient_team.id
                )
                
                if result["success"]:
                    print("   ✅ Escrow created successfully with team IDs")
                    
                    # Test 6: Verify team names in escrow details
                    print("\n✅ Test 6: Verifying team names in escrow details...")
                    escrow_details = escrow_service.get_escrow_details(
                        result["escrow_token"], 
                        "test@example.com"
                    )
                    
                    if escrow_details["success"]:
                        escrow_data = escrow_details["escrow"]
                        print(f"   ✅ Initiator Team Name: {escrow_data.get('initiator_team_name', 'Not found')}")
                        print(f"   ✅ Recipient Team Name: {escrow_data.get('recipient_team_name', 'Not found')}")
                        
                        if escrow_data.get('initiator_team_name') == initiator_team.display_name:
                            print("   ✅ Initiator team name matches correctly")
                        else:
                            print("   ❌ Initiator team name mismatch")
                            
                        if escrow_data.get('recipient_team_name') == recipient_team.display_name:
                            print("   ✅ Recipient team name matches correctly")
                        else:
                            print("   ❌ Recipient team name mismatch")
                    else:
                        print(f"   ❌ Failed to get escrow details: {escrow_details.get('error')}")
                else:
                    print(f"   ❌ Failed to create escrow: {result.get('error')}")
            else:
                print("   ❌ Need at least 2 teams to test escrow creation")
            
            print("\n🎉 Team ID functionality tests completed!")
            
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_team_escrow_functionality() 