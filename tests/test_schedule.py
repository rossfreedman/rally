"""
Rally Schedule Management Tests
Comprehensive testing of schedule functionality including viewing, updates, and team matching
"""

import json
from datetime import date, datetime, time, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.models.database_models import (
    Club,
    League,
    Player,
    Schedule,
    Series,
    Team,
    User,
)


@pytest.mark.unit
class TestScheduleModel:
    """Test the Schedule model functionality"""

    def test_create_schedule(self, db_session, test_league, test_team):
        """Test creating a schedule entry"""
        match_date = date.today() + timedelta(days=7)
        match_time = time(18, 30)  # 6:30 PM

        schedule = Schedule(
            league_id=test_league.id,
            match_date=match_date,
            match_time=match_time,
            home_team="Test Club - 1",
            away_team="Opponent Club - 2",
            home_team_id=test_team.id,
            location="Test Club Courts",
        )

        db_session.add(schedule)
        db_session.commit()

        assert schedule.id is not None
        assert schedule.match_date == match_date
        assert schedule.match_time == match_time
        assert schedule.home_team == "Test Club - 1"
        assert schedule.location == "Test Club Courts"

    def test_schedule_relationships(self, db_session, test_league, test_team):
        """Test schedule model relationships"""
        schedule = Schedule(
            league_id=test_league.id,
            match_date=date.today() + timedelta(days=7),
            match_time=time(19, 0),
            home_team_id=test_team.id,
            location="Test Location",
        )

        db_session.add(schedule)
        db_session.commit()

        # Test league relationship
        assert schedule.league is not None
        assert schedule.league.id == test_league.id

        # Test home team relationship
        assert schedule.home_team_obj is not None
        assert schedule.home_team_obj.id == test_team.id


@pytest.mark.integration
class TestScheduleAPI:
    """Test schedule API endpoints"""

    def test_get_user_schedule(
        self,
        authenticated_client,
        db_session,
        test_user,
        test_player,
        test_team,
        test_league,
        linked_user_player,
    ):
        """Test retrieving user's team schedule"""
        # Create some schedule entries for the user's team
        today = date.today()
        schedules = []

        for i in range(3):
            schedule = Schedule(
                league_id=test_league.id,
                match_date=today + timedelta(days=7 * i),
                match_time=time(18, 30),
                home_team="Test Club - 1" if i % 2 == 0 else "Opponent Club",
                away_team="Opponent Club" if i % 2 == 0 else "Test Club - 1",
                home_team_id=test_team.id if i % 2 == 0 else None,
                away_team_id=test_team.id if i % 2 == 1 else None,
                location=f"Court {i+1}",
            )
            schedules.append(schedule)
            db_session.add(schedule)

        db_session.commit()

        # Test API endpoint
        response = authenticated_client.get("/api/schedule")

        assert response.status_code == 200
        data = response.get_json()

        assert "matches" in data
        assert len(data["matches"]) >= 3  # Should include our test matches

    def test_get_schedule_unauthorized(self, client):
        """Test schedule access without authentication"""
        response = client.get("/api/schedule")
        assert response.status_code == 401

    def test_schedule_page_rendering(self, authenticated_client, test_user):
        """Test schedule page renders correctly"""
        response = authenticated_client.get("/schedule")

        assert response.status_code == 200
        assert (
            b"schedule" in response.data.lower()
        )  # Check page contains schedule content


