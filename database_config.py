import logging
import os
import time
from contextlib import contextmanager
from urllib.parse import urlparse

import psycopg2
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global flag to track if we've already logged a successful connection
_connection_logged = False


def get_db_url():
    """Get database URL from environment or use default"""
    global _connection_logged
    
    # Check if we're running on Railway
    is_railway = os.getenv("RAILWAY_ENVIRONMENT") is not None

    if is_railway:
        # CRITICAL FIX: When running via 'railway run', we're outside the internal network
        # so we need to use the public URL instead of internal hostname
        url = os.getenv("DATABASE_URL")
        public_url = os.getenv("DATABASE_PUBLIC_URL")
        
        # Check if we have a public URL and if the DATABASE_URL contains internal hostname
        if (public_url and url and 
            ("railway.internal" in url or "postgres.railway.internal" in url)):
            # Use public URL for external connections (like 'railway run')
            url = public_url
            if not _connection_logged:
                logger.info("Using Railway public database connection (external access)")
        elif url and ("railway.internal" in url or "postgres.railway.internal" in url):
            if not _connection_logged:
                logger.info(
                    "Using Railway internal database connection (preferred for Railway deployments)"
                )
        else:
            # Fallback to public URL if internal not available
            url = public_url or url
            if not _connection_logged:
                logger.info("Using Railway public database connection")
    else:
        # For local development, prefer public URL or local connection
        url = os.getenv("DATABASE_PUBLIC_URL") or os.getenv(
            "DATABASE_URL", "postgresql://localhost/rally"
        )

    if not url:
        url = "postgresql://localhost/rally"

    # Handle Railway's postgres:// URLs
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    # Only log database URL selection once to avoid spam
    if not _connection_logged:
        logger.info(
            f"Using database URL with host: {url.split('@')[1].split('/')[0] if '@' in url else 'unknown'}"
        )
    return url


def get_db_engine():
    """Get SQLAlchemy database engine"""
    url = get_db_url()

    # SQLAlchemy engine configuration
    engine = create_engine(
        url,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,  # 30 minutes
        pool_pre_ping=True,  # Verify connections before use
        echo=False,  # Set to True for SQL query logging
    )

    logger.info(f"Created SQLAlchemy engine for database")
    return engine


def parse_db_url(url):
    """Parse database URL into connection parameters"""
    parsed = urlparse(url)

    # Determine SSL mode - require for Railway connections
    hostname = parsed.hostname or ""
    sslmode = (
        "require"
        if (
            "railway.app" in hostname
            or "rlwy.net" in hostname
            or "railway.internal" in hostname
        )
        else "prefer"
    )

    # Use Railway's timeout setting if available, otherwise use a shorter default
    # For Railway deployments, use shorter timeout since internal network should be fast
    connect_timeout = int(os.getenv("PGCONNECT_TIMEOUT", "30"))

    return {
        "dbname": parsed.path[1:],
        "user": parsed.username,
        "password": parsed.password,
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "sslmode": sslmode,
        "connect_timeout": connect_timeout,
        "application_name": "rally_app",
        "keepalives_idle": 600,
        "keepalives_interval": 30,
        "keepalives_count": 3,
        "tcp_user_timeout": 30000,  # 30 seconds in milliseconds
        "target_session_attrs": "read-write",
    }


def test_db_connection():
    """Test database connection without context manager for health checks"""
    url = get_db_url()
    db_params = parse_db_url(url)

    # For health checks, use a very short timeout to fail fast
    test_params = db_params.copy()
    test_params["connect_timeout"] = 5

    try:
        logger.info(
            f"Testing database connection to {test_params['host']}:{test_params['port']}"
        )
        conn = psycopg2.connect(**test_params)

        # Test with a simple query
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            logger.info(f"Database connection test query successful")

        conn.close()
        logger.info("Database connection test successful!")
        return True, None

    except Exception as e:
        error_msg = str(e)
        logger.warning(
            f"Database connection test failed (this is normal during startup): {error_msg}"
        )
        return False, error_msg


@contextmanager
def get_db():
    """Get database connection with retry logic and timezone configuration"""
    global _connection_logged
    url = get_db_url()
    db_params = parse_db_url(url)

    max_retries = 5
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            # Only log connection details on first successful connection ever, or on retries
            if attempt == 0 and not _connection_logged:
                logger.info(f"🔌 Connecting to DB: {db_params['host']}:{db_params['port']}/{db_params['dbname']}")
            elif attempt > 0:
                logger.info(f"Connection attempt {attempt + 1}/{max_retries}")
                time.sleep(retry_delay)

            conn = psycopg2.connect(**db_params)

            # Verify connection is working
            with conn.cursor() as cursor:
                cursor.execute("SELECT current_setting('timezone')")
                tz = cursor.fetchone()[0]
                # Only log timezone on first successful connection ever
                if not _connection_logged:
                    logger.info(f"✅ DB Connected! Timezone: {tz}")
                    _connection_logged = True

            conn.commit()
            yield conn
            return

        except psycopg2.OperationalError as e:
            error_msg = str(e)
            logger.error(
                f"Database connection error (attempt {attempt + 1}): {error_msg}"
            )

            # CRITICAL FIX: Railway internal hostname fallback
            if ("postgres.railway.internal" in error_msg or "railway.internal" in error_msg):
                logger.warning("🚂 Railway internal hostname resolution failed")
                
                # Try to fallback to public URL if available
                public_url = os.getenv("DATABASE_PUBLIC_URL")
                if public_url and attempt == 0:  # Only try this on first attempt
                    logger.info("🔄 Retrying with Railway public database URL...")
                    try:
                        public_params = parse_db_url(public_url)
                        conn = psycopg2.connect(**public_params)
                        
                        # Test the connection
                        with conn.cursor() as cursor:
                            cursor.execute("SELECT current_setting('timezone')")
                            tz = cursor.fetchone()[0]
                            logger.info(f"✅ Railway public connection successful! Timezone: {tz}")
                            _connection_logged = True
                        
                        conn.commit()
                        yield conn
                        return
                        
                    except Exception as fallback_error:
                        logger.warning(f"⚠️  Public URL fallback also failed: {fallback_error}")
                        # Continue with normal retry logic
                
                logger.info("💡 Suggestion: Use DATABASE_PUBLIC_URL for external Railway connections")

            if "timeout expired" in error_msg:
                logger.warning("Connection timeout detected. This could be due to:")
                logger.warning("1. Network connectivity issues")
                logger.warning("2. Database server overload")
                logger.warning("3. Firewall/security group restrictions")
                logger.warning("4. Incorrect host/port configuration")

            if attempt == max_retries - 1:
                logger.error(f"All {max_retries} connection attempts failed.")
                logger.error(
                    f"Connection params (excluding password): {dict(dbname=db_params['dbname'], user=db_params['user'], host=db_params['host'], port=db_params['port'], sslmode=db_params['sslmode'], connect_timeout=db_params['connect_timeout'])}"
                )
                raise
            else:
                retry_delay *= 2  # Exponential backoff

        except Exception as e:
            logger.error(f"Unexpected database error: {str(e)}")
            logger.error(
                f"Connection params (excluding password): {dict(dbname=db_params['dbname'], user=db_params['user'], host=db_params['host'], port=db_params['port'], sslmode=db_params['sslmode'])}"
            )
            raise
        finally:
            if "conn" in locals():
                conn.close()
