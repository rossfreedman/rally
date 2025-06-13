"""
Rally Database Models - Refactored Schema
Updated to support clean separation between authentication and player data
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, Text, Date, Time, ForeignKey, UniqueConstraint, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func
from datetime import datetime
import os

Base = declarative_base()

# Database session configuration
DATABASE_URL = os.getenv('DATABASE_URL')
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
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(255))
    last_name = Column(String(255))
    club_automation_password = Column(String(255))  # For club automation features
    is_admin = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Relationships - properly use user_player_associations for many-to-many
    player_associations = relationship("UserPlayerAssociation", back_populates="user", cascade="all, delete-orphan")
    players = relationship("Player", secondary="user_player_associations", back_populates="associated_users", overlaps="player_associations")
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', admin={self.is_admin})>"

class League(Base):
    """
    League organizations (APTA_CHICAGO, NSTF, etc.)
    """
    __tablename__ = 'leagues'
    
    id = Column(Integer, primary_key=True)
    league_id = Column(String(255), nullable=False, unique=True)  # 'APTA_CHICAGO', 'NSTF'
    league_name = Column(String(255), nullable=False)
    league_url = Column(String(512))
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    players = relationship("Player", back_populates="league")
    clubs = relationship("Club", secondary="club_leagues", back_populates="leagues")
    series = relationship("Series", secondary="series_leagues", back_populates="leagues")
    
    def __repr__(self):
        return f"<League(id={self.id}, league_id='{self.league_id}', name='{self.league_name}')>"

class Club(Base):
    """
    Tennis clubs/facilities
    """
    __tablename__ = 'clubs'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    players = relationship("Player", back_populates="club")
    leagues = relationship("League", secondary="club_leagues", back_populates="clubs")
    
    def __repr__(self):
        return f"<Club(id={self.id}, name='{self.name}')>"

class Series(Base):
    """
    Series/divisions within leagues
    """
    __tablename__ = 'series'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    players = relationship("Player", back_populates="series")
    leagues = relationship("League", secondary="series_leagues", back_populates="series")
    
    def __repr__(self):
        return f"<Series(id={self.id}, name='{self.name}')>"

class Player(Base):
    """
    League-specific player records with integrated statistics
    Each player-league combination is a separate record
    """
    __tablename__ = 'players'
    
    id = Column(Integer, primary_key=True)
    tenniscores_player_id = Column(String(255), nullable=False)  # Not globally unique
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    email = Column(String(255))  # Optional, not for authentication
    
    # Foreign keys - required for each player record
    league_id = Column(Integer, ForeignKey('leagues.id'), nullable=False)
    club_id = Column(Integer, ForeignKey('clubs.id'), nullable=False) 
    series_id = Column(Integer, ForeignKey('series.id'), nullable=False)
    
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
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships - fixed overlapping warnings
    league = relationship("League", back_populates="players")
    club = relationship("Club", back_populates="players")
    series = relationship("Series", back_populates="players")
    user_associations = relationship("UserPlayerAssociation", back_populates="player", cascade="all, delete-orphan", overlaps="players")
    associated_users = relationship("User", secondary="user_player_associations", back_populates="players", overlaps="user_associations,player_associations")
    
    # Constraints  
    __table_args__ = (
        UniqueConstraint('tenniscores_player_id', 'league_id', name='unique_player_in_league'),
    )
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self):
        return f"<Player(id={self.id}, name='{self.full_name}', league='{self.league.league_id if self.league else None}')>"

class UserPlayerAssociation(Base):
    """
    Junction table linking users to their player records
    Supports one-to-many relationship (user can have multiple player records)
    """
    __tablename__ = 'user_player_associations'
    
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    player_id = Column(Integer, ForeignKey('players.id'), primary_key=True)
    is_primary = Column(Boolean, default=False)  # Mark primary player association
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships - fixed overlapping warnings
    user = relationship("User", back_populates="player_associations", overlaps="associated_users,players")
    player = relationship("Player", back_populates="user_associations", overlaps="associated_users,players")
    
    def __repr__(self):
        return f"<UserPlayerAssociation(user_id={self.user_id}, player_id={self.player_id}, primary={self.is_primary})>"

# Junction tables for many-to-many relationships
class ClubLeague(Base):
    """Club-League associations"""
    __tablename__ = 'club_leagues'
    
    id = Column(Integer, primary_key=True)
    club_id = Column(Integer, ForeignKey('clubs.id'), nullable=False)
    league_id = Column(Integer, ForeignKey('leagues.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    __table_args__ = (
        UniqueConstraint('club_id', 'league_id', name='unique_club_league'),
    )

class SeriesLeague(Base):
    """Series-League associations"""
    __tablename__ = 'series_leagues'
    
    id = Column(Integer, primary_key=True)
    series_id = Column(Integer, ForeignKey('series.id'), nullable=False)
    league_id = Column(Integer, ForeignKey('leagues.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    __table_args__ = (
        UniqueConstraint('series_id', 'league_id', name='unique_series_league'),
    )

# Activity and data tables
class PlayerAvailability(Base):
    """Player availability for matches"""
    __tablename__ = 'player_availability'
    
    id = Column(Integer, primary_key=True)
    player_name = Column(String(255), nullable=False)  # Kept for backward compatibility
    player_id = Column(Integer, ForeignKey('players.id'))  # New FK reference
    match_date = Column(DateTime(timezone=True), nullable=False)
    availability_status = Column(Integer, nullable=False, default=3)  # 1=available, 2=unavailable, 3=not sure
    series_id = Column(Integer, ForeignKey('series.id'), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    player = relationship("Player")
    series = relationship("Series")
    
    __table_args__ = (
        UniqueConstraint('player_name', 'match_date', 'series_id', name='unique_player_availability'),
    )

class UserActivityLog(Base):
    """User activity audit trail"""
    __tablename__ = 'user_activity_logs'
    
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
    __tablename__ = 'user_instructions'
    
    id = Column(Integer, primary_key=True)
    user_email = Column(String(255), nullable=False)
    instruction = Column(Text, nullable=False)
    series_id = Column(Integer, ForeignKey('series.id'))
    team_id = Column(Integer)
    created_at = Column(DateTime(timezone=True), default=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    series = relationship("Series")

class MatchScore(Base):
    """Match scores and results"""
    __tablename__ = 'match_scores'
    
    id = Column(Integer, primary_key=True)
    league_id = Column(Integer, ForeignKey('leagues.id'))
    match_date = Column(Date)
    home_team = Column(Text)
    away_team = Column(Text)
    home_player_1_id = Column(Text)
    home_player_2_id = Column(Text)
    away_player_1_id = Column(Text)
    away_player_2_id = Column(Text)
    scores = Column(Text)
    winner = Column(Text)  # 'home' or 'away'
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    league = relationship("League")

class PlayerHistory(Base):
    """Historical player performance data"""
    __tablename__ = 'player_history'
    
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('players.id'))
    league_id = Column(Integer, ForeignKey('leagues.id'))
    series = Column(String(255))
    date = Column(Date)
    end_pti = Column(Numeric(10, 2))  # Performance Tracking Index
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    player = relationship("Player")
    league = relationship("League")

class Schedule(Base):
    """Match scheduling"""
    __tablename__ = 'schedule'
    
    id = Column(Integer, primary_key=True)
    league_id = Column(Integer, ForeignKey('leagues.id'))
    match_date = Column(Date)
    match_time = Column(Time)
    home_team = Column(Text)
    away_team = Column(Text)
    location = Column(Text)
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    league = relationship("League")

class SeriesStats(Base):
    """Team statistics by series"""
    __tablename__ = 'series_stats'
    
    id = Column(Integer, primary_key=True)
    league_id = Column(Integer, ForeignKey('leagues.id'))
    series = Column(String(255))
    team = Column(String(255))
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