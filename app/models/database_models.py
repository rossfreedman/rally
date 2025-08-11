"""
Rally Database Models - Refactored Schema
Updated to support clean separation between authentication and player data
"""

import os
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    create_engine,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func

Base = declarative_base()

# Database session configuration
try:
    # Import database config to use the same URL resolution logic
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from database_config import get_db_url
    
    DATABASE_URL = get_db_url()
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    print("✅ Database session factory initialized successfully")
except Exception as e:
    print(f"⚠️  Failed to initialize database session factory: {e}")
    # Fallback for when database is not available (e.g., during migrations)
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
    phone_number = Column(String(20))  # For SMS notifications

    # Player preferences - personal attributes that don't change across leagues
    ad_deuce_preference = Column(String(50))  # 'Ad', 'Deuce', 'Either'
    dominant_hand = Column(String(20))  # 'Righty', 'Lefty'

    # Context persistence - remembers which league user was last active in
    league_context = Column(Integer, ForeignKey('leagues.id'))  # Last active league

    # Temporary password fields
    has_temporary_password = Column(Boolean, default=False)
    temporary_password_set_at = Column(DateTime(timezone=True))

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

    def get_active_player(self, session):
        """Get the currently active player based on user context"""
        # Check if user has an active context
        if hasattr(self, 'context') and self.context:
            if self.context.active_team_id:
                # Find player in the active team
                return (
                    session.query(Player)
                    .join(UserPlayerAssociation, Player.tenniscores_player_id == UserPlayerAssociation.tenniscores_player_id)
                    .filter(
                        UserPlayerAssociation.user_id == self.id,
                        Player.team_id == self.context.active_team_id,
                        Player.is_active == True
                    )
                    .first()
                )
            elif self.context.active_league_id:
                # Find any player in the active league
                return (
                    session.query(Player)
                    .join(UserPlayerAssociation, Player.tenniscores_player_id == UserPlayerAssociation.tenniscores_player_id)
                    .filter(
                        UserPlayerAssociation.user_id == self.id,
                        Player.league_id == self.context.active_league_id,
                        Player.is_active == True
                    )
                    .first()
                )
        
        # Fallback: return any player (for backwards compatibility)
        assoc = (
            session.query(UserPlayerAssociation)
            .filter(UserPlayerAssociation.user_id == self.id)
            .first()
        )
        return assoc.get_player(session) if assoc else None

    def get_user_leagues(self, session):
        """Get all leagues this user is associated with"""
        return (
            session.query(League)
            .join(Player, League.id == Player.league_id)
            .join(UserPlayerAssociation, Player.tenniscores_player_id == UserPlayerAssociation.tenniscores_player_id)
            .filter(UserPlayerAssociation.user_id == self.id, Player.is_active == True)
            .distinct()
            .all()
        )

    def get_user_teams(self, session, league_id=None):
        """Get all teams this user is associated with, optionally filtered by league"""
        query = (
            session.query(Team)
            .join(Player, Team.id == Player.team_id)
            .join(UserPlayerAssociation, Player.tenniscores_player_id == UserPlayerAssociation.tenniscores_player_id)
            .filter(
                UserPlayerAssociation.user_id == self.id,
                Player.is_active == True,
                Team.is_active == True
            )
        )
        
        if league_id:
            query = query.filter(Team.league_id == league_id)
            
        return query.distinct().all()

    def switch_context(self, session, league_id=None, team_id=None):
        """Switch user's active context"""
        # Get or create user context
        context = session.query(UserContext).filter(UserContext.user_id == self.id).first()
        if not context:
            context = UserContext(user_id=self.id)
            session.add(context)
        
        # Update context
        if league_id:
            context.active_league_id = league_id
        if team_id:
            context.active_team_id = team_id
            # If team is specified, also set the league
            team = session.query(Team).filter(Team.id == team_id).first()
            if team:
                context.active_league_id = team.league_id
        
        context.last_updated = func.now()
        session.commit()
        
        return context

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
    logo_filename = Column(String(500), nullable=True)
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
    series_stats = relationship("SeriesStats", back_populates="series_obj")

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


class UserContext(Base):
    """
    Dynamic user context for multi-league/multi-team users
    Tracks the current active league/team context for session
    Replaces the problematic 'is_primary' concept with dynamic context switching
    """
    
    __tablename__ = "user_contexts"
    
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    active_league_id = Column(Integer, ForeignKey("leagues.id"))
    active_team_id = Column(Integer, ForeignKey("teams.id"))
    last_updated = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="context")
    active_league = relationship("League")
    active_team = relationship("Team")
    
    def __repr__(self):
        return f"<UserContext(user_id={self.user_id}, league_id={self.active_league_id}, team_id={self.active_team_id})>"


