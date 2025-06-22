"""
Rally Database Models - Refactored Schema
Updated to support clean separation between authentication and player data
"""

import os
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func

Base = declarative_base()

# Database session configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    # Fallback for when DATABASE_URL is not available (e.g., during migrations)
    SessionLocal = None


class User(Base):
    """
    Authentication and core user profile table
    Clean separation from player data
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(255))
    last_name = Column(String(255))
    club_automation_password = Column(String(255))  # For club automation features
    is_admin = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    last_login = Column(DateTime(timezone=True))

    # Relationships
    player_associations = relationship(
        "UserPlayerAssociation", back_populates="user", cascade="all, delete-orphan"
    )

    # Helper method to get associated players
    def get_players(self, session):
        """Get all players associated with this user"""
        from sqlalchemy.orm import joinedload

        associations = (
            session.query(UserPlayerAssociation)
            .filter(UserPlayerAssociation.user_id == self.id)
            .all()
        )

        players = []
        for assoc in associations:
            player = assoc.get_player(session)
            if player:
                players.append(player)
        return players

    def get_primary_player(self, session):
        """Get the primary player for this user"""
        assoc = (
            session.query(UserPlayerAssociation)
            .filter(
                UserPlayerAssociation.user_id == self.id,
                UserPlayerAssociation.is_primary == True,
            )
            .first()
        )

        return assoc.get_player(session) if assoc else None

    def get_player(self, session, league_id):
        """Get the player for this user in a specific league"""
        for assoc in self.player_associations:
            player = assoc.get_player(session)
            if player and player.league and player.league.league_id == league_id:
                return player
        return None

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', admin={self.is_admin})>"


class League(Base):
    """
    League organizations (APTA_CHICAGO, NSTF, etc.)
    """

    __tablename__ = "leagues"

    id = Column(Integer, primary_key=True)
    league_id = Column(
        String(255), nullable=False, unique=True
    )  # 'APTA_CHICAGO', 'NSTF'
    league_name = Column(String(255), nullable=False)
    league_url = Column(String(512))
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )

    # Relationships
    players = relationship("Player", back_populates="league")
    clubs = relationship("Club", secondary="club_leagues", back_populates="leagues")
    series = relationship(
        "Series", secondary="series_leagues", back_populates="leagues"
    )
    teams = relationship("Team", back_populates="league")

    def __repr__(self):
        return f"<League(id={self.id}, league_id='{self.league_id}', name='{self.league_name}')>"


class Club(Base):
    """
    Tennis clubs/facilities
    """

    __tablename__ = "clubs"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    club_address = Column(String(500), nullable=True)
    updated_at = Column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )

    # Relationships
    players = relationship("Player", back_populates="club")
    leagues = relationship("League", secondary="club_leagues", back_populates="clubs")
    teams = relationship("Team", back_populates="club")

    def __repr__(self):
        return f"<Club(id={self.id}, name='{self.name}')>"


class Series(Base):
    """
    Series/divisions within leagues
    """

    __tablename__ = "series"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    updated_at = Column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )

    # Relationships
    players = relationship("Player", back_populates="series")
    leagues = relationship(
        "League", secondary="series_leagues", back_populates="series"
    )
    teams = relationship("Team", back_populates="series")

    def __repr__(self):
        return f"<Series(id={self.id}, name='{self.name}')>"


class Team(Base):
    """
    Team entities representing club participation in a series within a league
    """

    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)
    club_id = Column(Integer, ForeignKey("clubs.id"), nullable=False)
    series_id = Column(Integer, ForeignKey("series.id"), nullable=False)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    team_name = Column(String(255), nullable=False)
    team_alias = Column(String(255))  # Optional display alias
    external_team_id = Column(String(255))  # For ETL mapping
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )

    # Relationships
    club = relationship("Club", back_populates="teams")
    series = relationship("Series", back_populates="teams")
    league = relationship("League", back_populates="teams")
    players = relationship("Player", back_populates="team")
    polls = relationship("Poll", back_populates="team")
    series_stats = relationship("SeriesStats", back_populates="team_obj")
    home_matches = relationship(
        "MatchScore",
        foreign_keys="MatchScore.home_team_id",
        back_populates="home_team_obj",
    )
    away_matches = relationship(
        "MatchScore",
        foreign_keys="MatchScore.away_team_id",
        back_populates="away_team_obj",
    )
    home_scheduled_matches = relationship(
        "Schedule", foreign_keys="Schedule.home_team_id", back_populates="home_team_obj"
    )
    away_scheduled_matches = relationship(
        "Schedule", foreign_keys="Schedule.away_team_id", back_populates="away_team_obj"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "club_id", "series_id", "league_id", name="unique_team_club_series_league"
        ),
    )

    @property
    def display_name(self):
        """Return team_alias if available, otherwise team_name"""
        return self.team_alias or self.team_name

    def __repr__(self):
        return f"<Team(id={self.id}, name='{self.team_name}', club='{self.club.name if self.club else None}')>"


class Player(Base):
    """
    League-specific player records with integrated statistics
    Each player-league combination is a separate record
    """

    __tablename__ = "players"

    id = Column(Integer, primary_key=True)
    tenniscores_player_id = Column(String(255), nullable=False)  # Not globally unique
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    email = Column(String(255))  # Optional, not for authentication

    # Foreign keys - required for each player record
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    club_id = Column(Integer, ForeignKey("clubs.id"), nullable=False)
    series_id = Column(Integer, ForeignKey("series.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"))  # Nullable during migration

    # Player statistics integrated directly
    pti = Column(Numeric(10, 2))  # Performance Tracking Index
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    win_percentage = Column(Numeric(5, 2), default=0.00)
    captain_status = Column(String(50))

    # Career statistics (additional columns found in database)
    career_win_percentage = Column(Numeric(5, 2))
    career_matches = Column(Integer)
    career_wins = Column(Integer)
    career_losses = Column(Integer)

    # Status and metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )

    # Relationships
    league = relationship("League", back_populates="players")
    club = relationship("Club", back_populates="players")
    series = relationship("Series", back_populates="players")
    team = relationship("Team", back_populates="players")

    # Helper method to get associated users
    def get_associated_users(self, session):
        """Get all users associated with this player"""
        associations = (
            session.query(UserPlayerAssociation)
            .filter(
                UserPlayerAssociation.tenniscores_player_id
                == self.tenniscores_player_id
            )
            .all()
        )

        users = []
        for assoc in associations:
            if assoc.user:
                users.append(assoc.user)
        return users

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "tenniscores_player_id",
            "league_id",
            "club_id",
            "series_id",
            name="unique_player_in_league_club_series",
        ),
    )

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"<Player(id={self.id}, name='{self.full_name}', league='{self.league.league_id if self.league else None}')>"


class UserPlayerAssociation(Base):
    """
    Junction table linking users to their player records using stable identifiers
    Uses tenniscores_player_id only - league is derived from player data
    This makes associations ETL-resilient and fully normalized
    """

    __tablename__ = "user_player_associations"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    tenniscores_player_id = Column(String(255), nullable=False, primary_key=True)
    is_primary = Column(Boolean, default=False)  # Mark primary player association
    created_at = Column(DateTime(timezone=True), default=func.now())

    # Relationships
    user = relationship("User", back_populates="player_associations")

    # Helper method to get associated player
    def get_player(self, session):
        """Get the associated player record (league derived from player)"""
        # Get all players with this tenniscores_player_id
        players = (
            session.query(Player)
            .filter(Player.tenniscores_player_id == self.tenniscores_player_id)
            .all()
        )

        if not players:
            return None
        elif len(players) == 1:
            return players[0]
        else:
            # Multiple players with same tenniscores_player_id
            # Prefer players from Tennaqua club (user's preferred registration)
            tennaqua_players = [
                p for p in players if p.club and p.club.name == "Tennaqua"
            ]
            if tennaqua_players:
                return tennaqua_players[0]

            # If no Tennaqua player, return first one (existing behavior)
            return players[0]

    # Helper method to get league information
    def get_league(self, session):
        """Get the league for this association (derived from player)"""
        player = self.get_player(session)
        return player.league if player else None

    def __repr__(self):
        return f"<UserPlayerAssociation(user_id={self.user_id}, tenniscores_player_id='{self.tenniscores_player_id}', primary={self.is_primary})>"


# Junction tables for many-to-many relationships
class ClubLeague(Base):
    """Club-League associations"""

    __tablename__ = "club_leagues"

    id = Column(Integer, primary_key=True)
    club_id = Column(Integer, ForeignKey("clubs.id"), nullable=False)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())

    __table_args__ = (
        UniqueConstraint("club_id", "league_id", name="unique_club_league"),
    )


class SeriesLeague(Base):
    """Series-League associations"""

    __tablename__ = "series_leagues"

    id = Column(Integer, primary_key=True)
    series_id = Column(Integer, ForeignKey("series.id"), nullable=False)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())

    __table_args__ = (
        UniqueConstraint("series_id", "league_id", name="unique_series_league"),
    )


# Activity and data tables
class PlayerAvailability(Base):
    """Player availability for matches"""

    __tablename__ = "player_availability"

    id = Column(Integer, primary_key=True)
    player_name = Column(String(255), nullable=False)  # Kept for backward compatibility
    player_id = Column(Integer, ForeignKey("players.id"))  # New FK reference
    match_date = Column(DateTime(timezone=True), nullable=False)
    availability_status = Column(
        Integer, nullable=False, default=3
    )  # 1=available, 2=unavailable, 3=not sure
    series_id = Column(Integer, ForeignKey("series.id"), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now())
    notes = Column(
        Text, nullable=True
    )  # Optional notes from user about their availability

    # Relationships
    player = relationship("Player")
    series = relationship("Series")

    __table_args__ = (
        UniqueConstraint(
            "player_name", "match_date", "series_id", name="unique_player_availability"
        ),
    )


class UserActivityLog(Base):
    """User activity audit trail"""

    __tablename__ = "user_activity_logs"

    id = Column(Integer, primary_key=True)
    user_email = Column(String(255), nullable=False)
    activity_type = Column(String(255), nullable=False)
    page = Column(String(255))
    action = Column(Text)
    details = Column(Text)
    ip_address = Column(String(45))
    timestamp = Column(DateTime(timezone=True), default=func.now())


class UserInstruction(Base):
    """User-specific instructions"""

    __tablename__ = "user_instructions"

    id = Column(Integer, primary_key=True)
    user_email = Column(String(255), nullable=False)
    instruction = Column(Text, nullable=False)
    series_id = Column(Integer, ForeignKey("series.id"))
    team_id = Column(Integer, ForeignKey("teams.id"))  # Now properly FK constrained
    created_at = Column(DateTime(timezone=True), default=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    series = relationship("Series")
    team = relationship("Team")


class MatchScore(Base):
    """Match scores and results"""

    __tablename__ = "match_scores"

    id = Column(Integer, primary_key=True)
    league_id = Column(Integer, ForeignKey("leagues.id"))
    match_date = Column(Date)
    home_team = Column(Text)  # Keep for backward compatibility
    away_team = Column(Text)  # Keep for backward compatibility
    home_team_id = Column(Integer, ForeignKey("teams.id"))  # New team foreign keys
    away_team_id = Column(Integer, ForeignKey("teams.id"))  # New team foreign keys
    home_player_1_id = Column(Text)
    home_player_2_id = Column(Text)
    away_player_1_id = Column(Text)
    away_player_2_id = Column(Text)
    scores = Column(Text)
    winner = Column(Text)  # 'home' or 'away'
    created_at = Column(DateTime(timezone=True), default=func.now())

    # Relationships
    league = relationship("League")
    home_team_obj = relationship(
        "Team", foreign_keys=[home_team_id], back_populates="home_matches"
    )
    away_team_obj = relationship(
        "Team", foreign_keys=[away_team_id], back_populates="away_matches"
    )


class PlayerHistory(Base):
    """Historical player performance data"""

    __tablename__ = "player_history"

    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey("players.id"))
    league_id = Column(Integer, ForeignKey("leagues.id"))
    series = Column(String(255))
    date = Column(Date)
    end_pti = Column(Numeric(10, 2))  # Performance Tracking Index
    created_at = Column(DateTime(timezone=True), default=func.now())

    # Relationships
    player = relationship("Player")
    league = relationship("League")


class Schedule(Base):
    """Match scheduling"""

    __tablename__ = "schedule"

    id = Column(Integer, primary_key=True)
    league_id = Column(Integer, ForeignKey("leagues.id"))
    match_date = Column(Date)
    match_time = Column(Time)
    home_team = Column(Text)  # Keep for backward compatibility
    away_team = Column(Text)  # Keep for backward compatibility
    home_team_id = Column(Integer, ForeignKey("teams.id"))  # New team foreign keys
    away_team_id = Column(Integer, ForeignKey("teams.id"))  # New team foreign keys
    location = Column(Text)
    created_at = Column(DateTime(timezone=True), default=func.now())

    # Relationships
    league = relationship("League")
    home_team_obj = relationship(
        "Team", foreign_keys=[home_team_id], back_populates="home_scheduled_matches"
    )
    away_team_obj = relationship(
        "Team", foreign_keys=[away_team_id], back_populates="away_scheduled_matches"
    )


class SeriesStats(Base):
    """Team statistics by series"""

    __tablename__ = "series_stats"

    id = Column(Integer, primary_key=True)
    league_id = Column(Integer, ForeignKey("leagues.id"))
    series = Column(String(255))  # Keep for backward compatibility
    team = Column(String(255))  # Keep for backward compatibility
    team_id = Column(Integer, ForeignKey("teams.id"))  # New team foreign key
    points = Column(Integer)
    matches_won = Column(Integer)
    matches_lost = Column(Integer)
    matches_tied = Column(Integer)
    lines_won = Column(Integer)
    lines_lost = Column(Integer)
    lines_for = Column(Integer)
    lines_ret = Column(Integer)
    sets_won = Column(Integer)
    sets_lost = Column(Integer)
    games_won = Column(Integer)
    games_lost = Column(Integer)
    created_at = Column(DateTime(timezone=True), default=func.now())

    # Relationships
    league = relationship("League")
    team_obj = relationship("Team", back_populates="series_stats")


class Poll(Base):
    """Team polls for voting/decisions"""

    __tablename__ = "polls"

    id = Column(Integer, primary_key=True)
    team_id = Column(
        Integer, ForeignKey("teams.id")
    )  # Foreign key reference to teams table
    created_by = Column(Integer, ForeignKey("users.id"))
    question = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())

    # Relationships
    team = relationship("Team", back_populates="polls")
    creator = relationship("User")
    choices = relationship(
        "PollChoice", back_populates="poll", cascade="all, delete-orphan"
    )
    responses = relationship(
        "PollResponse", back_populates="poll", cascade="all, delete-orphan"
    )


class PollChoice(Base):
    """Poll choice options"""

    __tablename__ = "poll_choices"

    id = Column(Integer, primary_key=True)
    poll_id = Column(Integer, ForeignKey("polls.id", ondelete="CASCADE"))
    choice_text = Column(Text, nullable=False)

    # Relationships
    poll = relationship("Poll", back_populates="choices")
    responses = relationship("PollResponse", back_populates="choice")


class PollResponse(Base):
    """Poll responses from players"""

    __tablename__ = "poll_responses"

    id = Column(Integer, primary_key=True)
    poll_id = Column(Integer, ForeignKey("polls.id", ondelete="CASCADE"))
    choice_id = Column(Integer, ForeignKey("poll_choices.id"))
    player_id = Column(Integer, ForeignKey("players.id"))
    responded_at = Column(DateTime(timezone=True), default=func.now())

    # Relationships
    poll = relationship("Poll", back_populates="responses")
    choice = relationship("PollChoice", back_populates="responses")
    player = relationship("Player")

    # Constraints
    __table_args__ = (
        UniqueConstraint("poll_id", "player_id", name="unique_poll_player_response"),
    )


class PlayerSeasonTracking(Base):
    """
    Season-specific tracking statistics for players
    Tracks forced byes, unavailability, and injury counts per season
    """

    __tablename__ = "player_season_tracking"

    id = Column(Integer, primary_key=True)
    player_id = Column(String(255), nullable=False)  # tenniscores_player_id
    league_id = Column(Integer, ForeignKey("leagues.id"))
    season_year = Column(Integer, nullable=False)  # e.g., 2024, 2025
    forced_byes = Column(Integer, default=0)
    not_available = Column(Integer, default=0)
    injury = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )

    # Relationships
    league = relationship("League")

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "league_id",
            "season_year",
            name="unique_player_season_tracking",
        ),
    )


class ActivityLog(Base):
    """
    Comprehensive activity tracking for all app actions
    Tracks every key action across the Rally application
    """

    __tablename__ = "activity_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_id = Column(
        Integer, ForeignKey("players.id"), nullable=True
    )  # Link to players table
    team_id = Column(
        Integer, ForeignKey("teams.id"), nullable=True
    )  # Link to teams table
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # Link to users table
    action_type = Column(
        String(255), nullable=False
    )  # 'login', 'match_created', 'poll_response', etc.
    action_description = Column(Text, nullable=False)  # Human-readable description
    related_id = Column(
        String(255), nullable=True
    )  # FK to related object (match_id, poll_id, etc.)
    related_type = Column(
        String(100), nullable=True
    )  # Type of related object ('match', 'poll', etc.)
    ip_address = Column(String(45), nullable=True)  # User's IP address
    user_agent = Column(Text, nullable=True)  # Browser/device info
    extra_data = Column(Text, nullable=True)  # JSON string for additional data
    timestamp = Column(DateTime(timezone=True), default=func.now(), nullable=False)

    # Relationships
    player = relationship("Player", backref="activity_logs")
    team = relationship("Team", backref="activity_logs")
    user = relationship("User", backref="activity_logs")

    def __repr__(self):
        return f"<ActivityLog(id={self.id}, action='{self.action_type}', player_id={self.player_id})>"