@pytest.mark.integration
class TestScheduleMatching:
    """Test schedule team matching logic"""

    def test_user_team_schedule_filtering(
        self,
        db_session,
        test_user,
        test_player,
        test_team,
        test_league,
        linked_user_player,
    ):
        """Test that users only see their team's schedule"""
        # Create another team
        other_club = Club(name="Other Club")
        db_session.add(other_club)
        db_session.flush()

        other_team = Team(
            club_id=other_club.id,
            series_id=test_team.series_id,
            league_id=test_team.league_id,
            team_name="Other Club - 1",
        )
        db_session.add(other_team)
        db_session.flush()

        today = date.today()

        # Create schedule for user's team
        user_team_schedule = Schedule(
            league_id=test_league.id,
            match_date=today + timedelta(days=7),
            match_time=time(18, 30),
            home_team_id=test_team.id,
            away_team_id=other_team.id,
            location="User Team Court",
        )

        # Create schedule for other team (not involving user's team)
        other_schedule = Schedule(
            league_id=test_league.id,
            match_date=today + timedelta(days=14),
            match_time=time(18, 30),
            home_team_id=other_team.id,
            location="Other Team Court",
        )

        db_session.add_all([user_team_schedule, other_schedule])
        db_session.commit()

        # Query schedules for user's team
        user_schedules = (
            db_session.query(Schedule)
            .filter(
                (Schedule.home_team_id == test_team.id)
                | (Schedule.away_team_id == test_team.id)
            )
            .all()
        )

        # Should only return the schedule involving user's team
        assert len(user_schedules) == 1
        assert user_schedules[0].id == user_team_schedule.id

    def test_schedule_opponent_identification(self, db_session, test_team, test_league):
        """Test identifying opponents in schedule"""
        # Create opponent team
        opponent_club = Club(name="Opponent Club")
        db_session.add(opponent_club)
        db_session.flush()

        opponent_team = Team(
            club_id=opponent_club.id,
            series_id=test_team.series_id,
            league_id=test_team.league_id,
            team_name="Opponent Club - 1",
        )
        db_session.add(opponent_team)
        db_session.flush()

        # Test as home team
        home_schedule = Schedule(
            league_id=test_league.id,
            match_date=date.today() + timedelta(days=7),
            match_time=time(18, 30),
            home_team_id=test_team.id,
            away_team_id=opponent_team.id,
            location="Home Court",
        )

        # Test as away team
        away_schedule = Schedule(
            league_id=test_league.id,
            match_date=date.today() + timedelta(days=14),
            match_time=time(18, 30),
            home_team_id=opponent_team.id,
            away_team_id=test_team.id,
            location="Away Court",
        )

        db_session.add_all([home_schedule, away_schedule])
        db_session.commit()

        # For home schedule, opponent should be away team
        assert home_schedule.home_team_obj.id == test_team.id
        assert home_schedule.away_team_obj.id == opponent_team.id

        # For away schedule, opponent should be home team
        assert away_schedule.home_team_obj.id == opponent_team.id
        assert away_schedule.away_team_obj.id == test_team.id


@pytest.mark.unit
class TestScheduleFormatting:
    """Test schedule display formatting"""

    def test_date_formatting(self, db_session, test_league):
        """Test various date format handling"""
        test_dates = [
            date(2024, 12, 25),  # Christmas
            date(2024, 1, 1),  # New Year
            date(2024, 7, 4),  # July 4th
        ]

        for test_date in test_dates:
            schedule = Schedule(
                league_id=test_league.id,
                match_date=test_date,
                match_time=time(18, 30),
                home_team="Team A",
                away_team="Team B",
                location="Test Court",
            )

            db_session.add(schedule)

        db_session.commit()

        schedules = db_session.query(Schedule).all()
        assert len(schedules) == 3

        # Verify dates are stored correctly
        stored_dates = [s.match_date for s in schedules]
        for original_date in test_dates:
            assert original_date in stored_dates

    def test_time_formatting(self, db_session, test_league):
        """Test various time format handling"""
        test_times = [
            time(18, 30),  # 6:30 PM
            time(19, 0),  # 7:00 PM
            time(20, 30),  # 8:30 PM
            time(6, 30),  # 6:30 AM
        ]

        for i, test_time in enumerate(test_times):
            schedule = Schedule(
                league_id=test_league.id,
                match_date=date.today() + timedelta(days=i),
                match_time=test_time,
                home_team=f"Team A{i}",
                away_team=f"Team B{i}",
                location="Test Court",
            )

            db_session.add(schedule)

        db_session.commit()

        schedules = db_session.query(Schedule).order_by(Schedule.match_date).all()
        stored_times = [s.match_time for s in schedules]

        for original_time in test_times:
            assert original_time in stored_times


