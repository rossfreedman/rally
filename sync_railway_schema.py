import os
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Boolean, Date, DateTime, ForeignKey, Text
from sqlalchemy.sql import text
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
from urllib.parse import urlparse
import logging
from sqlalchemy.engine import URL
from sqlalchemy import event
from sqlalchemy.exc import OperationalError, SQLAlchemyError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def get_railway_url():
    """Get the appropriate Railway database URL"""
    # Use the working connection URL with the proxy domain
    return "postgresql://postgres:OoxuYNiTfyRqbqyoFTNTUHRGjtjHVscf@trolley.proxy.rlwy.net:34555/railway"

RAILWAY_DB_URL = get_railway_url()

# Create SQLAlchemy base
Base = declarative_base()

# Define models based on your schema
class Series(Base):
    __tablename__ = 'series'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)

class Club(Base):
    __tablename__ = 'clubs'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    club_id = Column(Integer, ForeignKey('clubs.id'))
    series_id = Column(Integer, ForeignKey('series.id'))
    club_automation_password = Column(String(255))
    created_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    last_login = Column(DateTime)
    is_admin = Column(Boolean, nullable=False, server_default=text('false'))

class PlayerAvailability(Base):
    __tablename__ = 'player_availability'
    id = Column(Integer, primary_key=True)
    player_name = Column(String(255), nullable=False)
    match_date = Column(Date, nullable=False)
    availability_status = Column(Integer, nullable=False, server_default=text('3'))
    updated_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    series_id = Column(Integer, ForeignKey('series.id'), nullable=False)

class UserActivityLog(Base):
    __tablename__ = 'user_activity_logs'
    id = Column(Integer, primary_key=True)
    user_email = Column(String(255), nullable=False)
    activity_type = Column(String(255), nullable=False)
    page = Column(String(255))
    action = Column(Text)
    details = Column(Text)
    ip_address = Column(String(45))
    timestamp = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))

class UserInstruction(Base):
    __tablename__ = 'user_instructions'
    id = Column(Integer, primary_key=True)
    user_email = Column(String(255), nullable=False)
    instruction = Column(Text, nullable=False)
    team_id = Column(Integer)
    created_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    is_active = Column(Boolean, nullable=False, server_default=text('true'))

def sync_schema():
    logger.info("Creating SQLAlchemy engine for Railway...")
    logger.info(f"Using database host: {urlparse(RAILWAY_DB_URL).hostname}")
    
    # Create engine with timeout and SSL requirements
    connect_args = {
        "connect_timeout": 10,
        "sslmode": "require",
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5
    }
    
    engine = create_engine(
        RAILWAY_DB_URL,
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_timeout=30
    )

    logger.info("Creating all tables that don't exist...")
    Base.metadata.create_all(engine)

    logger.info("Creating indexes...")
    with engine.connect() as conn:
        # Create indexes if they don't exist
        conn.execute(text('CREATE INDEX IF NOT EXISTS idx_user_email ON users(email)'))
        conn.execute(text('CREATE INDEX IF NOT EXISTS idx_player_availability ON player_availability(player_name, match_date, series_id)'))
        conn.execute(text('CREATE INDEX IF NOT EXISTS idx_user_activity_logs_user_email ON user_activity_logs(user_email, timestamp)'))
        conn.execute(text('CREATE INDEX IF NOT EXISTS idx_user_instructions_email ON user_instructions(user_email)'))
        conn.commit()

    logger.info("✅ Railway database schema synced with local models.")

if __name__ == "__main__":
    sync_schema() 