class UserPlayerAssociation(Base):
    """
    Junction table linking users to their player records using stable identifiers
    Uses tenniscores_player_id only - league is derived from player data
    This makes associations ETL-resilient and fully normalized
    
    ENHANCED: Removed is_primary field - context is now handled by UserContext table
    """

    __tablename__ = "user_player_associations"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    tenniscores_player_id = Column(String(255), nullable=False, primary_key=True)
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
        return f"<UserPlayerAssociation(user_id={self.user_id}, tenniscores_player_id='{self.tenniscores_player_id}')>"


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
    user_id = Column(Integer, ForeignKey("users.id"))  # Stable user reference

    # Relationships
    player = relationship("Player")
    series = relationship("Series")
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint(
            "player_name", "match_date", "series_id", name="unique_player_availability"
        ),
        Index("idx_availability_user_date", "user_id", "match_date", postgresql_where=text("user_id IS NOT NULL")),
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
    series_id = Column(Integer, ForeignKey("series.id"))  # New series foreign key
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
    series_obj = relationship("Series", back_populates="series_stats")
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


class Group(Base):
    """
    User-created groups for organizing players
    Allows users to create custom groups of players for easy organization
    """

    __tablename__ = "groups"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    creator_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Relationships
    creator = relationship("User", backref="created_groups")
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")

    def get_member_count(self, session):
        """Get the number of members in this group"""
        return session.query(GroupMember).filter(GroupMember.group_id == self.id).count()

    def get_members_list(self, session):
        """Get list of User objects who are members of this group"""
        return (
            session.query(User)
            .join(GroupMember, User.id == GroupMember.user_id)
            .filter(GroupMember.group_id == self.id)
            .all()
        )

    def is_member(self, session, user_id):
        """Check if a user is a member of this group"""
        return (
            session.query(GroupMember)
            .filter(GroupMember.group_id == self.id, GroupMember.user_id == user_id)
            .first()
            is not None
        )

    def __repr__(self):
        return f"<Group(id={self.id}, name='{self.name}', creator_id={self.creator_user_id})>"


class GroupMember(Base):
    """
    Junction table for group membership
    Links users to groups with tracking of when and by whom they were added
    """

    __tablename__ = "group_members"

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    added_at = Column(DateTime(timezone=True), default=func.now())
    added_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    group = relationship("Group", back_populates="members")
    user = relationship("User", foreign_keys=[user_id], backref="group_memberships")
    added_by = relationship("User", foreign_keys=[added_by_user_id])

    # Constraints
    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uc_unique_group_member"),
    )

    def __repr__(self):
        return f"<GroupMember(group_id={self.group_id}, user_id={self.user_id})>"


class LineupEscrow(Base):
    """
    Lineup Escrow sessions for fair lineup disclosure
    Stores lineup data that is revealed simultaneously to both captains
    """

    __tablename__ = "lineup_escrow"

    id = Column(Integer, primary_key=True)
    escrow_token = Column(String(255), nullable=False, unique=True)  # Unique token for sharing
    initiator_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipient_name = Column(String(255), nullable=False)
    recipient_contact = Column(String(255), nullable=False)  # Email or phone
    contact_type = Column(String(20), nullable=False)  # 'email' or 'sms'
    
    # Team references
    initiator_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)  # Initiator's team
    recipient_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)  # Recipient's team
    
    # Lineup data
    initiator_lineup = Column(Text, nullable=False)
    recipient_lineup = Column(Text, nullable=True)  # Null until recipient submits
    
    # Status tracking
    status = Column(String(50), nullable=False, default='pending')  # 'pending', 'both_submitted', 'expired'
    initiator_submitted_at = Column(DateTime(timezone=True), default=func.now())
    recipient_submitted_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Optional expiration
    
    # Message details
    subject = Column(String(255), nullable=True)  # For email
    message_body = Column(Text, nullable=False)
    
    # Notification tracking
    initiator_notified = Column(Boolean, default=False)
    recipient_notified = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Relationships
    initiator = relationship("User", foreign_keys=[initiator_user_id])
    initiator_team = relationship("Team", foreign_keys=[initiator_team_id])
    recipient_team = relationship("Team", foreign_keys=[recipient_team_id])

    def __repr__(self):
        return f"<LineupEscrow(id={self.id}, token='{self.escrow_token}', status='{self.status}')>"