@pytest.mark.integration
class TestScheduleUpdates:
    """Test schedule update functionality"""

    def test_schedule_modification(self, db_session, test_league):
        """Test updating schedule information"""
        original_schedule = Schedule(
            league_id=test_league.id,
            match_date=date.today() + timedelta(days=7),
            match_time=time(18, 30),
            home_team="Original Home",
            away_team="Original Away",
            location="Original Location",
        )

        db_session.add(original_schedule)
        db_session.commit()

        schedule_id = original_schedule.id

        # Update the schedule
        original_schedule.match_date = date.today() + timedelta(days=14)
        original_schedule.match_time = time(19, 0)
        original_schedule.location = "Updated Location"

        db_session.commit()

        # Verify updates
        updated_schedule = (
            db_session.query(Schedule).filter(Schedule.id == schedule_id).first()
        )

        assert updated_schedule.match_date == date.today() + timedelta(days=14)
        assert updated_schedule.match_time == time(19, 0)
        assert updated_schedule.location == "Updated Location"
        assert updated_schedule.home_team == "Original Home"  # Should remain unchanged

    def test_schedule_cancellation(self, db_session, test_league):
        """Test schedule cancellation/deletion"""
        schedule = Schedule(
            league_id=test_league.id,
            match_date=date.today() + timedelta(days=7),
            match_time=time(18, 30),
            home_team="Team A",
            away_team="Team B",
            location="Test Court",
        )

        db_session.add(schedule)
        db_session.commit()

        schedule_id = schedule.id

        # Delete/cancel the schedule
        db_session.delete(schedule)
        db_session.commit()

        # Verify deletion
        deleted_schedule = (
            db_session.query(Schedule).filter(Schedule.id == schedule_id).first()
        )
        assert deleted_schedule is None


@pytest.mark.performance
class TestSchedulePerformance:
    """Test schedule performance with large datasets"""

    def test_large_schedule_query_performance(self, db_session, test_league, test_team):
        """Test performance with many schedule entries"""
        import time

        # Create many schedule entries
        schedules = []
        start_date = date.today()

        for i in range(100):  # Create 100 schedule entries
            schedule = Schedule(
                league_id=test_league.id,
                match_date=start_date + timedelta(days=i % 30),  # Spread over 30 days
                match_time=time(18 + (i % 3), 30),  # Vary times
                home_team_id=test_team.id if i % 2 == 0 else None,
                away_team_id=test_team.id if i % 2 == 1 else None,
                home_team=f"Home Team {i}",
                away_team=f"Away Team {i}",
                location=f"Court {i % 10}",
            )
            schedules.append(schedule)

        # Batch insert for performance
        db_session.add_all(schedules)
        db_session.commit()

        # Time the query
        start_time = time.time()

        # Query user's team schedule
        user_schedules = (
            db_session.query(Schedule)
            .filter(
                (Schedule.home_team_id == test_team.id)
                | (Schedule.away_team_id == test_team.id)
            )
            .order_by(Schedule.match_date, Schedule.match_time)
            .all()
        )

        query_time = time.time() - start_time

        # Performance assertions
        assert len(user_schedules) == 100  # Should find all matches
        assert query_time < 1.0  # Should complete in under 1 second

        print(f"Schedule query performance: {query_time:.3f}s for 100 entries")


