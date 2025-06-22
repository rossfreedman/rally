#!/usr/bin/env python3
"""
Test Team Assignment Fix
========================

This test verifies that the team assignment fix works correctly during user registration.
It ensures that new users get proper team assignments and can immediately use team-based features.
"""

import os
import sys

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database_models import (
    Club,
    League,
    Player,
    Series,
    SessionLocal,
    Team,
    User,
    UserPlayerAssociation,
)

# Import directly to avoid blueprint import issues
from app.services.auth_service_refactored import (
    assign_player_to_team,
    fix_team_assignments_for_existing_users,
    register_user,
)


def test_team_assignment_during_registration():
    """Test that team assignment works during user registration"""
    print("🧪 Testing team assignment during registration...")

    # Test registration data
    test_data = {
        "email": "teamtest@example.com",
        "password": "password123",
        "first_name": "Team",
        "last_name": "Test",
        "league_name": "Test League",
        "club_name": "Test Club",
        "series_name": "Test Series",
    }

    db_session = SessionLocal()

    try:
        # Clean up any existing test data
        existing_user = (
            db_session.query(User).filter(User.email == test_data["email"]).first()
        )
        if existing_user:
            # Delete associations first
            db_session.query(UserPlayerAssociation).filter(
                UserPlayerAssociation.user_id == existing_user.id
            ).delete()
            db_session.delete(existing_user)
            db_session.commit()

        # Create test infrastructure (league, club, series, team)
        print("📝 Setting up test infrastructure...")

        # Create league
        league = League(league_id="TEST_LEAGUE", league_name=test_data["league_name"])
        db_session.add(league)
        db_session.flush()

        # Create club
        club = Club(name=test_data["club_name"])
        db_session.add(club)
        db_session.flush()

        # Create series
        series = Series(name=test_data["series_name"])
        db_session.add(series)
        db_session.flush()

        # Create team
        team = Team(
            club_id=club.id,
            series_id=series.id,
            league_id=league.id,
            team_name=f"{club.name} {series.name}",
            is_active=True,
        )
        db_session.add(team)
        db_session.flush()

        # Create a test player
        player = Player(
            tenniscores_player_id="TEST_PLAYER_001",
            first_name=test_data["first_name"],
            last_name=test_data["last_name"],
            league_id=league.id,
            club_id=club.id,
            series_id=series.id,
            team_id=None,  # Initially no team assignment
            is_active=True,
        )
        db_session.add(player)
        db_session.commit()

        print("✅ Test infrastructure created")

        # Test the registration process
        print("🚀 Testing registration with team assignment...")

        result = register_user(
            email=test_data["email"],
            password=test_data["password"],
            first_name=test_data["first_name"],
            last_name=test_data["last_name"],
            league_name=test_data["league_name"],
            club_name=test_data["club_name"],
            series_name=test_data["series_name"],
        )

        print(f"📊 Registration result: {result}")

        # Verify registration was successful
        assert result[
            "success"
        ], f"Registration failed: {result.get('error', 'Unknown error')}"

        # Verify user was created
        user = db_session.query(User).filter(User.email == test_data["email"]).first()
        assert user is not None, "User was not created"
        print("✅ User created successfully")

        # Verify player association was created
        association = (
            db_session.query(UserPlayerAssociation)
            .filter(UserPlayerAssociation.user_id == user.id)
            .first()
        )
        assert association is not None, "User-player association was not created"
        print("✅ Player association created")

        # Verify player has team assignment
        updated_player = (
            db_session.query(Player)
            .filter(Player.tenniscores_player_id == association.tenniscores_player_id)
            .first()
        )
        assert updated_player is not None, "Player not found"
        assert (
            updated_player.team_id is not None
        ), "Player does not have team assignment"
        assert (
            updated_player.team_id == team.id
        ), f"Player assigned to wrong team: {updated_player.team_id} != {team.id}"

        print(
            f"✅ Player assigned to team: {updated_player.team_id} ({team.team_name})"
        )

        # Verify the team relationship works
        player_team = (
            db_session.query(Team).filter(Team.id == updated_player.team_id).first()
        )
        assert player_team is not None, "Team not found"
        assert player_team.team_name == team.team_name, "Wrong team assigned"

        print("🎉 ALL TESTS PASSED!")
        print(
            f"✅ User {test_data['email']} can now create polls and use team features"
        )

        return True

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Clean up test data
        try:
            if "user" in locals() and user:
                # Delete associations
                db_session.query(UserPlayerAssociation).filter(
                    UserPlayerAssociation.user_id == user.id
                ).delete()
                # Delete user
                db_session.delete(user)

            if "player" in locals() and player:
                db_session.delete(player)
            if "team" in locals() and team:
                db_session.delete(team)
            if "series" in locals() and series:
                db_session.delete(series)
            if "club" in locals() and club:
                db_session.delete(club)
            if "league" in locals() and league:
                db_session.delete(league)

            db_session.commit()
            print("🧹 Test cleanup completed")

        except Exception as cleanup_error:
            print(f"⚠️  Cleanup error: {cleanup_error}")
            db_session.rollback()
        finally:
            db_session.close()


def test_retroactive_fix():
    """Test that the retroactive fix works for existing users"""
    print("\n🧪 Testing retroactive team assignment fix...")

    # Run the fix
    result = fix_team_assignments_for_existing_users()

    print(f"📊 Fix result: {result}")

    if result["success"]:
        print(
            f"✅ Fixed {result['fixed_count']} out of {result['total_players']} players"
        )
        if result["failed_count"] > 0:
            print(f"⚠️  {result['failed_count']} players could not be fixed")
    else:
        print(f"❌ Fix failed: {result['error']}")

    return result["success"]


if __name__ == "__main__":
    print("🚀 Running Team Assignment Fix Tests")
    print("=" * 50)

    # Test 1: Registration with team assignment
    test1_success = test_team_assignment_during_registration()

    # Test 2: Retroactive fix
    test2_success = test_retroactive_fix()

    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print(f"Registration Test: {'✅ PASSED' if test1_success else '❌ FAILED'}")
    print(f"Retroactive Fix Test: {'✅ PASSED' if test2_success else '❌ FAILED'}")

    if test1_success and test2_success:
        print("\n🎉 ALL TESTS PASSED! Team assignment fix is working correctly.")
    else:
        print("\n❌ SOME TESTS FAILED! Please check the implementation.")
        sys.exit(1)