class LineupEscrowView(Base):
    """
    Tracks who has viewed the lineup escrow results
    """

    __tablename__ = "lineup_escrow_views"

    id = Column(Integer, primary_key=True)
    escrow_id = Column(Integer, ForeignKey("lineup_escrow.id"), nullable=False)
    viewer_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Null for anonymous views
    viewer_contact = Column(String(255), nullable=False)  # Email or phone of viewer
    viewed_at = Column(DateTime(timezone=True), default=func.now())
    ip_address = Column(String(45), nullable=True)

    # Relationships
    escrow = relationship("LineupEscrow")
    viewer = relationship("User", foreign_keys=[viewer_user_id])

    def __repr__(self):
        return f"<LineupEscrowView(escrow_id={self.escrow_id}, viewer='{self.viewer_contact}')>"


class SavedLineup(Base):
    """
    Saved lineups for users and teams
    Allows users to save and reuse lineup configurations
    """

    __tablename__ = "saved_lineups"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    lineup_name = Column(String(255), nullable=False)  # User-defined name for the lineup
    lineup_data = Column(Text, nullable=False)  # JSON string containing lineup configuration
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="saved_lineups")
    team = relationship("Team", backref="saved_lineups")

    # Constraints
    __table_args__ = (
        UniqueConstraint("user_id", "team_id", "lineup_name", name="unique_user_team_lineup_name"),
    )

    def __repr__(self):
        return f"<SavedLineup(id={self.id}, user_id={self.user_id}, team_id={self.team_id}, name='{self.lineup_name}')>"


class CaptainMessage(Base):
    """
    Stores captain messages for teams. These messages will appear in the notifications feed for all team members.
    """
    __tablename__ = "captain_messages"

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    captain_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())

    # Relationships
    team = relationship("Team", backref="captain_messages")
    captain = relationship("User")

    def __repr__(self):
        return f"<CaptainMessage(id={self.id}, team_id={self.team_id}, captain_user_id={self.captain_user_id})>"


class PickupGame(Base):
    """
    Pickup games for organizing casual tennis/paddle tennis matches
    """

    __tablename__ = "pickup_games"

    id = Column(Integer, primary_key=True)
    description = Column(Text, nullable=False)
    game_date = Column(Date, nullable=False)
    game_time = Column(Time, nullable=False)
    players_requested = Column(Integer, nullable=False)
    players_committed = Column(Integer, nullable=False, server_default='0')
    pti_low = Column(Integer, nullable=False, server_default='-30')
    pti_high = Column(Integer, nullable=False, server_default='100')
    series_low = Column(Integer, nullable=True)
    series_high = Column(Integer, nullable=True)
    club_only = Column(Boolean, nullable=False, server_default='false')
    is_private = Column(Boolean, nullable=False, server_default='false')
    club_id = Column(Integer, ForeignKey("clubs.id"), nullable=True)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=True)
    creator_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    club = relationship("Club", backref="pickup_games")
    league = relationship("League", backref="pickup_games")
    creator = relationship("User", backref="created_pickup_games")
    participants = relationship("PickupGameParticipant", back_populates="pickup_game")

    # Constraints
    __table_args__ = (
        CheckConstraint('players_requested > 0', name='ck_players_requested_positive'),
        CheckConstraint('players_committed >= 0', name='ck_players_committed_non_negative'),
        CheckConstraint('players_committed <= players_requested', name='ck_valid_player_counts'),
        CheckConstraint('pti_low <= pti_high', name='ck_valid_pti_range'),
        CheckConstraint('series_low IS NULL OR series_high IS NULL OR series_low <= series_high', name='ck_valid_series_range'),
    )

    def __repr__(self):
        return f"<PickupGame(id={self.id}, description='{self.description[:30]}...', club_id={self.club_id})>"


class PickupGameParticipant(Base):
    """
    Junction table for pickup game participants
    """

    __tablename__ = "pickup_game_participants"

    id = Column(Integer, primary_key=True)
    pickup_game_id = Column(Integer, ForeignKey("pickup_games.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, server_default=func.now())

    # Relationships
    pickup_game = relationship("PickupGame", back_populates="participants")
    user = relationship("User", backref="pickup_game_participations")

    # Constraints
    __table_args__ = (
        UniqueConstraint('pickup_game_id', 'user_id', name='uc_unique_game_participant'),
    )

    def __repr__(self):
        return f"<PickupGameParticipant(id={self.id}, game_id={self.pickup_game_id}, user_id={self.user_id})>"