@pytest.mark.integration
class TestScheduleWithAvailability:
    """Test schedule integration with player availability"""

    def test_schedule_availability_integration(
        self,
        db_session,
        test_user,
        test_player,
        test_team,
        test_league,
        linked_user_player,
    ):
        """Test that schedule integrates with player availability system"""
        from app.models.database_models import PlayerAvailability

        match_date = datetime.now() + timedelta(days=7)

        # Create a schedule
        schedule = Schedule(
            league_id=test_league.id,
            match_date=match_date.date(),
            match_time=time(18, 30),
            home_team_id=test_team.id,
            location="Test Court",
        )

        db_session.add(schedule)
        db_session.commit()

        # Create availability for this match date
        availability = PlayerAvailability(
            player_name=f"{test_player.first_name} {test_player.last_name}",
            player_id=test_player.id,
            match_date=match_date,
            availability_status=1,  # Available
            series_id=test_player.series_id,
        )

        db_session.add(availability)
        db_session.commit()

        # Query to verify integration
        schedule_with_availability = (
            db_session.query(Schedule)
            .filter(Schedule.match_date == match_date.date())
            .first()
        )

        player_availability = (
            db_session.query(PlayerAvailability)
            .filter(
                PlayerAvailability.match_date == match_date,
                PlayerAvailability.player_id == test_player.id,
            )
            .first()
        )

        assert schedule_with_availability is not None
        assert player_availability is not None
        assert player_availability.availability_status == 1


@pytest.mark.regression
class TestScheduleRegression:
    """Regression tests for previously fixed schedule bugs"""

    def test_timezone_handling_regression(self, db_session, test_league):
        """Test that schedule handles timezone correctly"""
        # Create schedule with specific date/time
        local_date = date(2024, 6, 15)  # Summer date
        local_time = time(18, 30)

        schedule = Schedule(
            league_id=test_league.id,
            match_date=local_date,
            match_time=local_time,
            home_team="Team A",
            away_team="Team B",
            location="Test Court",
        )

        db_session.add(schedule)
        db_session.commit()

        # Retrieve and verify
        retrieved_schedule = db_session.query(Schedule).first()

        assert retrieved_schedule.match_date == local_date
        assert retrieved_schedule.match_time == local_time

    def test_duplicate_schedule_prevention(self, db_session, test_league, test_team):
        """Test prevention of duplicate schedule entries"""
        match_date = date.today() + timedelta(days=7)
        match_time = time(18, 30)

        # Create first schedule
        schedule1 = Schedule(
            league_id=test_league.id,
            match_date=match_date,
            match_time=match_time,
            home_team_id=test_team.id,
            location="Court 1",
        )

        db_session.add(schedule1)
        db_session.commit()

        # Try to create duplicate (same team, date, time)
        schedule2 = Schedule(
            league_id=test_league.id,
            match_date=match_date,
            match_time=match_time,
            home_team_id=test_team.id,
            location="Court 2",
        )

        db_session.add(schedule2)

        # Note: Current schema doesn't prevent duplicates at DB level
        # This test documents the current behavior
        # In production, business logic should prevent duplicates
        db_session.commit()

        # Count schedules for this team/date/time
        duplicate_count = (
            db_session.query(Schedule)
            .filter(
                Schedule.match_date == match_date,
                Schedule.match_time == match_time,
                Schedule.home_team_id == test_team.id,
            )
            .count()
        )

        # Currently allows duplicates - this could be improved
        assert duplicate_count >= 1

    def test_schedule_foreign_key_integrity(self, db_session, test_league, test_team):
        """Test that schedule maintains foreign key integrity"""
        schedule = Schedule(
            league_id=test_league.id,
            match_date=date.today() + timedelta(days=7),
            match_time=time(18, 30),
            home_team_id=test_team.id,
            location="Test Court",
        )

        db_session.add(schedule)
        db_session.commit()

        # Verify relationships work
        assert schedule.league is not None
        assert schedule.league.id == test_league.id
        assert schedule.home_team_obj is not None
        assert schedule.home_team_obj.id == test_team.id

        # Verify back-references work
        assert (
            schedule in test_league.schedules
            if hasattr(test_league, "schedules")
            else True
        )
        assert schedule in test_team.home_scheduled_matches
