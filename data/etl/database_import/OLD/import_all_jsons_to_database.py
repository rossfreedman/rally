#!/usr/bin/env python3
"""
Comprehensive ETL Script for JSON Data Import
===========================================

This script imports data from JSON files in data/leagues/all/ into the PostgreSQL database
in the correct order based on foreign key constraints.

Order of operations:
1. Extract leagues from players.json -> import to leagues table
2. Extract clubs from players.json -> import to clubs table
3. Extract series from players.json -> import to series table
4. Analyze club-league relationships -> populate club_leagues table
5. Analyze series-league relationships -> populate series_leagues table
6. Import players.json -> players table
7. Import career stats from player_history.json -> update players table career columns
8. Import player_history.json -> player_history table
9. Import   match_history.json -> match_scores table
10. Import series_stats.json -> series_stats table
11. Import schedules.json -> schedule table
"""

import json
import os
import re
import sys
import time
import traceback
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
sys.path.insert(0, project_root)

import psycopg2
from psycopg2.extras import RealDictCursor

from database_config import get_db
from utils.league_utils import (
    get_league_display_name,
    get_league_url,
    normalize_league_id,
)
# CRITICAL FIX: Import player lookup utilities for fallback matching
from utils.database_player_lookup import find_player_by_database_lookup


class PlayerMatchingValidator:
    """Handles player ID validation and fallback matching during JSON imports"""
    
    def __init__(self):
        self.validation_stats = {
            'total_lookups': 0,
            'exact_matches': 0,
            'fallback_matches': 0,
            'failed_matches': 0,
            'missing_player_ids': []
        }
    
    def validate_and_resolve_player_id(self, conn, tenniscores_player_id: str, 
                                     first_name: str = None, last_name: str = None,
                                     club_name: str = None, series_name: str = None, 
                                     league_id: str = None) -> Optional[str]:
        """
        Validate player ID exists in database, with fallback matching if needed.
        
        Returns:
            str: Valid tenniscores_player_id if found/resolved
            None: If no match can be established
        """
        if not tenniscores_player_id:
            return None
            
        self.validation_stats['total_lookups'] += 1
        
        # First, check if the tenniscores_player_id exists directly
        cursor = conn.cursor()
        cursor.execute(
            "SELECT tenniscores_player_id FROM players WHERE tenniscores_player_id = %s AND is_active = true",
            (tenniscores_player_id,)
        )
        
        if cursor.fetchone():
            self.validation_stats['exact_matches'] += 1
            return tenniscores_player_id
        
        # Player ID not found - attempt fallback matching if we have enough info
        if not all([first_name, last_name, league_id]):
            self.validation_stats['failed_matches'] += 1
            self.validation_stats['missing_player_ids'].append({
                'tenniscores_id': tenniscores_player_id,
                'reason': 'Player ID not found in database, insufficient info for fallback',
                'available_info': f"{first_name or 'N/A'} {last_name or 'N/A'} ({club_name or 'N/A'}, {series_name or 'N/A'}, {league_id or 'N/A'})"
            })
            return None
        
        # Attempt fallback matching using database lookup
        try:
            result = find_player_by_database_lookup(
                first_name=first_name,
                last_name=last_name, 
                club_name=club_name or "",
                series_name=series_name or "",
                league_id=league_id
            )
            
            if result and isinstance(result, dict):
                if result.get('match_type') in ['exact', 'probable', 'high_confidence']:
                    resolved_id = result['player']['tenniscores_player_id']
                    self.validation_stats['fallback_matches'] += 1
                    print(f"   🔧 FALLBACK MATCH: {tenniscores_player_id} → {resolved_id} for {first_name} {last_name}")
                    return resolved_id
                elif result.get('match_type') == 'multiple_high_confidence':
                    # For imports, take the first high-confidence match 
                    resolved_id = result['matches'][0]['tenniscores_player_id']
                    self.validation_stats['fallback_matches'] += 1
                    print(f"   🔧 MULTIPLE FALLBACK: {tenniscores_player_id} → {resolved_id} for {first_name} {last_name} (first of {len(result['matches'])} matches)")
                    return resolved_id
        except Exception as e:
            print(f"   ❌ Fallback matching error for {tenniscores_player_id}: {e}")
        
        # No fallback match found
        self.validation_stats['failed_matches'] += 1
        self.validation_stats['missing_player_ids'].append({
            'tenniscores_id': tenniscores_player_id,
            'reason': 'Player ID not found, fallback matching failed',
            'available_info': f"{first_name} {last_name} ({club_name or 'N/A'}, {series_name or 'N/A'}, {league_id})"
        })
        return None
    
    def print_validation_summary(self):
        """Print summary of player ID validation results"""
        stats = self.validation_stats
        print(f"\n📊 PLAYER ID VALIDATION SUMMARY")
        print(f"=" * 50)
        print(f"Total lookups: {stats['total_lookups']:,}")
        print(f"Exact matches: {stats['exact_matches']:,}")
        print(f"Fallback matches: {stats['fallback_matches']:,}")
        print(f"Failed matches: {stats['failed_matches']:,}")
        
        if stats['missing_player_ids']:
            print(f"\n⚠️  MISSING PLAYER IDs ({len(stats['missing_player_ids'])} total):")
            for i, missing in enumerate(stats['missing_player_ids'][:10]):  # Show first 10
                print(f"   {i+1}. {missing['tenniscores_id']}: {missing['reason']}")
                print(f"      Info: {missing['available_info']}")
            
            if len(stats['missing_player_ids']) > 10:
                print(f"   ... and {len(stats['missing_player_ids']) - 10} more")
        
        success_rate = ((stats['exact_matches'] + stats['fallback_matches']) / stats['total_lookups'] * 100) if stats['total_lookups'] > 0 else 0
        print(f"\n✅ SUCCESS RATE: {success_rate:.1f}% ({stats['exact_matches'] + stats['fallback_matches']:,}/{stats['total_lookups']:,})")


class ComprehensiveETL:
    def __init__(self, force_environment=None):
        # Fix path calculation - script is in data/etl/database_import/, need to go up 3 levels to project root
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
        self.data_dir = os.path.join(project_root, "data", "leagues", "all")
        self.imported_counts = {}
        self.errors = []
        self.series_mappings = {}  # Cache for series mappings
        # CRITICAL FIX: Add player matching validator
        self.player_validator = PlayerMatchingValidator()
        
        # ENHANCED ENVIRONMENT DETECTION
        self.environment = self._detect_environment(force_environment)
        self.log(f"🌍 Environment detected: {self.environment}")
        
        # Apply environment-specific optimizations (validation always enabled)
        self._configure_for_environment()
        
        # CONNECTION MANAGEMENT: Add connection limiting and rotation
        self._init_connection_management()

    def _init_connection_management(self):
        """Initialize connection management settings"""
        if self.environment == 'local':
            # Local: Relaxed connection settings
            self.max_connection_age = 1800  # 30 minutes
            self.connection_rotation_frequency = 10000  # Every 10k operations
            self.max_operations_per_connection = 50000
        elif self.environment == 'railway_staging':
            # Staging: Aggressive connection rotation for speed
            self.max_connection_age = 300  # 5 minutes
            self.connection_rotation_frequency = 2000  # Every 2k operations
            self.max_operations_per_connection = 10000
        elif self.environment == 'railway_production':
            # Production: Balanced connection management
            self.max_connection_age = 600  # 10 minutes
            self.connection_rotation_frequency = 5000  # Every 5k operations
            self.max_operations_per_connection = 25000
        
        # Connection tracking
        self._connection_start_time = None
        self._operations_count = 0
        self._current_connection = None
        
        self.log(f"🔗 Connection management: rotation every {self.connection_rotation_frequency:,} ops, max age {self.max_connection_age}s")

    def _should_rotate_connection(self) -> bool:
        """Check if connection should be rotated"""
        if not self._connection_start_time:
            return False
            
        # Check age limit
        age = time.time() - self._connection_start_time
        if age > self.max_connection_age:
            return True
            
        # Check operation count limit
        if self._operations_count >= self.connection_rotation_frequency:
            return True
            
        return False

    def _reset_connection_tracking(self):
        """Reset connection tracking counters"""
        self._connection_start_time = time.time()
        self._operations_count = 0

    def _increment_operation_count(self, count: int = 1):
        """Increment operation counter for connection management"""
        self._operations_count += count

    @contextmanager
    def get_managed_db_connection(self):
        """Get a managed database connection with rotation support"""
        if self.is_railway:
            # Use Railway optimizations with connection management
            connection_manager = self._get_railway_managed_connection()
        else:
            # Use standard connection for local
            connection_manager = get_db()
            
        with connection_manager as conn:
            self._reset_connection_tracking()
            yield conn

    def _get_railway_managed_connection(self):
        """Get Railway connection with management and rotation support"""
        @contextmanager
        def managed_railway_connection():
            max_retries = self.connection_retry_attempts
            retry_delay = 2
            
            for attempt in range(max_retries):
                try:
                    self.log(f"🚂 Railway: Creating managed connection (attempt {attempt + 1}/{max_retries})")
                    
                    # Import database utilities
                    from database import parse_db_url, get_db_url
                    import psycopg2
                    import os
                    
                    # CRITICAL FIX: Prefer PUBLIC URLs when running locally with Railway env vars
                    # Check if we're actually running on Railway servers vs local with Railway env
                    is_local_with_railway_env = not os.path.exists('/app')  # Railway containers have /app
                    
                    if is_local_with_railway_env:
                        # Running locally with 'railway run' - use PUBLIC URL to avoid internal hostname issues
                        db_url = os.getenv('DATABASE_PUBLIC_URL', os.getenv('DATABASE_URL'))
                        self.log(f"🚂 Railway (Local): Using DATABASE_PUBLIC_URL for external access: {db_url[:50]}...")
                    else:
                        # Actually running on Railway servers - can use internal URL
                        db_url = os.getenv('DATABASE_URL', os.getenv('DATABASE_PUBLIC_URL'))
                        self.log(f"🚂 Railway (Server): Using DATABASE_URL for internal access: {db_url[:50]}...")
                    
                    if db_url.startswith("postgres://"):
                        db_url = db_url.replace("postgres://", "postgresql://", 1)
                    
                    # Create connection with Railway optimizations
                    db_params = parse_db_url(db_url)
                    
                    # Add connection-specific optimizations for Railway
                    db_params.update({
                        'connect_timeout': 30,
                        'keepalives_idle': 600,
                        'keepalives_interval': 30,
                        'keepalives_count': 3,
                        'application_name': f'rally_etl_{self.environment}'
                    })
                    
                    conn = psycopg2.connect(**db_params)
                    
                    # Set Railway-specific session parameters
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1")  # Test connection
                        cursor.execute("SET statement_timeout = '300000'")  # 5 minutes
                        cursor.execute("SET idle_in_transaction_session_timeout = '600000'")  # 10 minutes
                        cursor.execute("SET work_mem = '64MB'")  # Conservative memory
                        cursor.execute("SET maintenance_work_mem = '128MB'")
                        cursor.execute("SET effective_cache_size = '256MB'")
                    
                    conn.commit()
                    self.log("✅ Railway managed connection established")
                    
                    try:
                        yield conn
                    finally:
                        conn.close()
                        self.log("🔒 Railway connection closed")
                    
                    return  # Success
                    
                except Exception as e:
                    self.log(f"⚠️ Railway connection attempt {attempt + 1} failed: {str(e)}", "WARNING")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay *= 1.5
                    else:
                        self.log("❌ All Railway connection attempts failed", "ERROR")
                        raise
        
        return managed_railway_connection()

    def check_and_rotate_connection_if_needed(self, conn):
        """Check if connection needs rotation and handle it gracefully"""
        if not self._should_rotate_connection():
            return conn
            
        if self.is_railway:
            self.log(f"🔄 Connection rotation needed (age: {time.time() - self._connection_start_time:.1f}s, ops: {self._operations_count:,})")
            # For Railway, we'll commit current transaction and get a fresh connection
            # This is handled at the operation level in import methods
            conn.commit()
            self._reset_connection_tracking()
            self.log("✅ Connection refreshed")
        
        return conn

    def _detect_environment(self, force_environment=None):
        """Detect current environment: local, railway_staging, or railway_production"""
        if force_environment:
            return force_environment
            
        # Check if running on Railway
        if os.getenv('RAILWAY_ENVIRONMENT'):
            # Check Railway environment name
            railway_env = os.getenv('RAILWAY_ENVIRONMENT_NAME', '').lower()
            if 'staging' in railway_env or 'stage' in railway_env:
                return 'railway_staging'
            elif 'production' in railway_env or 'prod' in railway_env:
                return 'railway_production'
            else:
                # Fallback: check database URL for clues
                db_url = os.getenv('DATABASE_URL', '')
                if 'staging' in db_url.lower():
                    return 'railway_staging'
                elif 'prod' in db_url.lower():
                    return 'railway_production'
                else:
                    return 'railway_staging'  # Default to staging for safety
        else:
            return 'local'
    
    def _configure_for_environment(self):
        """Configure ETL settings based on environment"""
        if self.environment == 'local':
            self.log("🏠 Local environment - using development settings")
            self.batch_size = 1000
            self.commit_frequency = 100
            self.connection_retry_attempts = 5
            self.use_railway_optimizations = False
            
        elif self.environment == 'railway_staging':
            self.log("🟡 Railway Staging - using staging optimizations")
            self.batch_size = 200  # Smaller batches for staging
            self.commit_frequency = 50  # More frequent commits
            self.connection_retry_attempts = 8
            self.use_railway_optimizations = True
            
        elif self.environment == 'railway_production':
            self.log("🔴 Railway Production - using production optimizations")
            self.batch_size = 500  # Medium batches for production
            self.commit_frequency = 100  # Standard commits
            self.connection_retry_attempts = 10  # Max retries for production
            self.use_railway_optimizations = True
        
        # Player validation is ALWAYS enabled for data integrity
        self.log("🛡️ Player validation ALWAYS enabled for data integrity")
        self.log(f"📊 Settings: batch_size={self.batch_size}, validation=ALWAYS_ENABLED")

    @property 
    def is_railway(self):
        """Check if running on any Railway environment"""
        return self.environment.startswith('railway_')

    def ensure_schema_requirements(self, conn):
        """Ensure required schema elements exist before import"""
        cursor = conn.cursor()
        
        try:
            # Create system_settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    id SERIAL PRIMARY KEY,
                    key VARCHAR(255) UNIQUE NOT NULL,
                    value TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Initialize session_version
            cursor.execute("""
                INSERT INTO system_settings (key, value, description) 
                VALUES ('session_version', '5', 'Current session version for cache busting')
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """)
            
            # Add logo_filename column to clubs
            cursor.execute("""
                ALTER TABLE clubs 
                ADD COLUMN IF NOT EXISTS logo_filename VARCHAR(255)
            """)
            
            conn.commit()
            self.log("✅ Schema requirements ensured")
            
        except Exception as e:
            self.log(f"⚠️ Schema fix error (non-critical): {e}", "WARNING")


    def log(self, message: str, level: str = "INFO"):
        """Enhanced logging with timestamps"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def get_railway_optimized_db_connection(self):
        """Get database connection with Railway-specific optimizations"""
        if not self.is_railway:
            return get_db()
        
        # Railway-specific connection with better error handling
        max_retries = self.connection_retry_attempts
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                self.log(f"🚂 Railway: Database connection attempt {attempt + 1}/{max_retries}")
                
                # Import database utilities to create direct connection
                from database import parse_db_url, get_db_url
                import psycopg2
                import os
                
                # CRITICAL FIX: Use appropriate URL based on execution context
                is_local_with_railway_env = not os.path.exists('/app')  # Railway containers have /app
                
                if is_local_with_railway_env:
                    # Running locally with 'railway run' - use PUBLIC URL
                    db_url = os.getenv('DATABASE_PUBLIC_URL', os.getenv('DATABASE_URL'))
                    self.log(f"🚂 Railway (Local): Using DATABASE_PUBLIC_URL: {db_url[:50]}...")
                else:
                    # Actually running on Railway servers - use internal URL
                    db_url = os.getenv('DATABASE_URL', os.getenv('DATABASE_PUBLIC_URL'))
                    self.log(f"🚂 Railway (Server): Using DATABASE_URL: {db_url[:50]}...")
                
                # Handle Railway's postgres:// URLs
                if db_url.startswith("postgres://"):
                    db_url = db_url.replace("postgres://", "postgresql://", 1)
                
                # Create direct connection for Railway (not context manager)
                db_params = parse_db_url(db_url)
                conn = psycopg2.connect(**db_params)
                
                try:
                    # Test connection
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
                    
                    # Set Railway-specific connection parameters for stability and speed
                    cursor.execute("SET statement_timeout = '600000'")  # 10 minutes
                    cursor.execute("SET idle_in_transaction_session_timeout = '1200000'")  # 20 minutes
                    cursor.execute("SET work_mem = '128MB'")  # More memory for faster queries
                    cursor.execute("SET maintenance_work_mem = '256MB'")  # More memory for maintenance
                    cursor.execute("SET effective_cache_size = '512MB'")  # Better query planning
                    
                    conn.commit()
                    self.log("✅ Railway: Database connection established with performance optimizations")
                    
                    # Return a context manager wrapper for the connection
                    @contextmanager
                    def railway_connection():
                        try:
                            yield conn
                        finally:
                            conn.close()
                    
                    return railway_connection()
                    
                except Exception as setup_error:
                    # Close the connection if setup fails
                    conn.close()
                    raise setup_error
                    
            except Exception as e:
                self.log(f"⚠️ Railway: Connection attempt {attempt + 1} failed: {str(e)}", "WARNING")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 1.5  # Exponential backoff
                else:
                    self.log("❌ Railway: All connection attempts failed", "ERROR")
                    raise
    
    def load_series_mappings(self, conn):
        """Load series display names from database (using new series.display_name system)"""
        self.log("📋 Loading series display names from database...")
        
        cursor = conn.cursor()
        
        # Initialize mappings dictionary using the new display_name system
        self.series_mappings = {}
        mapping_count = 0
        
        try:
            # Load existing series with display names from series table
            cursor.execute("""
                SELECT s.name, s.display_name, sl.league_id
                FROM series s
                JOIN series_leagues sl ON s.id = sl.series_id
                JOIN leagues l ON sl.league_id = l.id
                WHERE s.display_name IS NOT NULL AND s.display_name != s.name
                ORDER BY l.league_id, s.name
            """)
            
            mappings = cursor.fetchall()
            
            for database_name, display_name, league_id in mappings:
                if league_id not in self.series_mappings:
                    self.series_mappings[league_id] = {}
                
                # Map both directions: display_name -> database_name and database_name -> display_name
                self.series_mappings[league_id][display_name] = database_name
                self.series_mappings[league_id][database_name] = database_name  # Identity mapping
                mapping_count += 1
                
        except Exception as e:
            # Table structure might be different - use safe fallback
            self.log(f"⚠️  Could not load series display names: {e}")
            self.log("🔧 Will use identity mapping (no transformations)")
            # CRITICAL: Rollback the failed transaction before proceeding
            conn.rollback()
        
        if mapping_count > 0:
            self.log(f"✅ Loaded {mapping_count} series display mappings from database")
        else:
            self.log("⚠️  No series display mappings found - using identity mapping")
            # No need to create default mappings - series.display_name handles this
            
    def _create_default_series_mappings(self, conn):
        """DEPRECATED: No longer needed - series.display_name handles mapping"""
        self.log("🔧 Series mapping creation is deprecated - using series.display_name column instead")
        # This method is kept for backward compatibility but does nothing
        pass

    def map_series_name(self, series_name: str, league_id: str) -> str:
        """Convert user-facing series name to database series name using series.display_name system"""
        if not series_name or not league_id:
            return series_name
            
        # Check if we have mappings for this league
        if league_id not in self.series_mappings:
            return series_name
            
        # Check for exact match first
        if series_name in self.series_mappings[league_id]:
            return self.series_mappings[league_id][series_name]
            
        # Check for case-insensitive match
        for user_format, db_format in self.series_mappings[league_id].items():
            if user_format.lower() == series_name.lower():
                return db_format
                
        # No mapping found, return original (series.display_name handles this at runtime)
        return series_name

    def load_json_file(self, filename: str) -> List[Dict]:
        """Load and parse JSON file with error handling"""
        filepath = os.path.join(self.data_dir, filename)
        self.log(f"Loading {filename}...")

        try:
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"File not found: {filepath}")

            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.log(f"✅ Loaded {len(data):,} records from {filename}")
            return data

        except Exception as e:
            self.log(f"❌ Error loading {filename}: {str(e)}", "ERROR")
            raise

    def backup_user_data_and_team_mappings(self, conn):
        """
        Comprehensive backup system for user data that depends on team_id references.
        
        This method:
        1. Backs up polls with team IDs (direct ID-based backup)
        2. Backs up captain messages with team IDs (direct ID-based backup)
        3. Backs up practice times with team IDs (direct ID-based backup)
        4. Backs up user associations and league contexts
        5. Backs up availability data
        """
        self.log("💾 Starting comprehensive user data backup with team ID preservation...")
        
        cursor = conn.cursor()
        
        # Step 1: Backup polls with team IDs (direct backup)
        self.log("📊 Backing up polls with team IDs...")
        cursor.execute("""
            DROP TABLE IF EXISTS polls_backup;
            CREATE TABLE polls_backup AS
            SELECT * FROM polls
        """)
        
        cursor.execute("SELECT COUNT(*) FROM polls_backup")
        polls_backup_count = cursor.fetchone()[0]
        self.log(f"✅ Backed up {polls_backup_count:,} polls with team IDs")
        
        # Step 2: Backup captain messages with team IDs (direct backup)
        self.log("💬 Backing up captain messages with team IDs...")
        cursor.execute("""
            DROP TABLE IF EXISTS captain_messages_backup;
            CREATE TABLE captain_messages_backup AS
            SELECT * FROM captain_messages
        """)
        
        cursor.execute("SELECT COUNT(*) FROM captain_messages_backup")
        captain_messages_backup_count = cursor.fetchone()[0]
        self.log(f"✅ Backed up {captain_messages_backup_count:,} captain messages with team IDs")
        
        # Step 3: Backup practice times with team IDs (direct backup)
        self.log("⏰ Backing up practice times with team IDs...")
        cursor.execute("""
            DROP TABLE IF EXISTS practice_times_backup;
            CREATE TABLE practice_times_backup AS
            SELECT * FROM schedule WHERE home_team ILIKE '%practice%'
        """)
        
        cursor.execute("SELECT COUNT(*) FROM practice_times_backup")
        practice_times_backup_count = cursor.fetchone()[0]
        self.log(f"✅ Backed up {practice_times_backup_count:,} practice times with team IDs")
        
        # Step 4: Backup user associations
        self.log("👥 Backing up user associations...")
        cursor.execute("""
            DROP TABLE IF EXISTS user_player_associations_backup;
            CREATE TABLE user_player_associations_backup AS
            SELECT * FROM user_player_associations
        """)
        
        cursor.execute("SELECT COUNT(*) FROM user_player_associations_backup")
        associations_backup_count = cursor.fetchone()[0]
        self.log(f"✅ Backed up {associations_backup_count:,} user associations")
        
        # Step 5: Backup league contexts
        self.log("🏆 Backing up league contexts...")
        cursor.execute("""
            DROP TABLE IF EXISTS user_league_contexts_backup;
            CREATE TABLE user_league_contexts_backup AS
            SELECT u.id as user_id, u.email, u.first_name, u.last_name, 
                   u.league_context, l.league_id as league_string_id, l.league_name
            FROM users u
            LEFT JOIN leagues l ON u.league_context = l.id
            WHERE u.league_context IS NOT NULL
        """)
        
        cursor.execute("SELECT COUNT(*) FROM user_league_contexts_backup")
        contexts_backup_count = cursor.fetchone()[0]
        self.log(f"✅ Backed up {contexts_backup_count:,} league contexts")
        
        # Step 6: Backup availability data
        self.log("📅 Backing up availability data...")
        cursor.execute("""
            DROP TABLE IF EXISTS player_availability_backup;
            CREATE TABLE player_availability_backup AS
            SELECT * FROM player_availability
        """)
        
        cursor.execute("SELECT COUNT(*) FROM player_availability_backup")
        availability_backup_count = cursor.fetchone()[0]
        self.log(f"✅ Backed up {availability_backup_count:,} availability records")
        
        # Step 7: Backup team mapping data for restoration
        self.log("🏆 Backing up team mapping data...")
        cursor.execute("""
            DROP TABLE IF EXISTS team_mapping_backup;
            CREATE TABLE team_mapping_backup AS
            SELECT 
                t.id as old_team_id,
                t.team_name as old_team_name,
                t.team_alias as old_team_alias,
                l.league_id as old_league_string_id,
                t.club_id as old_club_id,
                t.series_id as old_series_id
            FROM teams t
            JOIN leagues l ON t.league_id = l.id
            WHERE t.is_active = true
        """)
        
        cursor.execute("SELECT COUNT(*) FROM team_mapping_backup")
        team_mapping_backup_count = cursor.fetchone()[0]
        self.log(f"✅ Backed up {team_mapping_backup_count:,} team mappings")
        
        conn.commit()
        
        # Summary
        self.log("📊 Backup Summary:")
        self.log(f"   📊 Polls with team IDs: {polls_backup_count:,}")
        self.log(f"   💬 Captain messages with team IDs: {captain_messages_backup_count:,}")
        self.log(f"   ⏰ Practice times with team IDs: {practice_times_backup_count:,}")
        self.log(f"   👥 User associations: {associations_backup_count:,}")
        self.log(f"   🏆 League contexts: {contexts_backup_count:,}")
        self.log(f"   📅 Availability records: {availability_backup_count:,}")
        self.log(f"   🏆 Team mappings: {team_mapping_backup_count:,}")
        
        return {
            'polls_backup_count': polls_backup_count,
            'captain_messages_backup_count': captain_messages_backup_count,
            'practice_times_backup_count': practice_times_backup_count,
            'associations_backup_count': associations_backup_count,
            'contexts_backup_count': contexts_backup_count,
            'availability_backup_count': availability_backup_count,
            'team_mapping_backup_count': team_mapping_backup_count
        }

    def restore_user_data_with_team_mappings(self, conn):
        """
        Simple restore system for user data using team ID preservation.
        
        This method:
        1. Restores polls with preserved team IDs (direct restore)
        2. Restores captain messages with preserved team IDs (direct restore)
        3. Restores practice times with preserved team IDs (direct restore)
        4. Restores league contexts and fixes any issues
        5. Validates all restorations
        """
        self.log("🔄 Starting simple user data restoration with team ID preservation...")
        
        cursor = conn.cursor()
        
        # Step 1: Restore polls with preserved team IDs (direct restore)
        self.log("📊 Restoring polls with preserved team IDs...")
        cursor.execute("""
            INSERT INTO polls 
            SELECT * FROM polls_backup
            ON CONFLICT (id) DO UPDATE SET
                team_id = EXCLUDED.team_id
        """)
        
        polls_restored = cursor.rowcount
        self.log(f"✅ Restored {polls_restored} polls with preserved team IDs")
        
        # Step 2: Restore captain messages with preserved team IDs (direct restore)
        self.log("💬 Restoring captain messages with preserved team IDs...")
        cursor.execute("""
            INSERT INTO captain_messages 
            SELECT * FROM captain_messages_backup
            ON CONFLICT (id) DO UPDATE SET
                team_id = EXCLUDED.team_id
        """)
        
        captain_messages_restored = cursor.rowcount
        self.log(f"✅ Restored {captain_messages_restored} captain messages with preserved team IDs")
        
        # Step 2.5: Fix team ID mappings for restored data
        self.log("🔧 Fixing team ID mappings for restored data...")
        self._fix_restored_team_id_mappings(conn)
        
        # Step 3: Restore practice times with preserved team IDs (direct restore)
        self.log("⏰ Restoring practice times with preserved team IDs...")
        
        # First, map old league IDs to new ones using dynamic mapping
        self.log("   🔄 Mapping old league IDs to new ones...")
        
        # Create dynamic league ID mapping by matching to current leagues
        cursor.execute("""
            UPDATE practice_times_backup pt
            SET league_id = l_new.id
            FROM leagues l_old, leagues l_new
            WHERE pt.league_id = l_old.id 
            AND l_new.league_name = l_old.league_name
            AND pt.league_id != l_new.id
        """)
        
        mapped_count = cursor.rowcount
        if mapped_count > 0:
            self.log(f"   ✅ Mapped {mapped_count} practice times to new league IDs")
        else:
            # Fallback: If no mapping worked, try to map by league string ID  
            cursor.execute("""
                SELECT COUNT(*) FROM practice_times_backup pt
                LEFT JOIN leagues l ON pt.league_id = l.id
                WHERE l.id IS NULL
            """)
            
            orphaned_count = cursor.fetchone()[0]
            if orphaned_count > 0:
                self.log(f"   ⚠️ Found {orphaned_count} practice times with orphaned league IDs")
                
                # Try to fix orphaned league IDs by finding the best match
                cursor.execute("""
                    UPDATE practice_times_backup pt
                    SET league_id = (
                        SELECT l.id FROM leagues l 
                        ORDER BY l.id 
                        LIMIT 1
                    )
                    WHERE pt.league_id NOT IN (SELECT id FROM leagues)
                """)
                
                fixed_count = cursor.rowcount
                if fixed_count > 0:
                    self.log(f"   🔧 Fixed {fixed_count} orphaned league IDs with fallback mapping")
        
        # Now restore with enhanced team name matching for practice times
        cursor.execute("""
            INSERT INTO schedule (
                id, league_id, match_date, match_time, home_team, away_team, 
                location, created_at, home_team_id, away_team_id
            )
            SELECT 
                pt.id, pt.league_id, pt.match_date, pt.match_time, pt.home_team, pt.away_team,
                pt.location, pt.created_at,
                COALESCE(
                    -- Strategy 1: Exact team name match
                    (SELECT t.id FROM teams t WHERE t.team_name = pt.home_team LIMIT 1),
                    -- Strategy 2: Exact alias match
                    (SELECT t.id FROM teams t WHERE t.team_alias = pt.home_team LIMIT 1),
                    -- Strategy 3: Practice time pattern matching for "Tennaqua Practice - Series X"
                    (SELECT t.id FROM teams t 
                     WHERE pt.home_team LIKE 'Tennaqua Practice - %' 
                       AND (t.team_name LIKE 'Tennaqua - %' OR t.team_name LIKE 'Tennaqua S%')
                       AND (
                           (pt.home_team LIKE '%Chicago 22%' AND t.team_alias = 'Series 22')
                           OR (pt.home_team LIKE '%Series 2B%' AND t.team_alias = 'Series 2B')
                           OR (pt.home_team LIKE '%Series 2A%' AND t.team_alias = 'Series 2A')
                           OR (pt.home_team LIKE '%Series 1%' AND t.team_alias = 'Series 1')
                           OR (pt.home_team LIKE '%Series 3%' AND t.team_alias = 'Series 3')
                       )
                     LIMIT 1),
                    -- Strategy 4: Generic practice time matching for same team names
                    (SELECT t.id FROM teams t 
                     WHERE pt.home_team = pt.away_team 
                       AND t.team_name = pt.home_team 
                     LIMIT 1)
                ) as home_team_id,
                pt.away_team_id
            FROM practice_times_backup pt
            ON CONFLICT (id) DO UPDATE SET
                home_team_id = EXCLUDED.home_team_id,
                away_team_id = EXCLUDED.away_team_id
        """)
        
        practice_times_restored = cursor.rowcount
        self.log(f"✅ Restored {practice_times_restored} practice times with preserved team IDs")
        
        # Step 4: Restore league contexts
        self.log("🏆 Restoring league contexts...")
        cursor.execute("""
            UPDATE users 
            SET league_context = (
                SELECT l.id 
                FROM user_league_contexts_backup backup
                JOIN leagues l ON l.league_id = backup.league_string_id
                WHERE backup.user_id = users.id
                LIMIT 1
            )
            WHERE id IN (
                SELECT backup.user_id
                FROM user_league_contexts_backup backup
                JOIN leagues l ON l.league_id = backup.league_string_id
                WHERE backup.user_id = users.id
            )
        """)
        
        contexts_restored = cursor.rowcount
        self.log(f"✅ Restored {contexts_restored} league contexts")
        
        # Step 5: Auto-fix any remaining NULL league contexts
        self.log("🔧 Auto-fixing any remaining NULL league contexts...")
        null_contexts_fixed = self._auto_fix_null_league_contexts(conn)
        
        # Step 6: Validate all restorations
        self.log("🔍 Validating all restorations...")
        validation_results = self._validate_user_data_restoration(conn)
        
        # Step 7: Fix any orphaned references
        self.log("🔧 Fixing orphaned references...")
        orphaned_polls_fixed = self.fix_orphaned_poll_references(conn)
        orphaned_messages_fixed = self.fix_orphaned_captain_message_references(conn)
        
        # Step 7.5: Fix any remaining orphaned data with intelligent matching
        remaining_orphaned_fixed = self._fix_remaining_orphaned_data(conn)
        
        # Step 8: Clean up backup tables
        self.log("🧹 Cleaning up backup tables...")
        cursor.execute("DROP TABLE IF EXISTS polls_backup")
        cursor.execute("DROP TABLE IF EXISTS captain_messages_backup")
        cursor.execute("DROP TABLE IF EXISTS practice_times_backup")
        cursor.execute("DROP TABLE IF EXISTS user_league_contexts_backup")
        cursor.execute("DROP TABLE IF EXISTS user_player_associations_backup")
        cursor.execute("DROP TABLE IF EXISTS player_availability_backup")
        
        conn.commit()
        
        # Final summary
        self.log("📊 Restoration Summary:")
        self.log(f"   📊 Polls restored: {polls_restored}")
        self.log(f"   💬 Captain messages restored: {captain_messages_restored}")
        self.log(f"   ⏰ Practice times restored: {practice_times_restored}")
        self.log(f"   🏆 League contexts restored: {contexts_restored}")
        self.log(f"   🔧 NULL contexts auto-fixed: {null_contexts_fixed}")
        self.log(f"   🔧 Orphaned polls fixed: {orphaned_polls_fixed}")
        self.log(f"   🔧 Orphaned messages fixed: {orphaned_messages_fixed}")
        self.log(f"   🔧 Remaining orphaned fixed: {remaining_orphaned_fixed}")
        
        return {
            "polls_restored": polls_restored,
            "captain_messages_restored": captain_messages_restored,
            "practice_times_restored": practice_times_restored,
            "contexts_restored": contexts_restored,
            "null_contexts_fixed": null_contexts_fixed,
            "orphaned_polls_fixed": orphaned_polls_fixed,
            "orphaned_messages_fixed": orphaned_messages_fixed,
            "remaining_orphaned_fixed": remaining_orphaned_fixed,
            "validation_results": validation_results
        }

    def _auto_fix_null_league_contexts(self, conn):
        """Auto-fix users with NULL or broken league_context by setting to their most active league"""
        cursor = conn.cursor()
        
        # Find users with NULL league_context who have associations
        cursor.execute("""
            SELECT DISTINCT u.id, u.email, u.first_name, u.last_name, 'NULL' as issue_type
            FROM users u
            JOIN user_player_associations upa ON u.id = upa.user_id
            WHERE u.league_context IS NULL
        """)
        
        null_users = cursor.fetchall()
        
        # ENHANCEMENT: Also find users with broken league_context (pointing to non-existent leagues)
        cursor.execute("""
            SELECT DISTINCT u.id, u.email, u.first_name, u.last_name, 'BROKEN' as issue_type
            FROM users u
            JOIN user_player_associations upa ON u.id = upa.user_id
            LEFT JOIN leagues l ON u.league_context = l.id
            WHERE u.league_context IS NOT NULL AND l.id IS NULL
        """)
        
        broken_users = cursor.fetchall()
        
        # Combine both types of users that need fixing
        users_to_fix = list(null_users) + list(broken_users)
        fixed_count = 0
        
        if users_to_fix:
            self.log(f"🔧 Found {len(null_users)} users with NULL contexts and {len(broken_users)} users with broken contexts")
        
        for user in users_to_fix:
            # Get their most active league with team assignment preference
            cursor.execute("""
                SELECT 
                    p.league_id,
                    l.league_name,
                    COUNT(ms.id) as match_count,
                    MAX(ms.match_date) as last_match_date,
                    (CASE WHEN p.team_id IS NOT NULL THEN 1 ELSE 0 END) as has_team
                FROM user_player_associations upa
                JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                JOIN leagues l ON p.league_id = l.id
                LEFT JOIN match_scores ms ON (
                    (ms.home_player_1_id = p.tenniscores_player_id OR 
                     ms.home_player_2_id = p.tenniscores_player_id OR
                     ms.away_player_1_id = p.tenniscores_player_id OR 
                     ms.away_player_2_id = p.tenniscores_player_id)
                    AND ms.league_id = p.league_id
                )
                WHERE upa.user_id = %s
                AND p.is_active = true
                GROUP BY p.league_id, l.league_name, p.team_id
                ORDER BY 
                    (CASE WHEN p.team_id IS NOT NULL THEN 1 ELSE 2 END),
                    COUNT(ms.id) DESC,
                    MAX(ms.match_date) DESC NULLS LAST
                LIMIT 1
            """, [user[0]])
            
            best_league = cursor.fetchone()
            
            if best_league:
                cursor.execute("""
                    UPDATE users 
                    SET league_context = %s
                    WHERE id = %s
                """, [best_league[0], user[0]])
                
                fixed_count += 1
                issue_type = user[4]  # NULL or BROKEN
                self.log(f"   🔧 {user[2]} {user[3]} ({issue_type}): → {best_league[1]} ({best_league[2]} matches)")
        
        return fixed_count

    def _validate_multi_league_contexts(self, conn):
        """Validate that users with multiple league associations are properly configured for league selector visibility"""
        cursor = conn.cursor()
        
        self.log("🔍 Validating multi-league users for league selector visibility...")
        
        # Find users with associations in multiple leagues
        cursor.execute("""
            SELECT 
                u.id,
                u.email,
                u.first_name,
                u.last_name,
                u.league_context,
                COUNT(DISTINCT p.league_id) as league_count,
                STRING_AGG(DISTINCT l.league_name, ', ' ORDER BY l.league_name) as leagues
            FROM users u
            JOIN user_player_associations upa ON u.id = upa.user_id
            JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
            JOIN leagues l ON p.league_id = l.id
            WHERE p.is_active = TRUE
            GROUP BY u.id, u.email, u.first_name, u.last_name, u.league_context
            HAVING COUNT(DISTINCT p.league_id) > 1
            ORDER BY COUNT(DISTINCT p.league_id) DESC, u.email
        """)
        
        multi_league_users = cursor.fetchall()
        
        if not multi_league_users:
            self.log("   ℹ️  No users with multiple league associations found")
            return
        
        self.log(f"   📊 Found {len(multi_league_users)} users with multiple league associations:")
        
        properly_configured = 0
        needs_attention = 0
        
        for user in multi_league_users:
            user_id, email, first_name, last_name, league_context, league_count, leagues = user
            
            # Check if league_context is valid
            if league_context:
                cursor.execute("SELECT league_name FROM leagues WHERE id = %s", [league_context])
                context_league = cursor.fetchone()
                context_league_name = context_league[0] if context_league else "INVALID"
            else:
                context_league_name = "NULL"
            
            # Status check
            is_properly_configured = (
                league_context is not None and 
                context_league_name != "INVALID"
            )
            
            if is_properly_configured:
                properly_configured += 1
                status = "✅"
            else:
                needs_attention += 1
                status = "⚠️"
            
            self.log(f"     {status} {first_name} {last_name} ({email})")
            self.log(f"        Leagues: {leagues}")
            self.log(f"        Context: {context_league_name}")
            self.log(f"        League Selector: {'Will Show' if is_properly_configured else 'May Not Show'}")
        
        # Summary
        self.log(f"   📊 Multi-league user status:")
        self.log(f"      ✅ Properly configured: {properly_configured}")
        self.log(f"      ⚠️  Need attention: {needs_attention}")
        
        if needs_attention > 0:
            self.log(f"   ⚠️  {needs_attention} users may not see league selector properly", "WARNING")
        else:
            self.log("   ✅ All multi-league users properly configured for league selector")

    def _check_final_league_context_health(self, conn):
        """Check the final health of league contexts and availability data after ETL"""
        cursor = conn.cursor()
        
        # Total users with associations
        cursor.execute("""
            SELECT COUNT(DISTINCT u.id) as count
            FROM users u
            JOIN user_player_associations upa ON u.id = upa.user_id
        """)
        total_users_with_assoc = cursor.fetchone()[0]
        
        # Users with valid league_context (context points to a league they're actually in)
        cursor.execute("""
            SELECT COUNT(DISTINCT u.id) as count
            FROM users u
            JOIN user_player_associations upa ON u.id = upa.user_id
            JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
            WHERE u.league_context = p.league_id AND p.is_active = true
        """)
        valid_context_count = cursor.fetchone()[0]
        
        # CRITICAL: Verify availability data was preserved
        cursor.execute("SELECT COUNT(*) FROM player_availability")
        total_availability_records = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM player_availability WHERE user_id IS NOT NULL")
        stable_availability_records = cursor.fetchone()[0]
        
        if total_users_with_assoc > 0:
            health_score = (valid_context_count / total_users_with_assoc) * 100
            self.log(f"   📊 League context health: {valid_context_count}/{total_users_with_assoc} users have valid contexts")
        else:
            health_score = 100.0
            
        # Availability data verification
        self.log(f"   🛡️  Availability preservation check:")
        self.log(f"      Total availability records: {total_availability_records:,}")
        self.log(f"      Records with stable user_id: {stable_availability_records:,}")
        
        if total_availability_records > 0:
            stable_percentage = (stable_availability_records / total_availability_records) * 100
            if stable_percentage < 90:
                self.log(f"      ⚠️  WARNING: Only {stable_percentage:.1f}% of availability records have stable user_id references", "WARNING")
            else:
                self.log(f"      ✅ {stable_percentage:.1f}% of availability records have stable user_id references")
        
        return health_score

    def fix_orphaned_poll_references(self, conn):
        """Fix orphaned team_id references in polls table after ETL"""
        self.log("🔧 Fixing orphaned poll team_id references...")
        
        cursor = conn.cursor()
        
        # Find polls with orphaned team_id references
        cursor.execute("""
            SELECT p.id, p.team_id, p.question, p.created_at, p.created_by
            FROM polls p
            LEFT JOIN teams t ON p.team_id = t.id
            WHERE p.team_id IS NOT NULL AND t.id IS NULL
            ORDER BY p.created_at DESC
        """)
        
        orphaned_polls = cursor.fetchall()
        
        if not orphaned_polls:
            self.log("✅ No orphaned poll references found")
            return 0
        
        self.log(f"⚠️  Found {len(orphaned_polls)} polls with orphaned team_id references")
        
        fixed_count = 0
        
        for poll in orphaned_polls:
            poll_id, old_team_id, question, created_at, created_by = poll
            
            # Try to find the correct team based on poll creator and question content
            new_team_id = self._find_correct_team_for_poll(cursor, created_by, question, old_team_id)
            
            if new_team_id:
                # Update the poll to reference the correct team
                cursor.execute("""
                    UPDATE polls 
                    SET team_id = %s 
                    WHERE id = %s
                """, [new_team_id, poll_id])
                
                self.log(f"   ✅ Fixed poll {poll_id}: {old_team_id} → {new_team_id}")
                fixed_count += 1
            else:
                # If no correct team found, delete the orphaned record to maintain data integrity
                cursor.execute("""
                    DELETE FROM polls 
                    WHERE id = %s
                """, [poll_id])
                
                self.log(f"   🗑️  Deleted poll {poll_id} (no matching team found)")
                fixed_count += 1
        
        conn.commit()
        self.log(f"✅ Fixed {fixed_count} orphaned poll references")
        return fixed_count

    def _find_correct_team_for_poll(self, cursor, created_by, question, old_team_id):
        """Find the correct team_id for a poll based on creator and content"""
        
        # Get all teams the user has access to
        cursor.execute("""
            SELECT p.team_id, t.team_name, t.team_alias, t.series_id, l.league_id, s.name as series_name
            FROM players p
            JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            JOIN teams t ON p.team_id = t.id
            JOIN leagues l ON p.league_id = l.id
            LEFT JOIN series s ON t.series_id = s.id
            WHERE upa.user_id = %s AND p.is_active = TRUE
            ORDER BY l.league_id, t.team_name
        """, [created_by])
        
        user_teams = cursor.fetchall()
        
        if not user_teams:
            return None
        
        # Strategy 1: Look for specific series mentions in the question
        question_lower = question.lower()
        
        # Check for NSTF Series 2B references (must be exact to avoid confusion with Series 22)
        if "2b" in question_lower or "series 2b" in question_lower:
            for team in user_teams:
                team_id, team_name, team_alias, series_id, league_id, series_name = team
                if league_id == 'NSTF' and ('2b' in team_alias.lower() or '2b' in team_name.lower() or '2b' in series_name.lower()):
                    return team_id
        
        # Check for APTA Series 22 references (must be exact to avoid confusion with Series 2B)
        if ("22" in question_lower or "series 22" in question_lower) and "2b" not in question_lower:
            for team in user_teams:
                team_id, team_name, team_alias, series_id, league_id, series_name = team
                if league_id == 'APTA_CHICAGO' and ('22' in team_alias or '22' in team_name or '22' in series_name):
                    return team_id
        
        # Strategy 2: Look for league-specific keywords
        if "nstf" in question_lower or "north shore" in question_lower:
            for team in user_teams:
                team_id, team_name, team_alias, series_id, league_id, series_name = team
                if league_id == 'NSTF':
                    return team_id
        
        if "apta" in question_lower or "chicago" in question_lower:
            for team in user_teams:
                team_id, team_name, team_alias, series_id, league_id, series_name = team
                if league_id == 'APTA_CHICAGO':
                    return team_id
        
        # Strategy 3: Default to primary team (APTA_CHICAGO preferred)
        for team in user_teams:
            team_id, team_name, team_alias, series_id, league_id, series_name = team
            if league_id == 'APTA_CHICAGO':
                return team_id
        
        # If no APTA team, use first available
        if user_teams:
            return user_teams[0][0]  # Return first team_id
        
        return None

    def fix_orphaned_captain_message_references(self, conn):
        """Fix orphaned team_id references in captain_messages table after ETL"""
        self.log("🔧 Fixing orphaned captain message team_id references...")
        
        cursor = conn.cursor()
        
        # Find captain messages with orphaned team_id references
        cursor.execute("""
            SELECT cm.id, cm.team_id, cm.message, cm.captain_user_id, cm.created_at
            FROM captain_messages cm
            LEFT JOIN teams t ON cm.team_id = t.id
            WHERE cm.team_id IS NOT NULL AND t.id IS NULL
            ORDER BY cm.created_at DESC
        """)
        
        orphaned_messages = cursor.fetchall()
        
        if not orphaned_messages:
            self.log("✅ No orphaned captain message references found")
            return 0
        
        self.log(f"⚠️  Found {len(orphaned_messages)} captain messages with orphaned team_id references")
        
        fixed_count = 0
        
        for msg in orphaned_messages:
            msg_id, old_team_id, message, captain_user_id, created_at = msg
            
            # Try to find the correct team based on captain and message content
            new_team_id = self._find_correct_team_for_captain_message(cursor, captain_user_id, message, old_team_id)
            
            if new_team_id:
                # Update the captain message to reference the correct team
                cursor.execute("""
                    UPDATE captain_messages 
                    SET team_id = %s 
                    WHERE id = %s
                """, [new_team_id, msg_id])
                
                self.log(f"   ✅ Fixed captain message {msg_id}: {old_team_id} → {new_team_id}")
                fixed_count += 1
            else:
                # If no correct team found, delete the orphaned record since team_id is NOT NULL
                cursor.execute("""
                    DELETE FROM captain_messages 
                    WHERE id = %s
                """, [msg_id])
                
                self.log(f"   🗑️  Deleted captain message {msg_id} (no matching team found)")
                fixed_count += 1
        
        conn.commit()
        self.log(f"✅ Fixed {fixed_count} orphaned captain message references")
        return fixed_count

    def _find_correct_team_for_captain_message(self, cursor, captain_user_id, message, old_team_id):
        """Find the correct team_id for a captain message based on captain and content"""
        
        # Strategy 1: Find captain's team based on message content (e.g., "Series 22", "Series 2B")
        message_lower = message.lower()
        
        # Check for NSTF Series 2B references (must be exact to avoid confusion with Series 22)
        if "2b" in message_lower or "series 2b" in message_lower:
            cursor.execute("""
                SELECT p.team_id, t.team_name, t.team_alias, s.name as series_name
                FROM players p
                JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
                JOIN teams t ON p.team_id = t.id
                JOIN leagues l ON p.league_id = l.id
                LEFT JOIN series s ON t.series_id = s.id
                WHERE upa.user_id = %s AND l.league_id = 'NSTF' 
                AND (t.team_name LIKE '%%2B%%' OR t.team_alias LIKE '%%2B%%' OR s.name LIKE '%%2B%%')
                LIMIT 1
            """, [captain_user_id])
            
            result = cursor.fetchone()
            if result:
                team_id, team_name, team_alias, series_name = result
                return team_id
        
        # Check for APTA Series 22 references (must be exact to avoid confusion with Series 2B)
        if ("22" in message_lower or "series 22" in message_lower) and "2b" not in message_lower:
            cursor.execute("""
                SELECT p.team_id, t.team_name, t.team_alias, s.name as series_name
                FROM players p
                JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
                JOIN teams t ON p.team_id = t.id
                JOIN leagues l ON p.league_id = l.id
                LEFT JOIN series s ON t.series_id = s.id
                WHERE upa.user_id = %s AND l.league_id = 'APTA_CHICAGO' 
                AND (t.team_name LIKE '%%22%%' OR t.team_alias LIKE '%%22%%' OR s.name LIKE '%%22%%')
                LIMIT 1
            """, [captain_user_id])
            
            result = cursor.fetchone()
            if result:
                team_id, team_name, team_alias, series_name = result
                return team_id
        
        # Strategy 2: Find captain's primary team (APTA_CHICAGO preferred)
        cursor.execute("""
            SELECT p.team_id, t.team_name, t.team_alias, l.league_id
            FROM players p
            JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            JOIN teams t ON p.team_id = t.id
            JOIN leagues l ON p.league_id = l.id
            WHERE upa.user_id = %s AND p.is_active = TRUE AND p.team_id IS NOT NULL
            ORDER BY 
                CASE WHEN l.league_id = 'APTA_CHICAGO' THEN 1 ELSE 2 END,
                p.id
            LIMIT 1
        """, [captain_user_id])
        
        result = cursor.fetchone()
        if result:
            team_id, team_name, team_alias, league_id = result
            return team_id
        
        return None

    def _fix_remaining_orphaned_data(self, conn):
        """
        Fix any remaining orphaned polls and captain messages using intelligent matching.
        This method runs after the main restore to catch any data that couldn't be matched
        with the precise team matching approach.
        """
        self.log("🔧 Running intelligent orphan fixing for remaining data...")
        
        cursor = conn.cursor()
        total_fixed = 0
        
        # Fix orphaned polls
        cursor.execute("""
            SELECT COUNT(*) FROM polls WHERE team_id IS NULL
        """)
        orphaned_polls = cursor.fetchone()[0]
        
        if orphaned_polls > 0:
            self.log(f"🔧 Found {orphaned_polls} orphaned polls, fixing with intelligent matching...")
            
            # Get all orphaned polls with user context
            cursor.execute("""
                SELECT p.id, p.created_by, p.question, p.created_at, u.first_name, u.last_name
                FROM polls p
                JOIN users u ON p.created_by = u.id
                WHERE p.team_id IS NULL
            """)
            
            orphaned_poll_records = cursor.fetchall()
            
            for poll_record in orphaned_poll_records:
                poll_id, created_by, question, created_at, first_name, last_name = poll_record
                
                # Find the correct team for this poll
                correct_team_id = self._find_correct_team_for_poll(cursor, created_by, question, None)
                
                if correct_team_id:
                    cursor.execute("""
                        UPDATE polls SET team_id = %s WHERE id = %s
                    """, [correct_team_id, poll_id])
                    total_fixed += 1
                    self.log(f"   ✅ Fixed poll {poll_id} ({first_name} {last_name}) → team_id {correct_team_id}")
                else:
                    self.log(f"   ⚠️  Could not find team for poll {poll_id} ({first_name} {last_name})")
        
        # Fix orphaned captain messages
        cursor.execute("""
            SELECT COUNT(*) FROM captain_messages WHERE team_id IS NULL
        """)
        orphaned_messages = cursor.fetchone()[0]
        
        if orphaned_messages > 0:
            self.log(f"🔧 Found {orphaned_messages} orphaned captain messages, fixing with intelligent matching...")
            
            # Get all orphaned captain messages with user context
            cursor.execute("""
                SELECT cm.id, cm.captain_user_id, cm.message, cm.created_at, u.first_name, u.last_name
                FROM captain_messages cm
                JOIN users u ON cm.captain_user_id = u.id
                WHERE cm.team_id IS NULL
            """)
            
            orphaned_message_records = cursor.fetchall()
            
            for message_record in orphaned_message_records:
                message_id, captain_user_id, message, created_at, first_name, last_name = message_record
                
                # Find the correct team for this captain message
                correct_team_id = self._find_correct_team_for_captain_message(cursor, captain_user_id, message, None)
                
                if correct_team_id:
                    cursor.execute("""
                        UPDATE captain_messages SET team_id = %s WHERE id = %s
                    """, [correct_team_id, message_id])
                    total_fixed += 1
                    self.log(f"   ✅ Fixed captain message {message_id} ({first_name} {last_name}) → team_id {correct_team_id}")
                else:
                    self.log(f"   ⚠️  Could not find team for captain message {message_id} ({first_name} {last_name})")
        
        conn.commit()
        self.log(f"✅ Intelligent orphan fixing completed: {total_fixed} records fixed")
        return total_fixed

    def increment_session_version(self, conn):
        """Increment session version to trigger automatic user session refresh"""
        self.log("🔄 Incrementing session version to trigger user session refresh...")
        
        cursor = conn.cursor()
        
        try:
            # First ensure the system_settings table exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    id SERIAL PRIMARY KEY,
                    key VARCHAR(100) UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Get current session version
            cursor.execute("""
                SELECT value FROM system_settings WHERE key = 'session_version'
            """)
            result = cursor.fetchone()
            
            if result:
                current_version = int(result[0])
                new_version = current_version + 1
                
                # Update existing version
                cursor.execute("""
                    UPDATE system_settings 
                    SET value = %s, updated_at = CURRENT_TIMESTAMP 
                    WHERE key = 'session_version'
                """, [str(new_version)])
                
                self.log(f"   📈 Session version updated: {current_version} → {new_version}")
            else:
                # Insert initial version
                new_version = 1
                cursor.execute("""
                    INSERT INTO system_settings (key, value, description)
                    VALUES ('session_version', %s, 'Version number incremented after each ETL run to trigger session refresh')
                """, [str(new_version)])
                
                self.log(f"   📈 Session version initialized: {new_version}")
            
            # ENHANCEMENT: Add specific cache invalidation for series ID-based queries
            # This helps frontend detect when series IDs have changed due to ETL
            cursor.execute("""
                INSERT INTO system_settings (key, value, description)
                VALUES ('series_cache_version', %s, 'Version incremented when series IDs change due to ETL')
                ON CONFLICT (key) DO UPDATE SET 
                    value = EXCLUDED.value, 
                    updated_at = CURRENT_TIMESTAMP
            """, [str(new_version)])
            
            self.log(f"   📋 Series cache version updated: {new_version} (invalidates frontend series ID cache)")
            
            # Add ETL timestamp for debugging
            cursor.execute("""
                INSERT INTO system_settings (key, value, description)
                VALUES ('last_etl_run', %s, 'Timestamp of last successful ETL run')
                ON CONFLICT (key) DO UPDATE SET 
                    value = EXCLUDED.value, 
                    updated_at = CURRENT_TIMESTAMP
            """, [str(datetime.now().isoformat())])
            
            conn.commit()
            self.log("✅ All user sessions will be automatically refreshed on next page load")
            self.log("✅ Frontend series ID cache will be invalidated")
            
        except Exception as e:
            self.log(f"⚠️  Warning: Could not increment session version: {e}", "WARNING")
            # Don't fail ETL if session versioning fails
            conn.rollback()

    def clear_target_tables(self, conn):
        """Clear existing data from target tables in reverse dependency order"""
        self.log("🗑️  Clearing existing data from target tables...")

        # ENHANCEMENT: Backup user data before clearing
        backup_results = self.backup_user_data_and_team_mappings(conn)

        # CRITICAL: These tables are NEVER cleared - they use stable user_id references
        # that are never orphaned during ETL imports
        tables_to_clear = [
            "schedule",  # No dependencies
            "series_stats",  # References leagues, teams
            "match_scores",  # References players, leagues, teams
            "player_history",  # References players, leagues
            # "user_player_associations",  # PROTECTED: Uses stable tenniscores_player_id references that remain valid after ETL
            "players",  # References leagues, clubs, series, teams
            "teams",  # References leagues, clubs, series
            "series_leagues",  # References series, leagues
            "club_leagues",  # References clubs, leagues
            "series",  # Referenced by others
            "clubs",  # Referenced by others
            "leagues",  # Referenced by others
        ]
        
        # CRITICAL VERIFICATION: Ensure critical user data tables are NEVER in the clear list
        protected_tables = ["player_availability", "user_player_associations", "polls", "poll_choices", "poll_responses", "captain_messages"]
        for protected_table in protected_tables:
            if protected_table in tables_to_clear:
                raise Exception(f"CRITICAL ERROR: {protected_table} should NEVER be cleared - it uses stable user_id references!")
        
        self.log(f"🛡️  PROTECTED: player_availability, user_player_associations, polls, and captain_messages tables will be preserved (prevent session logout and data loss)")
        self.log(f"🗑️  Clearing {len(tables_to_clear)} tables: {', '.join(tables_to_clear)}")

        try:
            cursor = conn.cursor()

            # Disable foreign key checks temporarily
            cursor.execute("SET session_replication_role = replica;")

            for table in tables_to_clear:
                try:
                    cursor.execute(f"DELETE FROM {table}")
                    deleted_count = cursor.rowcount
                    self.log(f"   ✅ Cleared {deleted_count:,} records from {table}")
                except Exception as e:
                    self.log(f"   ⚠️  Could not clear {table}: {str(e)}", "WARNING")

            # Re-enable foreign key checks
            cursor.execute("SET session_replication_role = DEFAULT;")
            conn.commit()
            self.log("✅ All target tables cleared successfully")
            self.log(f"💾 Polls backed up: {backup_results['polls_backup_count']:,} records")
            self.log(f"💾 Captain messages backed up: {backup_results['captain_messages_backup_count']:,} records")
            self.log(f"💾 Practice times backed up: {backup_results['practice_times_backup_count']:,} records")
            self.log(f"💾 User associations backed up: {backup_results['associations_backup_count']:,} records")
            self.log(f"💾 League contexts backed up: {backup_results['contexts_backup_count']:,} records")
            self.log(f"💾 Availability records backed up: {backup_results['availability_backup_count']:,} records")

        except Exception as e:
            self.log(f"❌ Error clearing tables: {str(e)}", "ERROR")
            conn.rollback()
            raise

    def extract_leagues(
        self,
        players_data: List[Dict],
        series_stats_data: List[Dict] = None,
        schedules_data: List[Dict] = None,
    ) -> List[Dict]:
        """Extract unique leagues from players data and all other data sources"""
        self.log("🔍 Extracting leagues from all data sources...")

        leagues = set()

        # Extract from players data (original logic)
        for player in players_data:
            league = player.get("League", "").strip()
            if league:
                # Normalize the league ID
                normalized_league = normalize_league_id(league)
                if normalized_league:
                    leagues.add(normalized_league)

        # Extract from series_stats data (new logic to catch all leagues)
        if series_stats_data:
            for record in series_stats_data:
                league = record.get("league_id", "").strip()
                if league:
                    # Normalize the league ID
                    normalized_league = normalize_league_id(league)
                    if normalized_league:
                        leagues.add(normalized_league)

        # Extract from schedules data (new logic to catch all leagues)
        if schedules_data:
            for record in schedules_data:
                league = record.get("League", "").strip()
                if league:
                    # Normalize the league ID
                    normalized_league = normalize_league_id(league)
                    if normalized_league:
                        leagues.add(normalized_league)

        # Convert to standardized format
        league_records = []
        for league_id in sorted(leagues):
            # Create standardized league data using utility functions
            league_record = {
                "league_id": league_id,
                "league_name": get_league_display_name(league_id),
                "league_url": get_league_url(league_id),
            }
            league_records.append(league_record)

        self.log(
            f"✅ Found {len(league_records)} unique leagues: {', '.join([l['league_id'] for l in league_records])}"
        )
        return league_records

    def extract_clubs(self, players_data: List[Dict]) -> List[Dict]:
        """Extract unique clubs from players data with case-insensitive deduplication"""
        self.log("🔍 Extracting clubs from players data...")

        # Use a dict to track normalized names and their preferred capitalization
        clubs_normalized = {}
        case_variants = {}
        
        for player in players_data:
            team_name = player.get(
                "Club", ""
            ).strip()  # This is actually the full team name
            if team_name:
                # Parse the actual club name from the team name
                club_name = self.extract_club_name_from_team(team_name)
                if club_name:
                    # Normalize for case-insensitive comparison
                    normalized_name = club_name.lower().strip()
                    
                    if normalized_name not in clubs_normalized:
                        # First occurrence - use this capitalization
                        clubs_normalized[normalized_name] = club_name
                        case_variants[normalized_name] = [club_name]
                    else:
                        # Track case variants for logging
                        if club_name not in case_variants[normalized_name]:
                            case_variants[normalized_name].append(club_name)
                            
                        # Use the most common capitalization or prefer title case
                        current_name = clubs_normalized[normalized_name]
                        if self._is_better_capitalization(club_name, current_name):
                            clubs_normalized[normalized_name] = club_name

        # Log any case variants detected
        duplicates_detected = 0
        for normalized_name, variants in case_variants.items():
            if len(variants) > 1:
                duplicates_detected += 1
                self.log(f"🔍 Case variants detected for '{clubs_normalized[normalized_name]}': {variants}", "WARNING")

        if duplicates_detected > 0:
            self.log(f"⚠️  Detected {duplicates_detected} clubs with case variants - using normalized names", "WARNING")

        club_records = [{"name": club} for club in sorted(clubs_normalized.values())]

        self.log(f"✅ Found {len(club_records)} unique clubs (after case normalization)")
        return club_records

    def _is_better_capitalization(self, new_name: str, current_name: str) -> bool:
        """Determine if new_name has better capitalization than current_name"""
        # Prefer names with proper title case over all uppercase or all lowercase
        
        # If current is all caps and new is not, prefer new
        if current_name.isupper() and not new_name.isupper():
            return True
            
        # If current is all lowercase and new has proper case, prefer new  
        if current_name.islower() and not new_name.islower():
            return True
            
        # If new has more title case words, prefer it
        current_title_words = sum(1 for word in current_name.split() if word.istitle())
        new_title_words = sum(1 for word in new_name.split() if word.istitle())
        
        if new_title_words > current_title_words:
            return True
            
        return False

    def extract_club_name_from_team(self, team_name: str) -> str:
        """
        Extract club name from team name, matching the logic used in scrapers.

        Args:
            team_name (str): Team name in various formats

        Returns:
            str: Club name

        Examples:
            APTA: "Birchwood - 6" -> "Birchwood"
            CNSWPL: "Birchwood 1" -> "Birchwood"
            NSTF: "Birchwood S1" -> "Birchwood"
            NSTF: "Wilmette Sunday A" -> "Wilmette"
        """
        import re

        if not team_name:
            return "Unknown"

        team_name = team_name.strip()

        # APTA format: "Club - Number"
        if " - " in team_name:
            return team_name.split(" - ")[0].strip()

        # NSTF format: "Club SNumber" or "Club SNumberLetter" (e.g., S1, S2A, S2B)
        elif re.search(r"S\d+[A-Z]*", team_name):
            return re.sub(r"\s+S\d+[A-Z]*.*$", "", team_name).strip()

        # NSTF Sunday format: "Club Sunday A/B"
        elif "Sunday" in team_name:
            club_name = (
                team_name.replace("Sunday A", "").replace("Sunday B", "").strip()
            )
            return club_name if club_name else team_name

        # CNSWPL format: "Club Number" or "Club NumberLetter" (e.g., "Birchwood 1", "Hinsdale PC 1a")
        elif re.search(r"\s+\d+[a-zA-Z]*$", team_name):
            club_part = re.sub(r"\s+\d+[a-zA-Z]*$", "", team_name).strip()
            return club_part if club_part else team_name

        # Fallback: use the team name as-is
        return team_name

    def extract_series(
        self,
        players_data: List[Dict],
        series_stats_data: List[Dict] = None,
        schedules_data: List[Dict] = None,
        conn=None,
    ) -> List[Dict]:
        """Extract unique series from players data and team data, applying mappings"""
        self.log("🔍 Extracting series from players data and team data...")

        # Load series mappings if we have a connection
        if conn:
            self.load_series_mappings(conn)

        series = set()

        # Extract from players data with mapping conversion
        for player in players_data:
            series_name = player.get("Series", "").strip()
            league_id = normalize_league_id(player.get("League", "").strip())
            if series_name and league_id:
                # Convert using mapping
                db_series_name = self.map_series_name(series_name, league_id)
                series.add(db_series_name)

        # Extract from series_stats data with mapping conversion
        if series_stats_data:
            for record in series_stats_data:
                series_name = record.get("series", "").strip()
                league_id = normalize_league_id(record.get("league_id", "").strip())
                if series_name and league_id:
                    # Clean any malformed series names like "Series eries 16"
                    if "eries " in series_name:
                        series_name = series_name.replace("eries ", "")
                    # Convert using mapping
                    db_series_name = self.map_series_name(series_name, league_id)
                    series.add(db_series_name)

        # Extract from schedules data by parsing team names with mapping conversion
        if schedules_data:
            for record in schedules_data:
                league_id = normalize_league_id(record.get("League", "").strip())
                home_team = record.get("home_team", "").strip()
                away_team = record.get("away_team", "").strip()

                for team_name in [home_team, away_team]:
                    if team_name and team_name != "BYE" and league_id:
                        # Parse team name to extract series
                        club_name, series_name = self.parse_schedule_team_name(
                            team_name
                        )
                        if series_name:
                            # Convert using mapping
                            db_series_name = self.map_series_name(series_name, league_id)
                            series.add(db_series_name)

        series_records = [{"name": series_name} for series_name in sorted(series)]

        self.log(f"✅ Found {len(series_records)} unique series (after mapping conversion)")
        return series_records

    def analyze_club_league_relationships(self, players_data: List[Dict], teams_data: List[Dict] = None) -> List[Dict]:
        """Analyze which clubs belong to which leagues from ALL data sources"""
        self.log("🔍 Analyzing club-league relationships from all data sources...")

        club_league_map = {}
        
        # Extract from players data (original logic)
        for player in players_data:
            team_name = player.get(
                "Club", ""
            ).strip()  # This is actually the full team name
            club = self.extract_club_name_from_team(
                team_name
            )  # Parse the actual club name
            league = player.get("League", "").strip()

            if club and league:
                # Normalize the league ID
                normalized_league = normalize_league_id(league)
                if normalized_league:
                    if club not in club_league_map:
                        club_league_map[club] = set()
                    club_league_map[club].add(normalized_league)

        # ENHANCEMENT: Extract from teams data to catch any missing relationships
        if teams_data:
            for team in teams_data:
                club_name = team.get("club_name", "").strip()
                league_id = team.get("league_id", "").strip()
                
                if club_name and league_id:
                    if club_name not in club_league_map:
                        club_league_map[club_name] = set()
                    club_league_map[club_name].add(league_id)

        relationships = []
        for club, leagues in club_league_map.items():
            for league_id in leagues:
                relationships.append({"club_name": club, "league_id": league_id})

        self.log(f"✅ Found {len(relationships)} club-league relationships (from players + teams data)")
        return relationships

    def analyze_series_league_relationships(
        self, players_data: List[Dict], teams_data: List[Dict] = None
    ) -> List[Dict]:
        """Analyze which series belong to which leagues from ALL data sources, using mapped series names"""
        self.log("🔍 Analyzing series-league relationships from all data sources...")

        series_league_map = {}
        
        # Extract from players data (original logic)
        for player in players_data:
            raw_series_name = player.get("Series", "").strip()
            league = player.get("League", "").strip()

            if raw_series_name and league:
                # Normalize the league ID
                normalized_league = normalize_league_id(league)
                if normalized_league:
                    # Convert series name using mapping
                    mapped_series_name = self.map_series_name(raw_series_name, normalized_league)
                    
                    if mapped_series_name not in series_league_map:
                        series_league_map[mapped_series_name] = set()
                    series_league_map[mapped_series_name].add(normalized_league)

        # ENHANCEMENT: Extract from teams data to catch any missing relationships
        if teams_data:
            for team in teams_data:
                series_name = team.get("series_name", "").strip()
                league_id = team.get("league_id", "").strip()
                
                if series_name and league_id:
                    if series_name not in series_league_map:
                        series_league_map[series_name] = set()
                    series_league_map[series_name].add(league_id)

        relationships = []
        for series_name, leagues in series_league_map.items():
            for league_id in leagues:
                relationships.append(
                    {"series_name": series_name, "league_id": league_id}
                )

        self.log(f"✅ Found {len(relationships)} series-league relationships (from players + teams data, after mapping)")
        return relationships

    def extract_teams(
        self, series_stats_data: List[Dict], schedules_data: List[Dict], conn=None
    ) -> List[Dict]:
        """Extract unique teams from series stats and schedules data, applying mappings"""
        self.log("🔍 Extracting teams from JSON data...")

        # Load series mappings if we have a connection
        if conn:
            self.load_series_mappings(conn)

        teams = set()

        # Extract from series_stats.json
        for record in series_stats_data:
            series_name = record.get("series", "").strip()
            team_name = record.get("team", "").strip()
            league_id = normalize_league_id(record.get("league_id", "").strip())

            if team_name and series_name and league_id:
                # Clean any malformed series names like "Series eries 16"
                if "eries " in series_name:
                    series_name = series_name.replace("eries ", "")

                # Apply mapping to convert to database format
                db_series_name = self.map_series_name(series_name, league_id)

                # Parse team name to extract club
                club_name = self.parse_team_name_to_club(team_name, db_series_name)
                if club_name:
                    teams.add((club_name, db_series_name, league_id, team_name))

        # Extract from schedules.json (both home and away teams)
        for record in schedules_data:
            league_id = normalize_league_id(record.get("League", "").strip())
            home_team = record.get("home_team", "").strip()
            away_team = record.get("away_team", "").strip()

            for team_name in [home_team, away_team]:
                if team_name and league_id and team_name != "BYE":
                    # Parse team name to extract club and series
                    club_name, series_name = self.parse_schedule_team_name(team_name)
                    if club_name and series_name:
                        # Clean any malformed series names like "Series eries 16"
                        if "eries " in series_name:
                            series_name = series_name.replace("eries ", "")
                        
                        # Apply mapping to convert to database format
                        db_series_name = self.map_series_name(series_name, league_id)
                        teams.add((club_name, db_series_name, league_id, team_name))

        # Convert to list of dictionaries
        team_records = []
        for club_name, series_name, league_id, team_name in sorted(teams):
            team_records.append(
                {
                    "club_name": club_name,
                    "series_name": series_name,
                    "league_id": league_id,
                    "team_name": team_name,
                }
            )

        self.log(f"✅ Found {len(team_records)} unique teams (after mapping conversion)")
        return team_records

    def parse_team_name_to_club(self, team_name: str, series_name: str) -> str:
        """Parse team name from series_stats to extract club name"""
        # Use the same logic as extract_club_name_from_team for consistency
        return self.extract_club_name_from_team(team_name)

    def parse_schedule_team_name(self, team_name: str) -> tuple:
        """Parse team name from schedules to extract club and series"""
        # Examples:
        # APTA_CHICAGO: "Tennaqua - 22" -> ("Tennaqua", "Chicago 22")
        # NSTF: "Tennaqua S2B" -> ("Tennaqua", "Series 2B")
        # CNSWPL: "Tennaqua 1" -> ("Tennaqua", "Division 1")

        # Handle APTA_CHICAGO format: "Club - Suffix"
        if " - " in team_name:
            parts = team_name.split(" - ")
            if len(parts) >= 2:
                club_name = parts[0].strip()
                series_suffix = parts[1].strip()

                # Map series suffix to full series name
                series_name = self.map_series_suffix_to_full_name(series_suffix)
                return club_name, series_name

        # Handle NSTF format: "Club SSuffix" (like "Tennaqua S2B")
        # Must be " S" followed by number or number+letter (not words like "Shore")
        import re

        if re.search(r" S\d", team_name):  # " S" followed by a digit
            parts = team_name.split(" S")
            if len(parts) >= 2:
                club_name = parts[0].strip()
                series_suffix = parts[1].strip()

                # Map series suffix to full series name (for NSTF, this becomes "Series 2B")
                series_name = self.map_series_suffix_to_full_name(f"S{series_suffix}")
                return club_name, series_name

        # Handle CNSWPL format: "Club Number" or "Club NumberLetter" (like "Tennaqua 1", "Hinsdale PC 1a")
        # Must end with space + digit + optional letter(s)
        if re.search(r"\s+\d+[a-zA-Z]*$", team_name):
            club_name = re.sub(r"\s+\d+[a-zA-Z]*$", "", team_name).strip()
            if club_name:
                # Extract the series suffix (number + optional letters)
                series_match = re.search(r"\s+(\d+[a-zA-Z]*)$", team_name)
                if series_match:
                    series_suffix = series_match.group(1)
                    # For CNSWPL, map to "Division N" format to match player data
                    series_name = f"Division {series_suffix}"
                    return club_name, series_name

        # Fallback for edge cases: treat entire name as club with default series
        return team_name, "Series A"

    def map_series_suffix_to_full_name(self, suffix: str) -> str:
        """Map series suffix to full series name"""
        # Examples: "22" -> "Chicago 22", "21 SW" -> "Chicago 21 SW", "S2B" -> "Series 2B"
        try:
            # If it's a pure number, check if it's a small number (likely CNSWPL Division N)
            series_num = int(suffix)
            if (
                series_num <= 20
            ):  # CNSWPL divisions are typically 1-17, with some letters
                return f"Division {series_num}"
            else:
                # Larger numbers are likely APTA Chicago series
                return f"Chicago {series_num}"
        except ValueError:
            # If it's not a pure number, handle special cases
            if suffix.upper().startswith("S"):
                # NSTF format like "S2B" -> "Series 2B"
                return f"Series {suffix[1:]}"
            elif any(char.isdigit() for char in suffix):
                # If it contains numbers but isn't pure number
                # Check if it's CNSWPL format (like "1a", "16b")
                if len(suffix) <= 3 and suffix[0].isdigit():
                    return f"Division {suffix}"
                else:
                    # Otherwise assume Chicago (like "21 SW")
                    return f"Chicago {suffix}"

            # Default: assume it's already a series name
            return suffix

    def import_leagues(self, conn, leagues_data: List[Dict]):
        """Import leagues into database"""
        self.log("📥 Importing leagues...")

        cursor = conn.cursor()
        imported = 0

        for league in leagues_data:
            try:
                cursor.execute(
                    """
                    INSERT INTO leagues (league_id, league_name, league_url, created_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (league_id) DO NOTHING
                """,
                    (league["league_id"], league["league_name"], league["league_url"]),
                )

                if cursor.rowcount > 0:
                    imported += 1

            except Exception as e:
                self.log(
                    f"❌ Error importing league {league['league_id']}: {str(e)}",
                    "ERROR",
                )
                raise

        conn.commit()
        self.imported_counts["leagues"] = imported
        self.log(f"✅ Imported {imported} leagues")

    def import_clubs(self, conn, clubs_data: List[Dict]):
        """Import clubs into database with case-insensitive duplicate prevention"""
        self.log("📥 Importing clubs...")

        cursor = conn.cursor()
        imported = 0
        skipped_duplicates = 0

        for club in clubs_data:
            try:
                club_name = club["name"]
                
                # Check for case-insensitive duplicates in existing database
                cursor.execute(
                    """
                    SELECT id, name FROM clubs 
                    WHERE LOWER(name) = LOWER(%s)
                """,
                    (club_name,),
                )
                
                existing_club = cursor.fetchone()
                
                if existing_club:
                    existing_id, existing_name = existing_club
                    
                    if existing_name != club_name:
                        # Case-insensitive duplicate detected
                        self.log(
                            f"🔍 Case-insensitive duplicate detected: '{club_name}' (existing: '{existing_name}')",
                            "WARNING"
                        )
                        
                        # Update to better capitalization if needed
                        if self._is_better_capitalization(club_name, existing_name):
                            cursor.execute(
                                """
                                UPDATE clubs SET name = %s WHERE id = %s
                                """,
                                (club_name, existing_id),
                            )
                            self.log(f"📝 Updated club capitalization: '{existing_name}' → '{club_name}'")
                    
                    skipped_duplicates += 1
                else:
                    # Insert new club - preserve existing logo if club existed before
                    cursor.execute(
                        """
                        INSERT INTO clubs (name, logo_filename)
                        SELECT %s, COALESCE(
                            (SELECT logo_filename FROM clubs WHERE LOWER(name) = LOWER(%s) LIMIT 1),
                            CASE 
                                WHEN LOWER(%s) = 'glenbrook rc' THEN 'static/images/clubs/glenbrook_rc_logo.png'
                                WHEN LOWER(%s) = 'tennaqua' THEN 'static/images/clubs/tennaqua_logo.png'
                                ELSE NULL
                            END
                        )
                    """,
                        (club_name, club_name, club_name, club_name),
                    )
                    imported += 1

            except Exception as e:
                self.log(f"❌ Error importing club {club['name']}: {str(e)}", "ERROR")
                raise

        conn.commit()
        self.imported_counts["clubs"] = imported
        
        if skipped_duplicates > 0:
            self.log(f"✅ Imported {imported} clubs, skipped {skipped_duplicates} case-insensitive duplicates")
        else:
            self.log(f"✅ Imported {imported} clubs")

    def import_series(self, conn, series_data: List[Dict]):
        """Import series into database"""
        self.log("📥 Importing series...")

        cursor = conn.cursor()
        imported = 0

        for series in series_data:
            try:
                # Use series name as display_name for now (can be customized later)
                display_name = series["name"]
                
                cursor.execute(
                    """
                    INSERT INTO series (name, display_name)
                    VALUES (%s, %s)
                    ON CONFLICT (name) DO NOTHING
                """,
                    (series["name"], display_name),
                )

                if cursor.rowcount > 0:
                    imported += 1

            except Exception as e:
                self.log(
                    f"❌ Error importing series {series['name']}: {str(e)}", "ERROR"
                )
                raise

        conn.commit()
        self.imported_counts["series"] = imported
        self.log(f"✅ Imported {imported} series")

    def import_club_leagues(self, conn, relationships: List[Dict]):
        """Import club-league relationships"""
        self.log("📥 Importing club-league relationships...")

        cursor = conn.cursor()
        imported = 0

        for rel in relationships:
            try:
                cursor.execute(
                    """
                    INSERT INTO club_leagues (club_id, league_id, created_at)
                    SELECT c.id, l.id, CURRENT_TIMESTAMP
                    FROM clubs c, leagues l
                    WHERE c.name = %s AND l.league_id = %s
                    ON CONFLICT ON CONSTRAINT unique_club_league DO NOTHING
                """,
                    (rel["club_name"], rel["league_id"]),
                )

                if cursor.rowcount > 0:
                    imported += 1

            except Exception as e:
                self.log(
                    f"❌ Error importing club-league relationship {rel['club_name']}-{rel['league_id']}: {str(e)}",
                    "ERROR",
                )
                raise

        conn.commit()
        self.imported_counts["club_leagues"] = imported
        self.log(f"✅ Imported {imported} club-league relationships")

    def import_series_leagues(self, conn, relationships: List[Dict]):
        """Import series-league relationships"""
        self.log("📥 Importing series-league relationships...")

        cursor = conn.cursor()
        imported = 0

        for rel in relationships:
            try:
                cursor.execute(
                    """
                    INSERT INTO series_leagues (series_id, league_id, created_at)
                    SELECT s.id, l.id, CURRENT_TIMESTAMP
                    FROM series s, leagues l
                    WHERE s.name = %s AND l.league_id = %s
                    ON CONFLICT ON CONSTRAINT unique_series_league DO NOTHING
                """,
                    (rel["series_name"], rel["league_id"]),
                )

                if cursor.rowcount > 0:
                    imported += 1

            except Exception as e:
                self.log(
                    f"❌ Error importing series-league relationship {rel['series_name']}-{rel['league_id']}: {str(e)}",
                    "ERROR",
                )
                raise

        conn.commit()
        self.imported_counts["series_leagues"] = imported
        self.log(f"✅ Imported {imported} series-league relationships")

    def import_teams(self, conn, teams_data: List[Dict]):
        """Import teams into database with team ID preservation using UPSERT"""
        self.log("📥 Importing teams with ID preservation...")

        cursor = conn.cursor()
        imported = 0
        updated = 0
        errors = 0
        skipped = 0

        # First, let's deduplicate the teams_data based on BOTH database constraints:
        # 1. unique_team_club_series_league: (club_id, series_id, league_id)
        # 2. unique_team_name_per_league: (team_name, league_id)

        from collections import defaultdict

        teams_by_club_series_league = defaultdict(list)  # Constraint 1
        teams_by_name_league = defaultdict(list)  # Constraint 2

        for team in teams_data:
            constraint_key_1 = (
                team["club_name"],
                team["series_name"],
                team["league_id"],
            )
            constraint_key_2 = (team["team_name"], team["league_id"])

            teams_by_club_series_league[constraint_key_1].append(team)
            teams_by_name_league[constraint_key_2].append(team)

        # Log any duplicates found for first constraint
        duplicates_found_1 = 0
        for constraint_key, team_list in teams_by_club_series_league.items():
            if len(team_list) > 1:
                duplicates_found_1 += 1
                if duplicates_found_1 <= 5:  # Log first 5 duplicates
                    club_name, series_name, league_id = constraint_key
                    self.log(
                        f"🔍 DUPLICATE CONSTRAINT: {club_name} / {series_name} / {league_id}",
                        "INFO",
                    )
                    for i, team in enumerate(team_list, 1):
                        self.log(f"   {i}. Team name: {team['team_name']}", "INFO")

        # Log any duplicates found for second constraint
        duplicates_found_2 = 0
        for constraint_key, team_list in teams_by_name_league.items():
            if len(team_list) > 1:
                duplicates_found_2 += 1
                if duplicates_found_2 <= 5:  # Log first 5 duplicates
                    team_name, league_id = constraint_key
                    self.log(
                        f"🔍 DUPLICATE CONSTRAINT 2: {team_name} / {league_id}", "INFO"
                    )
                    for i, team in enumerate(team_list, 1):
                        self.log(
                            f"   {i}. Club/Series: {team['club_name']} / {team['series_name']}",
                            "INFO",
                        )

        if duplicates_found_1 > 0:
            self.log(
                f"📊 Found {duplicates_found_1} club/series/league duplicates", "INFO"
            )
        if duplicates_found_2 > 0:
            self.log(
                f"📊 Found {duplicates_found_2} team name/league duplicates", "INFO"
            )

        # Deduplicate by both constraints - use a two-stage approach
        # Stage 1: Deduplicate by club/series/league (first constraint)
        teams_stage_1 = []
        for constraint_key, team_list in teams_by_club_series_league.items():
            teams_stage_1.append(team_list[0])  # Use first occurrence

        # Stage 2: Deduplicate by team name/league (second constraint)
        teams_by_name_league_stage_2 = defaultdict(list)
        for team in teams_stage_1:
            constraint_key_2 = (team["team_name"], team["league_id"])
            teams_by_name_league_stage_2[constraint_key_2].append(team)

        teams_to_process = []
        name_conflicts_resolved = 0
        for constraint_key, team_list in teams_by_name_league_stage_2.items():
            if len(team_list) > 1:
                name_conflicts_resolved += 1
                # For name conflicts, modify the team names to make them unique
                team_name, league_id = constraint_key
                for i, team in enumerate(team_list):
                    if i > 0:  # Keep first one as-is, modify others
                        original_name = team["team_name"]
                        # Make it unique by adding series info
                        team["team_name"] = f"{original_name} ({team['series_name']})"
                        if name_conflicts_resolved <= 3:  # Log first 3 resolutions
                            self.log(
                                f"🔧 Resolved name conflict: {original_name} → {team['team_name']}"
                            )
                    # Add each team to the processing list (all teams in the conflict group)
                    teams_to_process.append(team)
            else:
                # Only one team with this name in this league
                teams_to_process.append(team_list[0])

        if name_conflicts_resolved > 0:
            self.log(f"🔧 Resolved {name_conflicts_resolved} team name conflicts")

        self.log(
            f"📊 Processing {len(teams_to_process)} unique teams (deduplicated from {len(teams_data)})"
        )

        for team in teams_to_process:
            try:
                club_name = team["club_name"]
                series_name = team["series_name"]
                league_id = team["league_id"]
                team_name = team["team_name"]

                # Create team alias for display (optional)
                team_alias = self.generate_team_alias(team_name, series_name)

                # Verify that the club, series, and league exist
                cursor.execute(
                    """
                    SELECT c.id, s.id, l.id 
                    FROM clubs c, series s, leagues l
                    WHERE c.name = %s AND s.name = %s AND l.league_id = %s
                """,
                    (club_name, series_name, league_id),
                )

                refs = cursor.fetchone()

                if not refs:
                    self.log(
                        f"⚠️  Skipping team {team_name}: missing references (club: {club_name}, series: {series_name}, league: {league_id})",
                        "WARNING",
                    )
                    skipped += 1
                    continue

                club_id, series_id, league_db_id = refs

                # ENHANCEMENT: Use UPSERT to preserve team IDs
                # This allows direct backup/restore using team IDs instead of complex matching
                display_name = team_name  # Can be customized later if needed
                
                cursor.execute(
                    """
                    INSERT INTO teams (club_id, series_id, league_id, team_name, team_alias, display_name, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (club_id, series_id, league_id) DO UPDATE SET
                        team_name = EXCLUDED.team_name,
                        team_alias = EXCLUDED.team_alias,
                        display_name = EXCLUDED.display_name,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id, (xmax = 0) as is_insert
                """,
                    (club_id, series_id, league_db_id, team_name, team_alias, display_name),
                )
                
                result = cursor.fetchone()
                team_id, is_insert = result
                
                if is_insert:
                    imported += 1
                    self.log(f"   ✅ Created team: {team_name} (ID: {team_id})")
                else:
                    updated += 1
                    self.log(f"   📝 Updated team: {team_name} (ID: {team_id})")

            except Exception as e:
                errors += 1
                if errors <= 10:
                    self.log(
                        f"❌ Error importing team {team.get('team_name', 'Unknown')}: {str(e)}",
                        "ERROR",
                    )

                if errors > 25:  # Reduced threshold since we deduplicated
                    self.log(
                        f"❌ Too many team import errors ({errors}), stopping", "ERROR"
                    )
                    raise Exception(f"Too many team import errors ({errors})")

        conn.commit()
        self.log(f"✅ Team import completed: {imported} created, {updated} updated, {skipped} skipped, {errors} errors")
        return imported + updated

    def generate_team_alias(self, team_name: str, series_name: str) -> str:
        """Generate a user-friendly team alias"""
        # Examples:
        # APTA_CHICAGO: "Tennaqua - 22" -> "Series 22"
        # NSTF: "Tennaqua S2B" -> "Series 2B"

        # Handle APTA_CHICAGO format: "Club - Suffix"
        if " - " in team_name:
            parts = team_name.split(" - ")
            if len(parts) >= 2:
                suffix = parts[1].strip()
                return f"Series {suffix}"

        # Handle NSTF format: "Club SSuffix"
        # Must be " S" followed by number or number+letter (not words like "Shore")
        import re

        if re.search(r" S\d", team_name):  # " S" followed by a digit
            parts = team_name.split(" S")
            if len(parts) >= 2:
                suffix = parts[1].strip()
                return f"Series {suffix}"

        # Fallback: use series name
        return series_name

    def import_players(self, conn, players_data: List[Dict]):
        """Import players data with enhanced conflict detection"""
        self.log("📥 Importing players with enhanced conflict detection...")

        cursor = conn.cursor()
        imported = 0
        updated = 0
        errors = 0
        player_id_tracker = {}  # Track multiple records per Player ID

        # First pass: analyze for potential conflicts
        self.log("🔍 Step 1: Analyzing potential conflicts...")
        conflicts_found = 0
        for player in players_data:
            player_id = player.get("Player ID", "").strip()
            league_id = normalize_league_id(player.get("League", "").strip())
            club_name = player.get("Club", "").strip()
            series_name = player.get("Series", "").strip()

            if player_id and league_id:
                key = f"{league_id}::{player_id}"
                if key not in player_id_tracker:
                    player_id_tracker[key] = []
                player_id_tracker[key].append(
                    {
                        "club": club_name,
                        "series": series_name,
                        "name": f"{player.get('First Name', '')} {player.get('Last Name', '')}",
                    }
                )

        # Log conflicts found
        for key, records in player_id_tracker.items():
            if len(records) > 1:
                conflicts_found += 1
                if conflicts_found <= 5:  # Log first 5 conflicts as examples
                    league, player_id = key.split("::")
                    self.log(
                        f"🔍 CONFLICT DETECTED: Player ID {player_id} in {league}",
                        "INFO",
                    )
                    for i, record in enumerate(records, 1):
                        self.log(
                            f"   {i}. {record['name']} at {record['club']} / {record['series']}",
                            "INFO",
                        )

        if conflicts_found > 0:
            self.log(
                f"📊 Found {conflicts_found} Player IDs with multiple club/series records",
                "INFO",
            )
            self.log("✅ Enhanced constraint will allow all records to coexist", "INFO")

        # Second pass: import players
        self.log("📥 Step 2: Importing player records...")

        for player in players_data:
            try:
                # Extract and clean data
                tenniscores_player_id = player.get("Player ID", "").strip()
                first_name = player.get("First Name", "").strip()
                last_name = player.get("Last Name", "").strip()
                raw_league_id = player.get("League", "").strip()
                league_id = normalize_league_id(raw_league_id) if raw_league_id else ""
                # The "Club" field needs parsing to remove team numbers (e.g., "Birchwood 1" -> "Birchwood")
                team_name = player.get("Club", "").strip()
                club_name = self.extract_club_name_from_team(team_name)
                raw_series_name = player.get("Series", "").strip()
                # Convert series name using mapping
                series_name = self.map_series_name(raw_series_name, league_id)

                # Parse PTI - handle both string and numeric types
                pti_value = player.get("PTI", "")
                pti = None
                if pti_value is not None and pti_value != "":
                    if isinstance(pti_value, (int, float)):
                        pti = float(pti_value)
                    else:
                        pti_str = str(pti_value).strip()
                        if pti_str and pti_str.upper() != "N/A":
                            try:
                                pti = float(pti_str)
                            except ValueError:
                                pass

                # Parse wins/losses
                wins = self._parse_int(player.get("Wins", "0"))
                losses = self._parse_int(player.get("Losses", "0"))

                # Parse win percentage - handle both string and numeric types
                win_pct_value = player.get("Win %", "0.0%")
                win_percentage = 0.0
                if isinstance(win_pct_value, (int, float)):
                    win_percentage = float(win_pct_value)
                else:
                    try:
                        win_pct_str = str(win_pct_value).replace("%", "").strip()
                        win_percentage = float(win_pct_str)
                    except (ValueError, AttributeError):
                        pass

                # Captain status - handle different data types
                captain_value = player.get("Captain", "")
                captain_status = (
                    str(captain_value).strip() if captain_value is not None else ""
                )

                if not all([tenniscores_player_id, first_name, last_name, league_id]):
                    self.log(
                        f"⚠️  Skipping player with missing required data: {player}",
                        "WARNING",
                    )
                    continue

                # Check if this exact combination already exists
                cursor.execute(
                    """
                    SELECT p.id FROM players p
                    JOIN leagues l ON p.league_id = l.id
                    LEFT JOIN clubs c ON p.club_id = c.id
                    LEFT JOIN series s ON p.series_id = s.id
                    WHERE p.tenniscores_player_id = %s 
                    AND l.league_id = %s
                    AND LOWER(COALESCE(c.name, '')) = LOWER(%s)
                    AND LOWER(COALESCE(s.name, '')) = LOWER(%s)
                """,
                    (
                        tenniscores_player_id,
                        league_id,
                        club_name or "",
                        series_name or "",
                    ),
                )

                existing_player = cursor.fetchone()
                is_update = existing_player is not None

                cursor.execute(
                    """
                    INSERT INTO players (
                        tenniscores_player_id, first_name, last_name, 
                        league_id, club_id, series_id, team_id, pti, wins, losses, 
                        win_percentage, captain_status, is_active, created_at
                    )
                    SELECT 
                        %s, %s, %s,
                        l.id, c.id, s.id, t.id, %s, %s, %s,
                        %s, %s, true, CURRENT_TIMESTAMP
                    FROM leagues l
                    LEFT JOIN clubs c ON LOWER(c.name) = LOWER(%s)
                    LEFT JOIN series s ON LOWER(s.name) = LOWER(%s)
                    LEFT JOIN teams t ON (
                        t.club_id = c.id AND 
                        t.league_id = l.id AND
                        (
                            -- Direct series match
                            t.series_id = s.id
                            OR
                            -- NSTF fallback: match team_alias to series name
                            (t.team_alias IS NOT NULL AND t.team_alias = s.name)
                        )
                    )
                    WHERE l.league_id = %s
                    ON CONFLICT ON CONSTRAINT unique_player_in_league_club_series DO UPDATE SET
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        team_id = EXCLUDED.team_id,
                        pti = EXCLUDED.pti,
                        wins = EXCLUDED.wins,
                        losses = EXCLUDED.losses,
                        win_percentage = EXCLUDED.win_percentage,
                        captain_status = EXCLUDED.captain_status,
                        is_active = EXCLUDED.is_active,
                        updated_at = CURRENT_TIMESTAMP
                """,
                    (
                        tenniscores_player_id,
                        first_name,
                        last_name,
                        pti,
                        wins,
                        losses,
                        win_percentage,
                        captain_status,
                        club_name,
                        series_name,
                        league_id,
                    ),
                )

                if is_update:
                    updated += 1
                else:
                    imported += 1

                if (imported + updated) % 1000 == 0:
                    self.log(
                        f"   📊 Processed {imported + updated:,} players so far (New: {imported:,}, Updated: {updated:,})..."
                    )
                    self._increment_operation_count(1000)
                    conn.commit()  # Commit in batches
                    
                    # Check for connection rotation on Railway
                    if self.is_railway and self._should_rotate_connection():
                        self.check_and_rotate_connection_if_needed(conn)

            except Exception as e:
                errors += 1
                if errors <= 10:  # Only log first 10 errors
                    self.log(
                        f"❌ Error importing player {player.get('Player ID', 'Unknown')}: {str(e)}",
                        "ERROR",
                    )

                if errors > 100:  # Stop if too many errors
                    self.log(
                        f"❌ Too many errors ({errors}), stopping player import",
                        "ERROR",
                    )
                    raise Exception(f"Too many player import errors ({errors})")

        conn.commit()
        self.imported_counts["players"] = imported + updated
        
        # Validate team assignments
        self.log("🔍 Validating team assignments...")
        try:
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM players 
                WHERE team_id IS NULL AND is_active = TRUE
            """)
            unassigned_count = cursor.fetchone()[0]
            
            if unassigned_count > 0:
                self.log(f"⚠️  WARNING: {unassigned_count} players still have no team_id assigned", "WARNING")
                
                # Log some examples for debugging
                cursor.execute("""
                    SELECT p.first_name, p.last_name, c.name as club, s.name as series, l.league_name
                    FROM players p
                    LEFT JOIN clubs c ON p.club_id = c.id
                    LEFT JOIN series s ON p.series_id = s.id
                    LEFT JOIN leagues l ON p.league_id = l.id
                    WHERE p.team_id IS NULL AND p.is_active = TRUE
                    LIMIT 5
                """)
                examples = cursor.fetchall()
                
                self.log("   Examples of players without team assignments:")
                for example in examples:
                    if len(example) >= 5:
                        self.log(f"     - {example[0]} {example[1]} ({example[2]} - {example[3]} - {example[4]})", "WARNING")
                    else:
                        self.log(f"     - Incomplete data: {example}", "WARNING")
            else:
                self.log("✅ All players have team_id assigned successfully")
        except Exception as e:
            self.log(f"⚠️  Warning: Could not validate team assignments: {str(e)}", "WARNING")
        
        self.log(
            f"✅ Player import complete: {imported:,} new, {updated:,} updated, {errors} errors"
        )
        self.log(
            f"🎯 Conflict resolution: {conflicts_found} Player IDs now exist across multiple clubs/series"
        )

    def import_career_stats(self, conn, player_history_data: List[Dict]):
        """Import career stats from player_history.json into players table career columns"""
        self.log("📥 Importing career stats...")

        cursor = conn.cursor()
        updated = 0
        not_found = 0
        errors = 0

        for player_data in player_history_data:
            try:
                # Extract career stats from JSON
                player_name = player_data.get("name", "")
                career_wins = player_data.get("wins", 0)
                career_losses = player_data.get("losses", 0)
                tenniscores_id = player_data.get("player_id", "").strip()

                if not tenniscores_id:
                    continue

                # Calculate derived stats
                career_matches = career_wins + career_losses
                career_win_percentage = (
                    round((career_wins / career_matches) * 100, 2)
                    if career_matches > 0
                    else 0.00
                )

                # Find and update the player in the database
                cursor.execute(
                    """
                    UPDATE players 
                    SET 
                        career_wins = %s,
                        career_losses = %s, 
                        career_matches = %s,
                        career_win_percentage = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE tenniscores_player_id = %s
                """,
                    (
                        career_wins,
                        career_losses,
                        career_matches,
                        career_win_percentage,
                        tenniscores_id,
                    ),
                )

                if cursor.rowcount > 0:
                    updated += 1

                    # Log progress for significant players
                    if career_matches >= 20 and updated % 50 == 0:
                        self.log(f"   📊 Updated {updated:,} career stats so far...")
                else:
                    not_found += 1

            except Exception as e:
                errors += 1
                if errors <= 10:
                    self.log(
                        f"❌ Error updating career stats for {player_name}: {str(e)}",
                        "ERROR",
                    )

                if errors > 100:
                    self.log(
                        f"❌ Too many career stats errors ({errors}), stopping", "ERROR"
                    )
                    raise Exception(f"Too many career stats import errors ({errors})")

        conn.commit()
        self.imported_counts["career_stats"] = updated
        self.log(
            f"✅ Updated {updated:,} players with career stats ({not_found} not found, {errors} errors)"
        )

    def import_player_history(self, conn, player_history_data: List[Dict]):
        """Import player history data with enhanced player ID validation and connection resilience"""
        self.log("📥 Importing player history with enhanced player ID validation...")

        cursor = conn.cursor()
        imported = 0
        errors = 0
        player_id_fixes = 0
        skipped_players = 0
        
        # Add progress tracking for large datasets
        total_players = len(player_history_data)
        progress_interval = max(100, total_players // 10)  # Report progress every 10% or 100 records
        
        self.log(f"📊 Processing {total_players:,} player history records...")

        for player_idx, player_record in enumerate(player_history_data):
            try:
                # Add connection health check for long-running processes
                if player_idx > 0 and player_idx % 1000 == 0:
                    try:
                        # Test connection health
                        cursor.execute("SELECT 1")
                        cursor.fetchone()
                    except Exception as conn_error:
                        self.log(f"⚠️ Connection issue detected at record {player_idx}, attempting to recover...", "WARNING")
                        # Could implement connection recovery here if needed
                        pass
                
                # Progress reporting
                if player_idx > 0 and player_idx % progress_interval == 0:
                    progress_pct = (player_idx / total_players) * 100
                    self.log(f"📈 Progress: {player_idx:,}/{total_players:,} players ({progress_pct:.1f}%) - {imported:,} records imported")
                
                original_player_id = player_record.get("player_id", "").strip()
                raw_league_id = player_record.get("league_id", "").strip()
                league_id = normalize_league_id(raw_league_id) if raw_league_id else ""
                series = player_record.get("series", "").strip()
                matches = player_record.get("matches", [])
                player_name = player_record.get("name", "").strip()

                if not all([original_player_id, league_id]) or not matches:
                    skipped_players += 1
                    continue

                # CRITICAL FIX: Validate and resolve player ID using fallback matching
                first_name, last_name = self._parse_player_name(player_name)
                validated_player_id = self.player_validator.validate_and_resolve_player_id(
                    conn=conn,
                    tenniscores_player_id=original_player_id,
                    first_name=first_name,
                    last_name=last_name,
                    club_name="",  # Not available in player history data
                    series_name=series,
                    league_id=league_id
                )
                
                if not validated_player_id:
                    skipped_players += 1
                    continue
                    
                if validated_player_id != original_player_id:
                    player_id_fixes += 1

                # Get the database player ID using validated player ID
                cursor.execute(
                    """
                    SELECT p.id, l.id 
                    FROM players p 
                    JOIN leagues l ON l.league_id = %s
                    WHERE p.tenniscores_player_id = %s AND p.league_id = l.id
                """,
                    (league_id, validated_player_id),
                )

                result = cursor.fetchone()
                if not result:
                    skipped_players += 1
                    continue

                db_player_id, db_league_id = result

                # Import each match history record
                for match in matches:
                    try:
                        date_str = match.get("date", "").strip()
                        end_pti = match.get("end_pti")
                        match_series = match.get("series", series).strip()

                        # Parse date
                        record_date = None
                        if date_str:
                            try:
                                record_date = datetime.strptime(
                                    date_str, "%m/%d/%Y"
                                ).date()
                            except ValueError:
                                try:
                                    record_date = datetime.strptime(
                                        date_str, "%Y-%m-%d"
                                    ).date()
                                except ValueError:
                                    pass

                        if not record_date:
                            continue

                        cursor.execute(
                            """
                            INSERT INTO player_history (player_id, league_id, series, date, end_pti, created_at)
                            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        """,
                            (
                                db_player_id,
                                db_league_id,
                                match_series,
                                record_date,
                                end_pti,
                            ),
                        )

                        imported += 1

                    except Exception as match_error:
                        errors += 1
                        if errors <= 10:
                            self.log(
                                f"❌ Error importing match for player {validated_player_id}: {str(match_error)}",
                                "ERROR",
                            )

                # More frequent commits for large datasets to prevent timeouts
                if imported % 500 == 0 and imported > 0:
                    self._increment_operation_count(500)
                    conn.commit()  # Commit every 500 records to prevent long transactions
                    
                    # Check for connection rotation on Railway
                    if self.is_railway and self._should_rotate_connection():
                        self.check_and_rotate_connection_if_needed(conn)
                    
                if imported % 2000 == 0 and imported > 0:
                    self.log(
                        f"   📊 Imported {imported:,} player history records so far..."
                    )

            except Exception as e:
                errors += 1
                if errors <= 10:
                    self.log(
                        f"❌ Error importing player history for {original_player_id}: {str(e)}",
                        "ERROR",
                    )

                if errors > 2000:  # Much higher threshold for large imports
                    self.log(
                        f"❌ Too many player history errors ({errors}), stopping",
                        "ERROR",
                    )
                    raise Exception(f"Too many player history import errors ({errors})")

        conn.commit()
        self.imported_counts["player_history"] = imported
        
        # Enhanced completion message with validation stats
        message_parts = [f"✅ Imported {imported:,} player history records ({errors} errors"]
        if player_id_fixes > 0:
            message_parts.append(f"{player_id_fixes} player ID fixes")
        if skipped_players > 0:
            message_parts.append(f"{skipped_players} skipped players")
        message_parts[-1] += ")"
        
        self.log(", ".join(message_parts))

    def validate_and_correct_winner(
        self,
        scores: str,
        winner: str,
        home_team: str,
        away_team: str,
        league_id: str = None,
    ) -> str:
        """
        Validate winner against score data and correct if needed
        Enhanced with league-specific validation logic
        """
        if not scores or not scores.strip():
            return winner

        # Use the enhanced league-aware validation
        from utils.league_utils import normalize_league_id

        normalized_league = normalize_league_id(league_id) if league_id else None

        # Clean up score string and remove tiebreak info
        scores_clean = scores.strip()
        scores_clean = re.sub(r"\s*\[[^\]]+\]", "", scores_clean)

        # Split by comma to get individual sets
        sets = [s.strip() for s in scores_clean.split(",") if s.strip()]

        # CITA League: Skip validation for problematic data patterns
        if normalized_league == "CITA" and len(sets) >= 1:
            for set_score in sets:
                if "-" in set_score:
                    try:
                        parts = set_score.split("-")
                        if len(parts) == 2:
                            home_games = int(parts[0].strip())
                            away_games = int(parts[1].strip())
                            # Skip incomplete CITA matches (like 2-2, 3-3, etc.)
                            if (
                                home_games < 6
                                and away_games < 6
                                and abs(home_games - away_games) <= 2
                                and not (home_games == 0 and away_games == 0)
                            ):
                                return winner  # Don't correct problematic CITA data
                    except (ValueError, IndexError):
                        pass

        home_sets_won = 0
        away_sets_won = 0

        for i, set_score in enumerate(sets):
            if "-" not in set_score:
                continue

            try:
                parts = set_score.split("-")
                if len(parts) != 2:
                    continue

                home_games = int(parts[0].strip())
                away_games = int(parts[1].strip())

                # Handle super tiebreak format (NSTF, CITA)
                if (
                    i == 2
                    and len(sets) == 3
                    and (
                        normalized_league in ["NSTF", "CITA"]
                        or home_games >= 10
                        or away_games >= 10
                    )
                ):
                    # This is a super tiebreak
                    if home_games > away_games:
                        home_sets_won += 1
                    elif away_games > home_games:
                        away_sets_won += 1
                    continue

                # Standard set scoring
                if home_games > away_games:
                    home_sets_won += 1
                elif away_games > home_games:
                    away_sets_won += 1

            except (ValueError, IndexError):
                continue

        # Determine overall winner
        calculated_winner = None
        if home_sets_won > away_sets_won:
            calculated_winner = "home"
        elif away_sets_won > home_sets_won:
            calculated_winner = "away"

        # Return corrected winner if mismatch found
        if calculated_winner and winner.lower() not in ["home", "away"]:
            return calculated_winner
        elif (
            calculated_winner
            and winner.lower() in ["home", "away"]
            and winner.lower() != calculated_winner
        ):
            return calculated_winner
        else:
            return winner

    def _validate_match_player_id(self, conn, player_id: str, player_name: str, 
                                team_name: str, league_id: str) -> Optional[str]:
        """
        Validate and resolve a player ID from match history data.
        Enhanced to handle null IDs with valid names (substitute players).
        
        Args:
            conn: Database connection
            player_id: Original player ID from JSON (may be null)
            player_name: Player name from JSON  
            team_name: Team name to extract club/series info
            league_id: League identifier
            
        Returns:
            str: Valid player ID if found/resolved, None if no match
        """
        # ENHANCED: Handle null player IDs with valid names (substitute players)
        if not player_id and player_name:
            self.log(f"    [IMPORT] Null player ID with name '{player_name}' - attempting cross-league lookup")
            
            # Parse player name
            first_name, last_name = self._parse_player_name(player_name)
            
            if first_name and last_name:
                # Search across ALL leagues for this player name
                cursor = conn.cursor()
                cross_league_query = """
                    SELECT tenniscores_player_id, first_name, last_name, 
                           l.league_id, c.name as club_name, s.name as series_name
                    FROM players p
                    JOIN leagues l ON p.league_id = l.id
                    JOIN clubs c ON p.club_id = c.id
                    JOIN series s ON p.series_id = s.id
                    WHERE LOWER(p.first_name) = LOWER(%s) 
                    AND LOWER(p.last_name) = LOWER(%s)
                    AND p.is_active = TRUE
                    ORDER BY l.league_id
                    LIMIT 1
                """
                cursor.execute(cross_league_query, (first_name, last_name))
                result = cursor.fetchone()
                
                if result:
                    found_id = result[0]
                    found_league = result[3]
                    found_club = result[4]
                    found_series = result[5]
                    self.log(f"    [IMPORT] ✅ Found substitute player: {first_name} {last_name} → {found_id} (League: {found_league}, Club: {found_club})")
                    return found_id
                else:
                    self.log(f"    [IMPORT] ❌ No cross-league match found for: {first_name} {last_name}")
                    return None
        
        # Original logic for non-null player IDs
        if not player_id:
            return None
            
        # Extract club and series from team name
        club_name = self.extract_club_name_from_team(team_name)
        series_name = self._extract_series_from_team_name(team_name, league_id)
        
        # Parse player name
        first_name, last_name = self._parse_player_name(player_name)
        
        # Use the validator to resolve the player ID
        return self.player_validator.validate_and_resolve_player_id(
            conn=conn,
            tenniscores_player_id=player_id,
            first_name=first_name,
            last_name=last_name,
            club_name=club_name,
            series_name=series_name,
            league_id=league_id
        )
    
    def _parse_player_name(self, full_name: str) -> tuple:
        """Parse full name into first and last name components"""
        if not full_name:
            return None, None
            
        # Handle "Last, First" format
        if ", " in full_name:
            parts = full_name.split(", ", 1)
            return parts[1].strip(), parts[0].strip()
        
        # Handle "First Last" format
        name_parts = full_name.strip().split()
        if len(name_parts) >= 2:
            return name_parts[0], " ".join(name_parts[1:])
        elif len(name_parts) == 1:
            return name_parts[0], ""
        
        return None, None
    
    def _extract_series_from_team_name(self, team_name: str, league_id: str) -> str:
        """Extract series name from team name using existing logic"""
        if not team_name:
            return ""
            
        # Use existing parse_schedule_team_name logic
        try:
            club_name, series_name = self.parse_schedule_team_name(team_name)
            if series_name:
                # Apply series mapping
                return self.map_series_name(series_name, league_id)
        except:
            pass
            
        return ""

    def import_match_history(self, conn, match_history_data: List[Dict]):
        """Import match history data into match_scores table with enhanced reliability and batch processing"""
        self.log("📥 Importing match history with enhanced reliability...")

        cursor = conn.cursor()
        imported = 0
        errors = 0
        winner_corrections = 0
        player_id_fixes = 0
        
        # Pre-cache league and team lookups to reduce database calls
        self.log("🔧 Pre-caching league and team data...")
        
        # Cache league mappings
        cursor.execute("SELECT league_id, id FROM leagues")
        league_cache = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Cache team mappings (league_id, team_name) -> team_id
        cursor.execute("""
            SELECT l.league_id, t.team_name, t.id 
            FROM teams t 
            JOIN leagues l ON t.league_id = l.id
        """)
        team_cache = {(row[0], row[1]): row[2] for row in cursor.fetchall()}
        
        # Cache active player IDs for validation
        cursor.execute("SELECT tenniscores_player_id FROM players WHERE is_active = true")
        valid_player_ids = {row[0] for row in cursor.fetchall()}
        
        self.log(f"✅ Cached {len(league_cache)} leagues, {len(team_cache)} teams, {len(valid_player_ids):,} players")

        # Batch processing for better performance and transaction control
        batch_size = 500
        batch_data = []
        
        for record_idx, record in enumerate(match_history_data):
            try:
                # Extract data using the actual field names from the JSON
                match_date_str = (record.get("Date") or "").strip()
                home_team = (record.get("Home Team") or "").strip()
                away_team = (record.get("Away Team") or "").strip()
                scores = record.get("Scores") or ""
                winner = (record.get("Winner") or "").strip()
                raw_league_id = (record.get("league_id") or "").strip()
                league_id = normalize_league_id(raw_league_id) if raw_league_id else ""

                # Extract and validate player IDs with caching
                home_player_1_id = (record.get("Home Player 1 ID") or "").strip()
                home_player_2_id = (record.get("Home Player 2 ID") or "").strip()
                away_player_1_id = (record.get("Away Player 1 ID") or "").strip()
                away_player_2_id = (record.get("Away Player 2 ID") or "").strip()
                
                # Quick validation using cached player IDs (much faster than database calls)
                player_ids = [home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id]
                validated_ids = []
                
                for pid in player_ids:
                    if pid and pid in valid_player_ids:
                        validated_ids.append(pid)
                    else:
                        validated_ids.append(None)  # Invalid or missing player ID
                        if pid:  # Only count as fix if there was an original ID
                            player_id_fixes += 1

                home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id = validated_ids

                # Parse date with better error handling
                match_date = None
                if match_date_str:
                    try:
                        # Try DD-Mon-YY format first
                        match_date = datetime.strptime(match_date_str, "%d-%b-%y").date()
                    except ValueError:
                        try:
                            match_date = datetime.strptime(match_date_str, "%m/%d/%Y").date()
                        except ValueError:
                            try:
                                match_date = datetime.strptime(match_date_str, "%Y-%m-%d").date()
                            except ValueError:
                                pass

                if not all([match_date, home_team, away_team]):
                    continue

                # Validate winner with league-specific logic
                original_winner = winner
                winner = self.validate_and_correct_winner(
                    scores, winner, home_team, away_team, league_id
                )
                if winner != original_winner:
                    winner_corrections += 1

                # Validate winner field - only allow 'home', 'away', or None
                if winner and winner.lower() not in ["home", "away"]:
                    winner = None

                # Generate unique tenniscores_match_id by combining match_id + Line
                base_match_id = record.get("match_id", "").strip()
                line = record.get("Line", "").strip()
                
                # Create unique tenniscores_match_id
                if base_match_id and line:
                    # Extract line number (e.g., "Line 1" -> "Line1", "Line 2" -> "Line2")
                    line_number = line.replace(" ", "")  # "Line 1" -> "Line1"
                    tenniscores_match_id = f"{base_match_id}_{line_number}"
                else:
                    # Fallback: use original match_id if line info is missing
                    tenniscores_match_id = base_match_id

                # Use cached lookups instead of database queries
                league_db_id = league_cache.get(league_id)
                home_team_id = team_cache.get((league_id, home_team)) if home_team != "BYE" else None
                away_team_id = team_cache.get((league_id, away_team)) if away_team != "BYE" else None

                # Add to batch (including tenniscores_match_id)
                batch_data.append((
                    match_date, home_team, away_team, home_team_id, away_team_id,
                    home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id,
                    str(scores), winner, league_db_id, tenniscores_match_id
                ))

                # Process batch when it reaches batch_size or at the end
                if len(batch_data) >= batch_size or record_idx == len(match_history_data) - 1:
                    imported_count = self._process_match_batch(cursor, batch_data)
                    imported += imported_count
                    batch_data = []  # Clear batch
                    
                    # Commit after each successful batch
                    conn.commit()
                    
                    if imported % 2000 == 0:
                        self.log(f"   📊 Imported {imported:,} match records so far...")
                        self._increment_operation_count(2000)
                        
                        # Check for connection rotation on Railway
                        if self.is_railway and self._should_rotate_connection():
                            self.check_and_rotate_connection_if_needed(conn)

            except Exception as e:
                errors += 1
                if errors <= 10:
                    self.log(f"❌ Error processing match record {record_idx}: {str(e)}", "ERROR")

                # Don't fail entire import for individual record errors
                if errors > 1000:  # Much higher threshold than before
                    self.log(f"❌ Too many match history errors ({errors}), stopping", "ERROR")
                    break

        # Process any remaining batch data
        if batch_data:
            imported_count = self._process_match_batch(cursor, batch_data)
            imported += imported_count
            conn.commit()

        self.imported_counts["match_scores"] = imported
        
        # Enhanced completion message
        message_parts = [f"✅ Imported {imported:,} match history records ({errors} errors"]
        if winner_corrections > 0:
            message_parts.append(f"{winner_corrections} winner corrections")
        if player_id_fixes > 0:
            message_parts.append(f"{player_id_fixes} player ID fixes")
        message_parts[-1] += ")"
        
        self.log(", ".join(message_parts))

    def _process_match_batch(self, cursor, batch_data):
        """Process a batch of match records with improved error handling and Railway optimization"""
        if not batch_data:
            return 0
        
        # RAILWAY OPTIMIZATION: Use smaller batch sizes on Railway
        actual_batch_size = min(len(batch_data), self.batch_size) if self.is_railway else len(batch_data)
        
        # Process in smaller chunks if on Railway
        if self.is_railway and len(batch_data) > self.batch_size:
            total_successful = 0
            for i in range(0, len(batch_data), self.batch_size):
                chunk = batch_data[i:i + self.batch_size]
                successful = self._process_match_batch(cursor, chunk)
                total_successful += successful
                
                # Force frequent commits on Railway to prevent memory issues
                if i % (self.batch_size * 2) == 0:
                    cursor.connection.commit()
                    self.log(f"🚂 Railway: Committed batch {i//self.batch_size + 1}, {total_successful} records processed so far")
                    
            return total_successful
            
        try:
            # Use executemany for better performance
            cursor.executemany(
                """
                INSERT INTO match_scores (
                    match_date, home_team, away_team, home_team_id, away_team_id,
                    home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id, 
                    scores, winner, league_id, tenniscores_match_id, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (tenniscores_match_id) WHERE tenniscores_match_id IS NOT NULL DO UPDATE
                SET
                    match_date = EXCLUDED.match_date,
                    home_team = EXCLUDED.home_team,
                    away_team = EXCLUDED.away_team,
                    home_team_id = EXCLUDED.home_team_id,
                    away_team_id = EXCLUDED.away_team_id,
                    home_player_1_id = EXCLUDED.home_player_1_id,
                    home_player_2_id = EXCLUDED.home_player_2_id,
                    away_player_1_id = EXCLUDED.away_player_1_id,
                    away_player_2_id = EXCLUDED.away_player_2_id,
                    scores = EXCLUDED.scores,
                    winner = EXCLUDED.winner,
                    league_id = EXCLUDED.league_id
                """,
                batch_data
            )
            
            # RAILWAY OPTIMIZATION: Force commit after each batch on Railway
            if self.is_railway:
                cursor.connection.commit()
                
            return len(batch_data)
            
        except Exception as e:
            self.log(f"❌ Batch insert failed, trying individual inserts: {str(e)}", "WARNING")
            
            # RAILWAY OPTIMIZATION: Use smaller retry batches on Railway
            retry_batch_size = 10 if self.is_railway else len(batch_data)
            
            # Fallback: try individual inserts to salvage what we can
            successful = 0
            for i, record_data in enumerate(batch_data):
                try:
                    cursor.execute(
                        """
                        INSERT INTO match_scores (
                            match_date, home_team, away_team, home_team_id, away_team_id,
                            home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id, 
                            scores, winner, league_id, tenniscores_match_id, created_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (tenniscores_match_id) WHERE tenniscores_match_id IS NOT NULL DO UPDATE
                        SET
                            match_date = EXCLUDED.match_date,
                            home_team = EXCLUDED.home_team,
                            away_team = EXCLUDED.away_team,
                            home_team_id = EXCLUDED.home_team_id,
                            away_team_id = EXCLUDED.away_team_id,
                            home_player_1_id = EXCLUDED.home_player_1_id,
                            home_player_2_id = EXCLUDED.home_player_2_id,
                            away_player_1_id = EXCLUDED.away_player_1_id,
                            away_player_2_id = EXCLUDED.away_player_2_id,
                            scores = EXCLUDED.scores,
                            winner = EXCLUDED.winner,
                            league_id = EXCLUDED.league_id
                        """,
                        record_data
                    )
                    successful += 1
                    
                    # RAILWAY OPTIMIZATION: Commit frequently during individual inserts
                    if self.is_railway and successful % 10 == 0:
                        cursor.connection.commit()
                        
                except Exception as individual_error:
                    # Log individual failures but continue
                    continue
                    
            if successful > 0:
                self.log(f"✅ Salvaged {successful}/{len(batch_data)} records from failed batch")
                if self.is_railway:
                    cursor.connection.commit()  # Final commit for Railway
            
            return successful

    def import_series_stats(self, conn, series_stats_data: List[Dict]):
        """Import series stats data with validation and calculation fallback"""
        self.log("📥 Importing series stats...")

        cursor = conn.cursor()
        imported = 0
        errors = 0
        league_not_found_count = 0
        skipped_count = 0

        # Debug: Check what leagues exist in the database
        cursor.execute("SELECT league_id FROM leagues ORDER BY league_id")
        existing_leagues = [row[0] for row in cursor.fetchall()]
        self.log(
            f"🔍 Debug: Found {len(existing_leagues)} leagues in database: {existing_leagues}"
        )

        for record in series_stats_data:
            try:
                series = record.get("series", "").strip()
                team = record.get("team", "").strip()
                raw_league_id = record.get("league_id", "").strip()
                league_id = normalize_league_id(raw_league_id) if raw_league_id else ""
                # Use the authoritative points from JSON source data
                points = record.get('points', 0)  # JSON contains correct point totals

                # Extract match stats
                matches = record.get("matches", {})
                matches_won = matches.get("won", 0)
                matches_lost = matches.get("lost", 0)
                matches_tied = matches.get("tied", 0)

                # Extract line stats
                lines = record.get("lines", {})
                lines_won = lines.get("won", 0)
                lines_lost = lines.get("lost", 0)
                lines_for = lines.get("for", 0)
                lines_ret = lines.get("ret", 0)

                # Extract set stats
                sets = record.get("sets", {})
                sets_won = sets.get("won", 0)
                sets_lost = sets.get("lost", 0)

                # Extract game stats
                games = record.get("games", {})
                games_won = games.get("won", 0)
                games_lost = games.get("lost", 0)

                if not all([series, team, league_id]):
                    skipped_count += 1
                    continue

                # FIX: Handle series name format mismatches
                # Convert "Series X" to "Division X" for CNSWPL compatibility
                original_series = series
                if series.startswith("Series ") and league_id == "CNSWPL":
                    series = series.replace("Series ", "Division ")
                    self.log(
                        f"🔧 Converted series name: {record.get('series')} → {series} for team {team}"
                    )

                # Get league database ID with better error handling
                cursor.execute(
                    "SELECT id FROM leagues WHERE league_id = %s", (league_id,)
                )
                league_row = cursor.fetchone()

                if not league_row:
                    league_not_found_count += 1
                    if league_not_found_count <= 5:  # Only log first 5 missing leagues
                        self.log(
                            f"⚠️  League not found: {league_id} for team {team} (raw: {raw_league_id})",
                            "WARNING",
                        )
                    continue

                league_db_id = league_row[0]

                # Get series_id and team_id from database
                cursor.execute(
                    """
                    SELECT s.id as series_id, t.id as team_id 
                    FROM series s
                    JOIN series_leagues sl ON s.id = sl.series_id
                    LEFT JOIN teams t ON s.id = t.series_id AND t.team_name = %s AND t.league_id = %s
                    WHERE s.name = %s AND sl.league_id = %s
                """,
                    (team, league_db_id, series, league_db_id),
                )

                lookup_row = cursor.fetchone()
                if lookup_row:
                    series_db_id = lookup_row[0]  # series_id is first column
                    team_db_id = lookup_row[1]   # team_id is second column (may be None)
                else:
                    # Fallback: try to get just series_id without team matching
                    cursor.execute(
                        """
                        SELECT s.id FROM series s
                        JOIN series_leagues sl ON s.id = sl.series_id
                        WHERE s.name = %s AND sl.league_id = %s
                    """,
                        (series, league_db_id),
                    )
                    series_row = cursor.fetchone()
                    series_db_id = series_row[0] if series_row else None
                    team_db_id = None

                cursor.execute(
                    """
                    INSERT INTO series_stats (
                        series, team, series_id, team_id, points, matches_won, matches_lost, matches_tied,
                        lines_won, lines_lost, lines_for, lines_ret,
                        sets_won, sets_lost, games_won, games_lost,
                        league_id, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (league_id, series, team) DO UPDATE SET
                        points = EXCLUDED.points,
                        matches_won = EXCLUDED.matches_won,
                        matches_lost = EXCLUDED.matches_lost,
                        matches_tied = EXCLUDED.matches_tied,
                        lines_won = EXCLUDED.lines_won,
                        lines_lost = EXCLUDED.lines_lost,
                        lines_for = EXCLUDED.lines_for,
                        lines_ret = EXCLUDED.lines_ret,
                        sets_won = EXCLUDED.sets_won,
                        sets_lost = EXCLUDED.sets_lost,
                        games_won = EXCLUDED.games_won,
                        games_lost = EXCLUDED.games_lost,
                        series_id = EXCLUDED.series_id,
                        team_id = EXCLUDED.team_id,
                        updated_at = CURRENT_TIMESTAMP
                """,
                    (
                        series,
                        team,
                        series_db_id,
                        team_db_id,
                        points,
                        matches_won,
                        matches_lost,
                        matches_tied,
                        lines_won,
                        lines_lost,
                        lines_for,
                        lines_ret,
                        sets_won,
                        sets_lost,
                        games_won,
                        games_lost,
                        league_db_id,
                    ),
                )

                if cursor.rowcount > 0:
                    imported += 1

                # RAILWAY OPTIMIZATION: Commit more frequently on Railway to prevent memory/transaction issues
                commit_freq = self.commit_frequency
                if imported % commit_freq == 0:
                    self._increment_operation_count(commit_freq)
                    conn.commit()
                    if self.is_railway:
                        self.log(f"🚂 Railway: Committed {imported} series_stats records")
                        
                        # Check for connection rotation on Railway
                        if self._should_rotate_connection():
                            self.check_and_rotate_connection_if_needed(conn)

            except Exception as e:
                errors += 1
                if errors <= 10:
                    self.log(
                        f"❌ Error importing series stats record: {str(e)}", "ERROR"
                    )

                if errors > 100:
                    self.log(
                        f"❌ Too many series stats errors ({errors}), stopping", "ERROR"
                    )
                    raise Exception(f"Too many series stats import errors ({errors})")

        conn.commit()
        self.imported_counts["series_stats"] = imported

        # Summary logging
        if league_not_found_count > 0:
            self.log(
                f"⚠️  {league_not_found_count} series stats records skipped due to missing leagues",
                "WARNING",
            )
        if skipped_count > 0:
            self.log(
                f"⚠️  {skipped_count} series stats records skipped due to missing data",
                "WARNING",
            )

        self.log(
            f"✅ Imported {imported:,} series stats records ({errors} errors, {league_not_found_count} missing leagues, {skipped_count} skipped)"
        )

        # Only recalculate points if there are teams with zero points (indicating missing/incomplete data)
        cursor.execute("SELECT COUNT(*) FROM series_stats WHERE points = 0")
        teams_with_zero_points = cursor.fetchone()[0]
        
        if teams_with_zero_points > 0:
            self.log(f"🔧 Found {teams_with_zero_points} teams with zero points, recalculating only those...")
            self.recalculate_missing_team_points(conn)
        else:
            self.log(f"✅ All teams have point data from JSON, skipping recalculation")

        # Validate the import results
        self.validate_series_stats_import(conn)
        
        # CRITICAL: Auto-populate missing series_id values - fail if unsuccessful
        series_id_success = self.auto_populate_series_ids(conn)
        if not series_id_success:
            self.log("🚨 CRITICAL: Series ID auto-population failed!", "ERROR")
            self.log("🔧 ETL process cannot continue with poor series_id coverage", "ERROR")
            # Don't fail the entire ETL, but log the critical issue
            self.log("⚠️  Continuing ETL but series functionality may be impaired", "WARNING")

    def validate_series_stats_import(self, conn):
        """Validate series stats import and trigger calculation fallback if needed"""
        self.log("🔍 Validating series stats import...")

        cursor = conn.cursor()

        # Check total teams imported
        cursor.execute("SELECT COUNT(*) FROM series_stats")
        total_teams = cursor.fetchone()[0]

        # Check teams with matches in match_scores that should have series stats
        cursor.execute(
            """
            SELECT COUNT(DISTINCT COALESCE(home_team, away_team))
            FROM (
                SELECT home_team, NULL as away_team FROM match_scores WHERE home_team IS NOT NULL
                UNION ALL
                SELECT NULL as home_team, away_team FROM match_scores WHERE away_team IS NOT NULL
            ) all_teams
            WHERE COALESCE(home_team, away_team) IS NOT NULL
        """
        )
        expected_teams = cursor.fetchone()[0]

        # Calculate coverage percentage
        coverage_percentage = (
            (total_teams / expected_teams * 100) if expected_teams > 0 else 0
        )

        self.log(f"📊 Series stats validation:")
        self.log(f"   Imported teams: {total_teams:,}")
        self.log(f"   Expected teams: {expected_teams:,}")
        self.log(f"   Coverage: {coverage_percentage:.1f}%")

        # Only trigger fallback calculation if coverage is extremely low (< 50%)
        # This preserves the correct JSON data for normal operations
        if coverage_percentage < 50:
            self.log(
                f"⚠️  CRITICAL: Series stats coverage ({coverage_percentage:.1f}%) is below 50% threshold",
                "WARNING",
            )
            self.log(
                f"🔧 Triggering calculation fallback due to severely incomplete data..."
            )

            # Clear existing data and recalculate from match results
            self.calculate_series_stats_from_matches(conn)
        elif coverage_percentage < 90:
            self.log(
                f"⚠️  WARNING: Series stats coverage ({coverage_percentage:.1f}%) is below 90%, but preserving JSON data",
                "WARNING",
            )
        else:
            self.log(
                f"✅ Series stats validation passed ({coverage_percentage:.1f}% coverage)"
            )

    def auto_populate_series_ids(self, conn):
        """Auto-populate missing series_id values in series_stats table with enhanced error handling"""
        self.log("🔄 Auto-populating missing series_id values...")
        
        cursor = conn.cursor()
        
        try:
            # Count records without series_id
            cursor.execute("SELECT COUNT(*) FROM series_stats WHERE series_id IS NULL")
            null_count = cursor.fetchone()[0]
            
            if null_count == 0:
                self.log("✅ All series_stats records already have series_id")
                return True
                
            self.log(f"🔍 Found {null_count} records without series_id, attempting to populate...")
            
            # Get records without series_id
            cursor.execute("""
                SELECT id, series, league_id 
                FROM series_stats 
                WHERE series_id IS NULL
            """)
            
            records_to_update = cursor.fetchall()
            updated_count = 0
            failed_count = 0
            failed_records = []
            
            for record in records_to_update:
                record_id = record[0]
                series_name = record[1]
                league_id = record[2]
                
                try:
                    # Try multiple matching strategies
                    series_id = self._find_series_id_for_name(cursor, series_name, league_id)
                    
                    if series_id:
                        cursor.execute("""
                            UPDATE series_stats 
                            SET series_id = %s 
                            WHERE id = %s
                        """, (series_id, record_id))
                        updated_count += 1
                    else:
                        failed_count += 1
                        failed_records.append(f"{series_name} (League: {league_id})")
                        
                except Exception as e:
                    failed_count += 1
                    failed_records.append(f"{series_name} (League: {league_id}) - Error: {str(e)}")
                    self.log(f"❌ Error updating record {record_id}: {str(e)}", "ERROR")
                    
            conn.commit()
            
            # Enhanced reporting
            total_records = execute_query_one("SELECT COUNT(*) as count FROM series_stats")["count"] if hasattr(self, 'execute_query_one') else len(records_to_update)
            health_score = ((total_records - failed_count) / total_records * 100) if total_records > 0 else 0
            
            if updated_count > 0:
                self.log(f"✅ Updated {updated_count} records with series_id")
            if failed_count > 0:
                self.log(f"⚠️  {failed_count} records still missing series_id (Health Score: {health_score:.1f}%)", "WARNING")
                
                # Log first few failed records for debugging
                if failed_records:
                    self.log("❌ Failed series (first 5):", "WARNING")
                    for i, failed in enumerate(failed_records[:5]):
                        self.log(f"   {i+1}. {failed}", "WARNING")
                    if len(failed_records) > 5:
                        self.log(f"   ... and {len(failed_records) - 5} more", "WARNING")
            
            # CRITICAL: Set error flag if health score is too low
            if health_score < 85:
                self.log(f"🚨 CRITICAL: Series ID health score ({health_score:.1f}%) below acceptable threshold!", "ERROR")
                self.log("🔧 This indicates missing series in the database - manual review required", "ERROR")
                return False
            
            return True
            
        except Exception as e:
            self.log(f"💥 CRITICAL ERROR in auto_populate_series_ids: {str(e)}", "ERROR")
            self.log("🔧 Series ID population failed - manual intervention required", "ERROR")
            return False
            
    def _find_series_id_for_name(self, cursor, series_name, league_id):
        """Find series_id using multiple matching strategies"""
        if not series_name:
            return None
            
        # Strategy 1: Exact match
        cursor.execute("""
            SELECT s.id FROM series s
            JOIN series_leagues sl ON s.id = sl.series_id
            WHERE s.name = %s AND sl.league_id = %s
        """, (series_name, league_id))
        
        result = cursor.fetchone()
        if result:
            return result[0]
            
        # Strategy 2: Case-insensitive match
        cursor.execute("""
            SELECT s.id FROM series s
            JOIN series_leagues sl ON s.id = sl.series_id
            WHERE LOWER(s.name) = LOWER(%s) AND sl.league_id = %s
        """, (series_name, league_id))
        
        result = cursor.fetchone()
        if result:
            return result[0]
            
        # Strategy 3: Format conversion (Series X -> Chicago X)
        if series_name.startswith("Series "):
            converted_name = series_name.replace("Series ", "Chicago ", 1)
            cursor.execute("""
                SELECT s.id FROM series s
                JOIN series_leagues sl ON s.id = sl.series_id
                WHERE s.name = %s AND sl.league_id = %s
            """, (converted_name, league_id))
            
            result = cursor.fetchone()
            if result:
                return result[0]
                
        # Strategy 4: Division format (Division X -> SX)
        if series_name.startswith("Division "):
            number = series_name.replace("Division ", "")
            sx_format = f"S{number}"
            cursor.execute("""
                SELECT s.id FROM series s
                JOIN series_leagues sl ON s.id = sl.series_id
                WHERE s.name = %s AND sl.league_id = %s
            """, (sx_format, league_id))
            
            result = cursor.fetchone()
            if result:
                return result[0]
                
        return None

    def recalculate_missing_team_points(self, conn):
        """Recalculate points only for teams that have zero points (missing data)"""
        self.log("🔧 Recalculating points for teams with missing point data...")

        cursor = conn.cursor()

        # Get only teams with zero points
        cursor.execute("SELECT id, team, league_id FROM series_stats WHERE points = 0")
        teams = cursor.fetchall()

        updated_count = 0

        for team_row in teams:
            team_id = team_row[0]  # id is first column
            team_name = team_row[1]  # team is second column
            league_id = team_row[2]  # league_id is third column

            # Calculate points from match history for missing data only
            cursor.execute(
                """
                SELECT home_team, away_team, winner, scores
                FROM match_scores
                WHERE (home_team = %s OR away_team = %s)
                AND league_id = %s
            """,
                [team_name, team_name, league_id],
            )

            matches = cursor.fetchall()
            total_points = 0

            for match in matches:
                home_team = match[0]  # home_team is first column
                away_team = match[1]  # away_team is second column
                winner = match[2]  # winner is third column
                scores_str = match[3]  # scores is fourth column

                is_home = home_team == team_name
                won_match = (is_home and winner == "home") or (
                    not is_home and winner == "away"
                )

                # 1 point for winning the match
                if won_match:
                    total_points += 1

                # Additional points for sets won (even in losing matches)
                scores = scores_str.split(", ") if scores_str else []
                for score_str in scores:
                    if "-" in score_str:
                        try:
                            # Extract just the numbers before any tiebreak info
                            clean_score = score_str.split("[")[0].strip()
                            our_score, their_score = map(int, clean_score.split("-"))
                            if not is_home:  # Flip scores if we're away team
                                our_score, their_score = their_score, our_score
                            if our_score > their_score:
                                total_points += 1
                        except (ValueError, IndexError):
                            continue

            # Update the points in series_stats
            cursor.execute(
                """
                UPDATE series_stats 
                SET points = %s
                WHERE id = %s
            """,
                [total_points, team_id],
            )

            updated_count += 1

        conn.commit()
        self.log(f"✅ Recalculated points for {updated_count:,} teams with missing data")

    def recalculate_all_team_points(self, conn):
        """Recalculate points for all teams based on actual match performance"""
        self.log("🔧 Recalculating team points from match performance...")

        cursor = conn.cursor()

        # Get all teams in series_stats
        cursor.execute("SELECT id, team, league_id FROM series_stats")
        teams = cursor.fetchall()

        updated_count = 0

        for team_row in teams:
            team_id = team_row[0]  # id is first column
            team_name = team_row[1]  # team is second column
            league_id = team_row[2]  # league_id is third column

            # Calculate correct points from match history
            cursor.execute(
                """
                SELECT home_team, away_team, winner, scores
                FROM match_scores
                WHERE (home_team = %s OR away_team = %s)
                AND league_id = %s
            """,
                [team_name, team_name, league_id],
            )

            matches = cursor.fetchall()
            total_points = 0

            for match in matches:
                home_team = match[0]  # home_team is first column
                away_team = match[1]  # away_team is second column
                winner = match[2]  # winner is third column
                scores_str = match[3]  # scores is fourth column

                is_home = home_team == team_name
                won_match = (is_home and winner == "home") or (
                    not is_home and winner == "away"
                )

                # 1 point for winning the match
                if won_match:
                    total_points += 1

                # Additional points for sets won (even in losing matches)
                scores = scores_str.split(", ") if scores_str else []
                for score_str in scores:
                    if "-" in score_str:
                        try:
                            # Extract just the numbers before any tiebreak info
                            clean_score = score_str.split("[")[0].strip()
                            our_score, their_score = map(int, clean_score.split("-"))
                            if not is_home:  # Flip scores if we're away team
                                our_score, their_score = their_score, our_score
                            if our_score > their_score:
                                total_points += 1
                        except (ValueError, IndexError):
                            continue

            # Update the points in series_stats
            cursor.execute(
                """
                UPDATE series_stats 
                SET points = %s
                WHERE id = %s
            """,
                [total_points, team_id],
            )

            updated_count += 1

        conn.commit()
        self.log(f"✅ Recalculated points for {updated_count:,} teams")

    def calculate_series_stats_from_matches(self, conn):
        """Calculate series stats from match_scores data as fallback
        
        WARNING: This function still uses the flawed point calculation logic
        that gives points for sets won even in losing matches. It should only
        be used when there's severely incomplete data (< 50% coverage).
        """
        self.log("🧮 Calculating series stats from match results...")

        cursor = conn.cursor()

        # Clear existing series_stats data
        cursor.execute("DELETE FROM series_stats")
        self.log("   Cleared existing series_stats data")

        # Get all matches and calculate team statistics
        matches = cursor.execute(
            """
            SELECT home_team, away_team, winner, scores, league_id
            FROM match_scores
            WHERE home_team IS NOT NULL AND away_team IS NOT NULL
        """
        ).fetchall()

        from collections import defaultdict

        team_stats = defaultdict(
            lambda: {
                "matches_won": 0,
                "matches_lost": 0,
                "matches_tied": 0,
                "lines_won": 0,
                "lines_lost": 0,
                "sets_won": 0,
                "sets_lost": 0,
                "games_won": 0,
                "games_lost": 0,
                "points": 0,
                "league_id": None,
                "series": None,
            }
        )

        # Process each match to calculate team stats
        for match in matches:
            home_team = match[0]  # home_team is first column
            away_team = match[1]  # away_team is second column
            winner = match[2]  # winner is third column
            scores = match[3] or ""  # scores is fourth column
            league_id = match[4]  # league_id is fifth column

            # Determine series from team name
            def extract_series_from_team(team_name):
                if not team_name:
                    return "Division 1"
                parts = team_name.split()
                if parts:
                    last_part = parts[-1]
                    if last_part.isdigit():
                        return f"Division {last_part}"
                    elif len(last_part) >= 2 and last_part[:-1].isdigit():
                        return f"Division {last_part[:-1]}"
                return "Division 1"

            # Initialize team data
            if "series" not in team_stats[home_team]:
                team_stats[home_team]["series"] = extract_series_from_team(home_team)
                team_stats[home_team]["league_id"] = league_id
            if "series" not in team_stats[away_team]:
                team_stats[away_team]["series"] = extract_series_from_team(away_team)
                team_stats[away_team]["league_id"] = league_id

            # Parse scores for detailed statistics
            def parse_scores(scores_str, is_home_perspective):
                if not scores_str:
                    return 0, 0, 0, 0
                sets = scores_str.split(", ")
                team_sets = opponent_sets = 0
                team_games = opponent_games = 0

                for set_score in sets:
                    if "-" in set_score:
                        try:
                            score1, score2 = map(int, set_score.split("-"))
                            if is_home_perspective:
                                team_games += score1
                                opponent_games += score2
                                if score1 > score2:
                                    team_sets += 1
                                else:
                                    opponent_sets += 1
                            else:
                                team_games += score2
                                opponent_games += score1
                                if score2 > score1:
                                    team_sets += 1
                                else:
                                    opponent_sets += 1
                        except ValueError:
                            continue

                return team_sets, opponent_sets, team_games, opponent_games

            # Calculate stats for both teams
            home_sets, away_sets, home_games, away_games = parse_scores(scores, True)
            away_sets, home_sets_check, away_games, home_games_check = parse_scores(
                scores, False
            )

            # Determine match winner and update stats
            if winner and winner.lower() == "home":
                team_stats[home_team]["matches_won"] += 1
                team_stats[away_team]["matches_lost"] += 1
                team_stats[home_team]["points"] += 1  # 1 point for match win
            elif winner and winner.lower() == "away":
                team_stats[away_team]["matches_won"] += 1
                team_stats[home_team]["matches_lost"] += 1
                team_stats[away_team]["points"] += 1  # 1 point for match win
            else:
                team_stats[home_team]["matches_tied"] += 1
                team_stats[away_team]["matches_tied"] += 1

            # FIXED: Add points for sets won (even in losing matches)
            team_stats[home_team]["points"] += home_sets  # Points for sets won
            team_stats[away_team]["points"] += away_sets  # Points for sets won

            # Update detailed stats
            team_stats[home_team]["sets_won"] += home_sets
            team_stats[home_team]["sets_lost"] += away_sets
            team_stats[home_team]["games_won"] += home_games
            team_stats[home_team]["games_lost"] += away_games
            team_stats[home_team]["lines_won"] += home_sets
            team_stats[home_team]["lines_lost"] += away_sets

            team_stats[away_team]["sets_won"] += away_sets
            team_stats[away_team]["sets_lost"] += home_sets
            team_stats[away_team]["games_won"] += away_games
            team_stats[away_team]["games_lost"] += home_games
            team_stats[away_team]["lines_won"] += away_sets
            team_stats[away_team]["lines_lost"] += home_sets

        # Insert calculated stats into database
        calculated_count = 0
        for team_name, stats in team_stats.items():
            try:
                # Get series_id for the calculated series
                series_db_id = self._find_series_id_for_name(cursor, stats["series"], stats["league_id"])
                
                cursor.execute(
                    """
                    INSERT INTO series_stats (
                        series, team, series_id, team_id, points, 
                        matches_won, matches_lost, matches_tied,
                        lines_won, lines_lost, lines_for, lines_ret,
                        sets_won, sets_lost, games_won, games_lost,
                        league_id, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (league_id, series, team) DO UPDATE SET
                        points = EXCLUDED.points,
                        matches_won = EXCLUDED.matches_won,
                        matches_lost = EXCLUDED.matches_lost,
                        matches_tied = EXCLUDED.matches_tied,
                        lines_won = EXCLUDED.lines_won,
                        lines_lost = EXCLUDED.lines_lost,
                        lines_for = EXCLUDED.lines_for,
                        lines_ret = EXCLUDED.lines_ret,
                        sets_won = EXCLUDED.sets_won,
                        sets_lost = EXCLUDED.sets_lost,
                        games_won = EXCLUDED.games_won,
                        games_lost = EXCLUDED.games_lost,
                        series_id = EXCLUDED.series_id,
                        team_id = EXCLUDED.team_id,
                        updated_at = CURRENT_TIMESTAMP
                """,
                    [
                        stats["series"],
                        team_name,
                        series_db_id,
                        None,  # team_id - will be populated later if needed
                        stats["points"],
                        stats["matches_won"],
                        stats["matches_lost"],
                        stats["matches_tied"],
                        stats["lines_won"],
                        stats["lines_lost"],
                        stats["lines_for"],
                        stats["lines_ret"],
                        stats["sets_won"],
                        stats["sets_lost"],
                        stats["games_won"],
                        stats["games_lost"],
                        stats["league_id"],
                    ],
                )

                calculated_count += 1

            except Exception as e:
                self.log(
                    f"❌ Error inserting calculated series stats for {team_name}: {str(e)}",
                    "ERROR",
                )

        conn.commit()
        self.log(f"✅ Calculated and inserted {calculated_count:,} series stats records")

        # CRITICAL: Populate series_id values for calculated records
        series_id_success = self.auto_populate_series_ids(conn)
        if not series_id_success:
            self.log("🚨 CRITICAL: Series ID population failed after calculation!", "ERROR")
            self.log("🔧 Calculated series stats may not have proper foreign key relationships", "ERROR")

    def import_schedules(self, conn, schedules_data: List[Dict]):
        """Import schedules data"""
        self.log("📥 Importing schedules...")

        cursor = conn.cursor()
        imported = 0
        errors = 0

        for record in schedules_data:
            try:
                date_str = record.get("date", "").strip()
                time_str = record.get("time", "").strip()
                home_team = record.get("home_team", "").strip()
                away_team = record.get("away_team", "").strip()
                location = record.get("location", "").strip()
                raw_league_id = record.get("League", "").strip()
                league_id = normalize_league_id(raw_league_id) if raw_league_id else ""

                # Parse date
                match_date = None
                if date_str:
                    try:
                        match_date = datetime.strptime(date_str, "%m/%d/%Y").date()
                    except ValueError:
                        try:
                            match_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                        except ValueError:
                            pass

                # Handle empty time fields - convert to None for PostgreSQL TIME column
                match_time = None
                if time_str:
                    match_time = time_str

                if not all([match_date, home_team, away_team]):
                    continue

                # Get league database ID
                cursor.execute(
                    "SELECT id FROM leagues WHERE league_id = %s", (league_id,)
                )
                league_row = cursor.fetchone()
                league_db_id = league_row[0] if league_row else None

                # Get team IDs from teams table with enhanced matching
                home_team_id = None
                away_team_id = None

                def normalize_team_name_for_matching(team_name: str) -> str:
                    """Normalize team name by removing ' - Series X' suffix for matching"""
                    if " - Series " in team_name:
                        return team_name.split(" - Series ")[0]
                    return team_name

                if home_team and home_team != "BYE":
                    # Try exact match first
                    cursor.execute(
                        """
                        SELECT t.id FROM teams t
                        JOIN leagues l ON t.league_id = l.id
                        WHERE l.league_id = %s AND t.team_name = %s
                    """,
                        (league_id, home_team),
                    )
                    home_team_row = cursor.fetchone()
                    
                    if not home_team_row:
                        # Try normalized match (remove " - Series X" suffix)
                        normalized_home_team = normalize_team_name_for_matching(home_team)
                        cursor.execute(
                            """
                            SELECT t.id FROM teams t
                            JOIN leagues l ON t.league_id = l.id
                            WHERE l.league_id = %s AND t.team_name = %s
                        """,
                            (league_id, normalized_home_team),
                        )
                        home_team_row = cursor.fetchone()
                    
                    home_team_id = home_team_row[0] if home_team_row else None

                if away_team and away_team != "BYE":
                    # Try exact match first
                    cursor.execute(
                        """
                        SELECT t.id FROM teams t
                        JOIN leagues l ON t.league_id = l.id
                        WHERE l.league_id = %s AND t.team_name = %s
                    """,
                        (league_id, away_team),
                    )
                    away_team_row = cursor.fetchone()
                    
                    if not away_team_row:
                        # Try normalized match (remove " - Series X" suffix)
                        normalized_away_team = normalize_team_name_for_matching(away_team)
                        cursor.execute(
                            """
                            SELECT t.id FROM teams t
                            JOIN leagues l ON t.league_id = l.id
                            WHERE l.league_id = %s AND t.team_name = %s
                        """,
                            (league_id, normalized_away_team),
                        )
                        away_team_row = cursor.fetchone()
                    
                    away_team_id = away_team_row[0] if away_team_row else None

                cursor.execute(
                    """
                    INSERT INTO schedule (
                        match_date, match_time, home_team, away_team, home_team_id, away_team_id,
                        location, league_id, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """,
                    (
                        match_date,
                        match_time,
                        home_team,
                        away_team,
                        home_team_id,
                        away_team_id,
                        location,
                        league_db_id,
                    ),
                )

                if cursor.rowcount > 0:
                    imported += 1

                if imported % 1000 == 0:
                    self.log(f"   📊 Imported {imported:,} schedule records so far...")
                    self._increment_operation_count(1000)
                    conn.commit()
                    
                    # Check for connection rotation on Railway
                    if self.is_railway and self._should_rotate_connection():
                        self.check_and_rotate_connection_if_needed(conn)

            except Exception as e:
                errors += 1
                if errors <= 10:
                    self.log(f"❌ Error importing schedule record: {str(e)}", "ERROR")

                if errors > 100:
                    self.log(
                        f"❌ Too many schedule errors ({errors}), stopping", "ERROR"
                    )
                    raise Exception(f"Too many schedule import errors ({errors})")

        conn.commit()
        self.imported_counts["schedule"] = imported
        self.log(f"✅ Imported {imported:,} schedule records ({errors} errors)")

    def validate_and_fix_team_hierarchy_relationships(self, conn) -> int:
        """
        Post-import validation to check for and fix any missing team hierarchy relationships.
        This prevents orphaned records by ensuring all club-league and series-league 
        relationships exist for teams that were imported.
        
        Returns:
            int: Number of missing relationships that were fixed
        """
        cursor = conn.cursor()
        total_fixes = 0
        
        # Check for missing club-league relationships
        cursor.execute("""
            SELECT DISTINCT c.id as club_id, c.name as club_name, 
                   l.id as league_id, l.league_name
            FROM teams t
            JOIN clubs c ON t.club_id = c.id
            JOIN leagues l ON t.league_id = l.id
            LEFT JOIN club_leagues cl ON cl.club_id = c.id AND cl.league_id = l.id
            WHERE cl.id IS NULL
        """)
        missing_club_relationships = cursor.fetchall()
        
        if missing_club_relationships:
            self.log(f"   🔧 Found {len(missing_club_relationships)} missing club-league relationships")
            for rel in missing_club_relationships:
                club_id, club_name, league_id, league_name = rel
                cursor.execute("""
                    INSERT INTO club_leagues (club_id, league_id, created_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT ON CONSTRAINT unique_club_league DO NOTHING
                """, [club_id, league_id])
                
                if cursor.rowcount > 0:
                    total_fixes += 1
                    self.log(f"     Added: {club_name} → {league_name}")
        
        # Check for missing series-league relationships
        cursor.execute("""
            SELECT DISTINCT s.id as series_id, s.name as series_name,
                   l.id as league_id, l.league_name
            FROM teams t
            JOIN series s ON t.series_id = s.id
            JOIN leagues l ON t.league_id = l.id
            LEFT JOIN series_leagues sl ON sl.series_id = s.id AND sl.league_id = l.id
            WHERE sl.id IS NULL
        """)
        missing_series_relationships = cursor.fetchall()
        
        if missing_series_relationships:
            self.log(f"   🔧 Found {len(missing_series_relationships)} missing series-league relationships")
            for rel in missing_series_relationships:
                series_id, series_name, league_id, league_name = rel
                cursor.execute("""
                    INSERT INTO series_leagues (series_id, league_id, created_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT ON CONSTRAINT unique_series_league DO NOTHING
                """, [series_id, league_id])
                
                if cursor.rowcount > 0:
                    total_fixes += 1
                    self.log(f"     Added: {series_name} → {league_name}")
        
        conn.commit()
        
        if total_fixes > 0:
            self.log(f"   ✅ Fixed {total_fixes} missing team hierarchy relationships")
        else:
            self.log("   ✅ No missing team hierarchy relationships found")
        
        return total_fixes

    def _validate_final_series_id_health(self, conn) -> float:
        """Validate final series_id health score for the entire ETL process"""
        cursor = conn.cursor()
        
        try:
            # Get total records
            cursor.execute("SELECT COUNT(*) FROM series_stats")
            total_records = cursor.fetchone()[0]
            
            # Get records with series_id
            cursor.execute("SELECT COUNT(*) FROM series_stats WHERE series_id IS NOT NULL")
            with_series_id = cursor.fetchone()[0]
            
            # Calculate health score
            health_score = (with_series_id / total_records * 100) if total_records > 0 else 100
            
            # Log detailed breakdown if health is poor
            if health_score < 85:
                cursor.execute("""
                    SELECT l.league_name, COUNT(*) as null_count
                    FROM series_stats s
                    JOIN leagues l ON s.league_id = l.id
                    WHERE s.series_id IS NULL
                    GROUP BY l.league_name
                    ORDER BY null_count DESC
                """)
                league_breakdown = cursor.fetchall()
                
                self.log("❌ Series_id health breakdown by league:")
                for league_name, null_count in league_breakdown:
                    self.log(f"   {league_name}: {null_count} missing series_id")
            
            return health_score
            
        except Exception as e:
            self.log(f"❌ Error calculating series_id health: {str(e)}", "ERROR")
            return 0.0

    def _validate_poll_references(self, conn) -> int:
        """Validate that all polls have valid team_id references"""
        cursor = conn.cursor()
        
        # Count orphaned poll references
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM polls p
            LEFT JOIN teams t ON p.team_id = t.id
            WHERE p.team_id IS NOT NULL AND t.id IS NULL
        """)
        
        orphaned_count = cursor.fetchone()[0]
        
        if orphaned_count > 0:
            self.log(f"   ⚠️  Found {orphaned_count} polls with orphaned team_id references", "WARNING")
        else:
            self.log(f"   ✅ All polls have valid team_id references")
        
        return orphaned_count

    def _restore_practice_times(self, conn) -> int:
        """Restore practice times after schedule import"""
        cursor = conn.cursor()
        
        # Check if backup exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'practice_times_backup'
            )
        """)
        
        backup_exists = cursor.fetchone()[0]
        
        if not backup_exists:
            self.log("   ⚠️  No practice times backup found")
            return 0
        
        # Restore practice times with updated team_id references
        cursor.execute("""
            INSERT INTO schedule (
                league_id, match_date, match_time, home_team, away_team, 
                home_team_id, location, created_at
            )
            SELECT 
                pt.league_id, pt.match_date, pt.match_time, pt.home_team, pt.away_team,
                t.id as home_team_id, pt.location, pt.created_at
            FROM practice_times_backup pt
            LEFT JOIN teams t ON (
                t.team_name = pt.home_team 
                OR (t.team_alias IS NOT NULL AND t.team_alias = pt.home_team)
            )
            ON CONFLICT DO NOTHING
        """)
        
        restored_count = cursor.rowcount
        
        # Clean up backup
        cursor.execute("DROP TABLE IF EXISTS practice_times_backup")
        
        if restored_count > 0:
            self.log(f"   ✅ Restored {restored_count} practice times")
        else:
            self.log(f"   ℹ️  No practice times restored (may already exist)")
        
        return restored_count

    def _create_pre_etl_backup(self) -> str:
        """Create a full database backup before ETL process"""
        try:
            # Only create backups for production or if explicitly requested
            if self.environment not in ['railway_production', 'railway_staging'] and not os.getenv('FORCE_ETL_BACKUP'):
                self.log("ℹ️  Skipping backup for local environment (set FORCE_ETL_BACKUP=1 to enable)")
                return None
            
            self.log("🔄 Creating pre-ETL database backup...")
            
            # Build path to backup script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
            backup_script = os.path.join(project_root, 'data', 'backup_restore_local_db', 'backup_database.py')
            
            if not os.path.exists(backup_script):
                self.log(f"❌ Backup script not found: {backup_script}", "ERROR")
                return None
            
            # Run backup script with custom format (smaller, faster)
            import subprocess
            
            cmd = [
                'python3', backup_script,
                '--format', 'custom',
                '--max-backups', '5'  # Keep only 5 backups to save space
            ]
            
            self.log(f"Running: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                self.log("✅ Database backup completed successfully")
                
                # Extract backup location from output (check both stdout and stderr)
                backup_path = None
                output_to_check = result.stdout + result.stderr
                
                for line in output_to_check.split('\n'):
                    if 'Backup location:' in line:
                        backup_path = line.split('Backup location:')[1].strip()
                        self.log(f"📁 Backup location: {backup_path}")
                        break
                    elif 'Backup path:' in line:
                        # Alternative format in case logging format changes
                        backup_path = line.split('Backup path:')[1].strip()
                        self.log(f"📁 Backup path: {backup_path}")
                        break
                
                if not backup_path:
                    # Try to extract from any line containing a .dump file path
                    for line in output_to_check.split('\n'):
                        if '.dump' in line and '/rally_db_backup_' in line:
                            # Extract the file path
                            import re
                            match = re.search(r'/[^\s]+rally_db_backup_[^\s]+\.dump', line)
                            if match:
                                backup_path = match.group(0)
                                self.log(f"📁 Extracted backup path: {backup_path}")
                                break
                
                return backup_path
            else:
                self.log(f"❌ Backup script failed: {result.stderr}", "ERROR")
                return None
                
        except subprocess.TimeoutExpired:
            self.log("❌ Backup script timed out after 5 minutes", "ERROR")
            return None
        except Exception as e:
            self.log(f"❌ Error creating backup: {str(e)}", "ERROR")
            return None

    def _restore_from_backup(self, backup_path: str) -> bool:
        """Restore database from backup file"""
        try:
            if not backup_path or not os.path.exists(backup_path):
                self.log(f"❌ Backup file not found: {backup_path}", "ERROR")
                return False
            
            self.log("🔄 Restoring database from backup...")
            self.log(f"📁 Backup: {backup_path}")
            
            # Build path to backup script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
            backup_script = os.path.join(project_root, 'data', 'backup_restore_local_db', 'backup_database.py')
            
            if not os.path.exists(backup_script):
                self.log(f"❌ Backup script not found: {backup_script}", "ERROR")
                return False
            
            # Run restore command with no confirmation (automated)
            import subprocess
            
            cmd = [
                'python3', backup_script,
                '--restore', backup_path,
                '--no-confirm'  # Skip confirmation in automated restore
            ]
            
            self.log(f"Running: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout for restore
            )
            
            if result.returncode == 0:
                self.log("✅ Database restore completed successfully")
                self.log("🔄 Database has been restored to pre-ETL state")
                return True
            else:
                self.log(f"❌ Restore failed: {result.stderr}", "ERROR")
                return False
                
        except subprocess.TimeoutExpired:
            self.log("❌ Restore timed out after 10 minutes", "ERROR")
            return False
        except Exception as e:
            self.log(f"❌ Error during restore: {str(e)}", "ERROR")
            return False

    def _parse_int(self, value: str) -> int:
        """Parse integer with error handling"""
        if not value or value.strip() == "":
            return 0
        try:
            return int(str(value).strip())
        except (ValueError, TypeError):
            return 0

    def print_summary(self):
        """Print import summary"""
        self.log("=" * 60)
        self.log("📊 IMPORT SUMMARY")
        self.log("=" * 60)

        total_imported = 0
        for table, count in self.imported_counts.items():
            self.log(f"   {table:<20}: {count:>10,} records")
            total_imported += count

        self.log("-" * 60)
        self.log(f"   {'TOTAL':<20}: {total_imported:>10,} records")

        if self.errors:
            self.log(f"\n⚠️  {len(self.errors)} errors encountered during import")

    def run(self):
        """Run the complete ETL process"""
        start_time = datetime.now()

        try:
            self.log("🚀 Starting Comprehensive JSON ETL Process")
            self.log("=" * 60)
            
            # CRITICAL: Create full database backup before ETL process
            self.log("\n💾 Step 0: Creating full database backup...")
            backup_path = self._create_pre_etl_backup()
            if not backup_path:
                self.log("⚠️  Backup failed but continuing ETL (backup is optional)", "WARNING")
            else:
                self.log("✅ Database backup completed successfully")
                
            # Enable auto-restore if backup was created and environment allows it
            auto_restore_enabled = (
                backup_path and 
                (self.environment in ['railway_production', 'railway_staging'] or os.getenv('FORCE_ETL_RESTORE'))
            )
            
            if auto_restore_enabled:
                self.log("🛡️  Auto-restore enabled - database will be restored if ETL fails critically")
            elif backup_path:
                self.log("ℹ️  Auto-restore disabled for this environment (set FORCE_ETL_RESTORE=1 to enable)")
            
            # RAILWAY OPTIMIZATION: Log environment and resource information
            if self.is_railway:
                env_display = {
                    'railway_staging': '🟡 Railway Staging Environment Detected',
                    'railway_production': '🔴 Railway Production Environment Detected'
                }.get(self.environment, f'🚂 Railway Environment Detected: {self.environment}')
                self.log(env_display)
                self.log(f"🚂 Railway: Batch size set to {self.batch_size}")
                self.log(f"🚂 Railway: Commit frequency set to {self.commit_frequency}")
                self.log(f"🚂 Railway: Connection retries set to {self.connection_retry_attempts}")
                # Log memory info if available
                try:
                    import psutil
                    memory_info = psutil.virtual_memory()
                    self.log(f"🚂 Railway: Available memory: {memory_info.available / (1024**3):.1f} GB")
                except ImportError:
                    self.log("🚂 Railway: psutil not available for memory monitoring")
                except Exception as e:
                    self.log(f"🚂 Railway: Memory check failed: {e}")
            
            self.log("=" * 60)

            # Step 1: Load all JSON files
            self.log("📂 Step 1: Loading JSON files...")
            players_data = self.load_json_file("players.json")
            player_history_data = self.load_json_file("player_history.json")
            match_history_data = self.load_json_file("match_history.json")
            series_stats_data = self.load_json_file("series_stats.json")
            schedules_data = self.load_json_file("schedules.json")

            # Step 2: Extract reference data from players.json (without mappings first)
            self.log("\n📋 Step 2: Extracting reference data...")
            leagues_data = self.extract_leagues(
                players_data, series_stats_data, schedules_data
            )
            clubs_data = self.extract_clubs(players_data)

            # Step 3: Connect to database for mapping-aware extraction  
            self.log("\n🗄️  Step 3: Connecting to database...")
            if self.is_railway:
                self.log("🚂 Railway: Using managed connection system with rotation")
            
            with self.get_managed_db_connection() as conn:
                try:
                    # Ensure schema requirements
                    self.ensure_schema_requirements(conn)

                    # Clear existing data
                    self.clear_target_tables(conn)

                    # Import basic reference data first
                    self.log("\n📥 Step 4: Importing basic reference data...")
                    self.import_leagues(conn, leagues_data)
                    self.import_clubs(conn, clubs_data)

                    # Now extract series and teams with mapping support
                    self.log("\n📋 Step 5: Extracting mapped data...")
                    series_data = self.extract_series(
                        players_data, series_stats_data, schedules_data, conn
                    )
                    teams_data = self.extract_teams(series_stats_data, schedules_data, conn)
                    
                    # ENHANCEMENT: Pass teams_data to relationship analysis for comprehensive coverage
                    club_league_rels = self.analyze_club_league_relationships(players_data, teams_data)
                    series_league_rels = self.analyze_series_league_relationships(players_data, teams_data)

                    # Import remaining data in dependency order
                    self.log("\n📥 Step 6: Importing remaining data...")
                    self.import_series(conn, series_data)
                    self.import_club_leagues(conn, club_league_rels)
                    self.import_series_leagues(conn, series_league_rels)
                    self.import_teams(conn, teams_data)
                    
                    # Load mappings for player import
                    self.load_series_mappings(conn)
                    self.import_players(conn, players_data)
                    self.import_career_stats(conn, player_history_data)
                    self.import_player_history(conn, player_history_data)
                    self.import_match_history(conn, match_history_data)
                    self.import_series_stats(conn, series_stats_data)
                    self.import_schedules(conn, schedules_data)

                    # ENHANCEMENT: Create missing teams from schedule data
                    self.log("\n🔧 Step 6.5: Creating missing teams from schedule data...")
                    missing_teams_created = self.create_missing_teams_from_schedule(conn)
                    if missing_teams_created > 0:
                        self.log(f"   ✅ Created {missing_teams_created} missing teams from schedule data")

                    # ENHANCEMENT: Restore user data with team ID preservation after import
                    self.log("\n🔄 Step 7: Restoring user data with team ID preservation...")
                    restore_results = self.restore_user_data_with_team_mappings(conn)
                    
                    # ENHANCED: Run comprehensive association discovery for all users
                    # This ensures users with multiple leagues are properly linked
                    self.log("🔍 Running comprehensive association discovery...")
                    try:
                        from app.services.association_discovery_service import AssociationDiscoveryService
                        
                        # PRODUCTION FIX: Limit discovery to prevent timeout and excessive logging
                        # Only process users most likely to benefit from discovery
                        discovery_limit = 50 if self.environment in ['railway_production', 'railway_staging'] else 100
                        
                        self.log(f"   🎯 Processing up to {discovery_limit} users for association discovery...")
                        discovery_result = AssociationDiscoveryService.discover_for_all_users(limit=discovery_limit)
                        
                        if discovery_result.get("total_associations_created", 0) > 0:
                            self.log(f"   ✅ Discovery found {discovery_result['total_associations_created']} additional associations")
                            
                            # Re-run league context fixing after new associations are found
                            self.log("🔧 Re-running league context fixes after discovery...")
                            additional_fixes = self._auto_fix_null_league_contexts(conn)
                            if additional_fixes > 0:
                                self.log(f"   ✅ Fixed {additional_fixes} additional league contexts")
                        else:
                            self.log("   ℹ️  No additional associations needed")
                        
                        # Log summary stats instead of individual failures
                        users_processed = discovery_result.get("users_processed", 0)
                        users_with_new = discovery_result.get("users_with_new_associations", 0)
                        error_count = len(discovery_result.get("errors", []))
                        
                        self.log(f"   📊 Discovery summary: {users_with_new}/{users_processed} users gained associations")
                        if error_count > 0:
                            self.log(f"   ⚠️  {error_count} users could not be matched (likely incomplete registration data)")
                        
                        # ENHANCEMENT: Validate multi-league users have proper league selectors
                        self._validate_multi_league_contexts(conn)
                        
                    except Exception as discovery_error:
                        self.log(f"   ⚠️  Association discovery failed: {discovery_error}", "WARNING")
                        self.log("   ℹ️  ETL will continue - association discovery can be run separately later", "INFO")

                    # Auto-run final league context health check
                    self.log("🔧 Running final league context health check...")
                    final_health_score = self._check_final_league_context_health(conn)
                    if final_health_score < 95:
                        self.log(f"⚠️  League context health score: {final_health_score:.1f}% - may need manual repair", "WARNING")
                    else:
                        self.log(f"✅ League context health score: {final_health_score:.1f}%")

                    # User data restoration is now handled by the comprehensive restore system
                    # No additional orphan fixing needed - everything is handled in restore_user_data_with_team_mappings

                    # CRITICAL FIX: Print player validation summary
                    self.player_validator.print_validation_summary()

                    # ENHANCEMENT: Post-import validation and orphan prevention
                    self.log("\n🔍 Step 8: Post-import validation and orphan prevention...")
                    orphan_fixes = self.validate_and_fix_team_hierarchy_relationships(conn)
                    
                    # CRITICAL: Validate and fix schedule team mappings
                    self.log("\n🔍 Step 8.5: Validating schedule team mappings...")
                    schedule_fixes = self.validate_and_fix_schedule_team_mappings(conn)
                    
                    # CRITICAL: Final series_id health check
                    self.log("\n🔍 Step 9: Final series_id health validation...")
                    final_series_health = self._validate_final_series_id_health(conn)
                    if final_series_health < 85:
                        self.log(f"🚨 CRITICAL: Final series_id health score ({final_series_health:.1f}%) is below 85%!", "ERROR")
                        self.log("🔧 This will cause 'No Series Data' issues in production", "ERROR")
                        self.log("⚠️  Manual series creation may be required", "WARNING")
                    else:
                        self.log(f"✅ Series_id health score: {final_series_health:.1f}% - Excellent!")

                    # CRITICAL: Increment session version to trigger user session refresh
                    self.increment_session_version(conn)

                    # Success!
                    self.log("\n✅ ETL process completed successfully!")
                    self.log(f"📊 Polls: {restore_results['polls_restored']:,} restored with team ID preservation")
                    self.log(f"💬 Captain messages: {restore_results['captain_messages_restored']:,} restored with team ID preservation")
                    self.log(f"⏰ Practice times: {restore_results['practice_times_restored']:,} restored with team ID preservation")
                    self.log(f"🎯 League contexts: {restore_results['contexts_restored']:,} restored, {restore_results['null_contexts_fixed']:,} auto-fixed")
                    if orphan_fixes > 0:
                        self.log(f"🔧 Relationship gaps fixed: {orphan_fixes} missing relationships added")
                    if missing_teams_created > 0:
                        self.log(f"🏆 Missing teams created: {missing_teams_created} teams from schedule data")
                    if schedule_fixes > 0:
                        self.log(f"📅 Schedule team mappings fixed: {schedule_fixes} entries corrected")
                    self.log(f"📊 Series_id health: {final_series_health:.1f}% ({'✅ Excellent' if final_series_health >= 95 else '⚠️ Needs attention' if final_series_health >= 85 else '🚨 Critical'})")
                    
                    # Final validation is now handled by the simple restore system
                    # Validation results are included in restore_results['validation_results']
                    
                    self.log("🎯 League selector and Find Subs functionality: ✅ Ready")
                    self.log("🔄 Session version incremented: ✅ Users will auto-refresh")

                except Exception as e:
                    self.log(f"\n❌ ETL process failed: {str(e)}", "ERROR")
                    self.log("🔄 Rolling back all changes...", "WARNING")
                    conn.rollback()
                    
                    # CRITICAL: Attempt automatic restore if enabled
                    if auto_restore_enabled and backup_path:
                        self.log("\n🚨 CRITICAL FAILURE - Attempting automatic database restore...")
                        restore_success = self._restore_from_backup(backup_path)
                        
                        if restore_success:
                            self.log("✅ Database successfully restored to pre-ETL state")
                            self.log("💡 You can safely retry the ETL process")
                        else:
                            self.log("❌ Automatic restore failed!", "ERROR")
                            self.log(f"🔧 Manual restore required: python3 data/backup_restore_local_db/backup_database.py --restore {backup_path}", "ERROR")
                    elif backup_path:
                        self.log(f"\n💡 ETL failed but backup available for manual restore:", "WARNING")
                        self.log(f"🔧 Run: python3 data/backup_restore_local_db/backup_database.py --restore {backup_path}", "WARNING")
                    
                    raise

        except Exception as e:
            self.log(f"\n💥 CRITICAL ERROR: {str(e)}", "ERROR")
            self.log(f"Traceback: {traceback.format_exc()}", "ERROR")
            
            # CRITICAL: Attempt automatic restore if ETL failed and restore is enabled
            if 'auto_restore_enabled' in locals() and locals()['auto_restore_enabled'] and 'backup_path' in locals() and locals()['backup_path']:
                self.log("\n🚨 CATASTROPHIC FAILURE - Attempting automatic database restore...")
                restore_success = self._restore_from_backup(locals()['backup_path'])
                
                if restore_success:
                    self.log("✅ Database successfully restored to pre-ETL state")
                    self.log("💡 You can safely retry the ETL process")
                else:
                    self.log("❌ Automatic restore failed!", "ERROR")
                    self.log(f"🔧 Manual restore required: python3 data/backup_restore_local_db/backup_database.py --restore {locals()['backup_path']}", "ERROR")
            elif 'backup_path' in locals() and locals()['backup_path']:
                self.log(f"\n💡 ETL failed but backup available for manual restore:", "WARNING")
                self.log(f"🔧 Run: python3 data/backup_restore_local_db/backup_database.py --restore {locals()['backup_path']}", "WARNING")
            
            return False

        finally:
            end_time = datetime.now()
            duration = end_time - start_time

            self.log(f"\n⏱️  Total execution time: {duration}")
            self.print_summary()

        return True

    def validate_and_fix_schedule_team_mappings(self, conn) -> int:
        """
        Post-import validation to check for and fix any schedule entries with NULL team_ids.
        This prevents the issue where team names with " - Series X" suffixes don't match
        team names in the teams table.
        
        Note: This primarily fixes NSTF league issues. Other leagues (CITA, CNSWPL) may have
        fundamental data mismatches between schedule and teams data that require manual intervention.
        
        Returns:
            int: Number of schedule entries that were fixed
        """
        cursor = conn.cursor()
        total_fixes = 0
        
        # Check for schedule entries with NULL team_ids
        cursor.execute("""
            SELECT COUNT(*) as null_count
            FROM schedule 
            WHERE (home_team_id IS NULL OR away_team_id IS NULL)
        """)
        null_count = cursor.fetchone()[0]
        
        if null_count == 0:
            self.log("   ✅ All schedule entries have valid team mappings")
            return 0
        
        self.log(f"   🔧 Found {null_count} schedule entries with NULL team_ids - fixing...")
        
        def normalize_team_name_for_matching(team_name: str) -> str:
            """Normalize team name by removing ' - Series X' suffix for matching"""
            if " - Series " in team_name:
                return team_name.split(" - Series ")[0]
            return team_name
        
        # Fix home team mappings
        cursor.execute("""
            SELECT DISTINCT s.id, s.home_team, s.league_id, l.league_id as league_code
            FROM schedule s
            JOIN leagues l ON s.league_id = l.id
            WHERE s.home_team_id IS NULL AND s.home_team != 'BYE'
        """)
        home_team_fixes = cursor.fetchall()
        
        for schedule_id, team_name, league_db_id, league_code in home_team_fixes:
            # Try exact match first
            cursor.execute("""
                SELECT t.id FROM teams t
                WHERE t.league_id = %s AND t.team_name = %s
            """, (league_db_id, team_name))
            team_row = cursor.fetchone()
            
            if not team_row:
                # Try normalized match (remove " - Series X" suffix)
                normalized_team_name = normalize_team_name_for_matching(team_name)
                cursor.execute("""
                    SELECT t.id FROM teams t
                    WHERE t.league_id = %s AND t.team_name = %s
                """, (league_db_id, normalized_team_name))
                team_row = cursor.fetchone()
            
            if team_row:
                cursor.execute("""
                    UPDATE schedule SET home_team_id = %s WHERE id = %s
                """, (team_row[0], schedule_id))
                total_fixes += 1
                self.log(f"     Fixed home team: {team_name} → team_id {team_row[0]}")
        
        # Fix away team mappings
        cursor.execute("""
            SELECT DISTINCT s.id, s.away_team, s.league_id, l.league_id as league_code
            FROM schedule s
            JOIN leagues l ON s.league_id = l.id
            WHERE s.away_team_id IS NULL AND s.away_team != 'BYE'
        """)
        away_team_fixes = cursor.fetchall()
        
        for schedule_id, team_name, league_db_id, league_code in away_team_fixes:
            # Try exact match first
            cursor.execute("""
                SELECT t.id FROM teams t
                WHERE t.league_id = %s AND t.team_name = %s
            """, (league_db_id, team_name))
            team_row = cursor.fetchone()
            
            if not team_row:
                # Try normalized match (remove " - Series X" suffix)
                normalized_team_name = normalize_team_name_for_matching(team_name)
                cursor.execute("""
                    SELECT t.id FROM teams t
                    WHERE t.league_id = %s AND t.team_name = %s
                """, (league_db_id, normalized_team_name))
                team_row = cursor.fetchone()
            
            if team_row:
                cursor.execute("""
                    UPDATE schedule SET away_team_id = %s WHERE id = %s
                """, (team_row[0], schedule_id))
                total_fixes += 1
                self.log(f"     Fixed away team: {team_name} → team_id {team_row[0]}")
        
        # Check final status by league
        cursor.execute("""
            SELECT l.league_name, COUNT(*) as remaining_null_count
            FROM schedule s
            JOIN leagues l ON s.league_id = l.id
            WHERE (s.home_team_id IS NULL OR s.away_team_id IS NULL)
            GROUP BY l.league_name
            ORDER BY remaining_null_count DESC
        """)
        remaining_by_league = cursor.fetchall()
        
        total_remaining = sum(count for _, count in remaining_by_league)
        
        if total_remaining > 0:
            self.log(f"   ⚠️  {total_remaining} schedule entries still have NULL team_ids after fixes", "WARNING")
            self.log("   📊 Breakdown by league:")
            for league_name, count in remaining_by_league:
                self.log(f"      {league_name}: {count:,} entries")
            
            # Provide guidance for manual intervention
            if any('CITA' in league_name or 'CNSWPL' in league_name for league_name, _ in remaining_by_league):
                self.log("   💡 Note: CITA and CNSWPL leagues have fundamental data mismatches", "INFO")
                self.log("      between schedule and teams data that require manual intervention", "INFO")
        else:
            self.log(f"   ✅ All schedule team mappings fixed successfully")
        
        return total_fixes

    def create_missing_teams_from_schedule(self, conn) -> int:
        """
        Create missing teams from schedule data to ensure all teams referenced in schedules
        exist in the teams table. This prevents the issue where schedule entries have NULL team_ids
        because the referenced teams don't exist in the teams table.
        
        Returns:
            int: Number of teams that were created
        """
        cursor = conn.cursor()
        teams_created = 0
        
        self.log("   🔧 Creating missing teams from schedule data...")
        
        # Get all unique team names from schedule that don't exist in teams table
        cursor.execute("""
            SELECT DISTINCT 
                s.home_team as team_name,
                s.league_id,
                l.league_id as league_code
            FROM schedule s
            JOIN leagues l ON s.league_id = l.id
            WHERE s.home_team != 'BYE'
            AND NOT EXISTS (
                SELECT 1 FROM teams t 
                WHERE t.team_name = s.home_team 
                AND t.league_id = s.league_id
            )
            
            UNION
            
            SELECT DISTINCT 
                s.away_team as team_name,
                s.league_id,
                l.league_id as league_code
            FROM schedule s
            JOIN leagues l ON s.league_id = l.id
            WHERE s.away_team != 'BYE'
            AND NOT EXISTS (
                SELECT 1 FROM teams t 
                WHERE t.team_name = s.away_team 
                AND t.league_id = s.league_id
            )
        """)
        
        missing_teams = cursor.fetchall()
        
        if not missing_teams:
            self.log("   ✅ All teams from schedule already exist in teams table")
            return 0
        
        self.log(f"   📊 Found {len(missing_teams)} missing teams to create")
        
        for team_name, league_db_id, league_code in missing_teams:
            try:
                # Parse team name to extract club and series
                club_name, series_name = self.parse_schedule_team_name(team_name)
                
                if not club_name or not series_name:
                    self.log(f"     ⚠️  Could not parse team name: {team_name}")
                    continue
                
                # Get club_id
                cursor.execute("""
                    SELECT id FROM clubs WHERE name = %s
                """, (club_name,))
                club_result = cursor.fetchone()
                
                if not club_result:
                    self.log(f"     ⚠️  Club not found: {club_name}")
                    continue
                
                club_id = club_result[0]
                
                # Get series_id
                cursor.execute("""
                    SELECT id FROM series WHERE name = %s
                """, (series_name,))
                series_result = cursor.fetchone()
                
                if not series_result:
                    self.log(f"     ⚠️  Series not found: {series_name}")
                    continue
                
                series_id = series_result[0]
                
                # Create the team
                cursor.execute("""
                    INSERT INTO teams (team_name, club_id, series_id, league_id, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, NOW(), NOW())
                """, (team_name, club_id, series_id, league_db_id))
                
                teams_created += 1
                
                if teams_created % 10 == 0:
                    self.log(f"     ✅ Created {teams_created} teams...")
                
            except Exception as e:
                self.log(f"     ❌ Error creating team {team_name}: {str(e)}")
                continue
        
        if teams_created > 0:
            self.log(f"   ✅ Created {teams_created} missing teams from schedule data")
        else:
            self.log("   ⚠️  No teams were created (parsing issues)")
        
        return teams_created

    def _fix_restored_team_id_mappings(self, conn):
        """Fix team ID mappings for restored polls and captain messages"""
        cursor = conn.cursor()
        
        # Check if team_mapping_backup table exists and has data
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_name = 'team_mapping_backup'
        """)
        table_exists = cursor.fetchone()[0] > 0
        
        if not table_exists:
            self.log("   ⚠️  team_mapping_backup table not found - skipping team ID mapping fix")
            return
        
        # Get team mapping backup data
        cursor.execute("""
            SELECT 
                old_team_id,
                old_team_name,
                old_team_alias,
                old_league_string_id,
                old_club_id,
                old_series_id
            FROM team_mapping_backup
        """)
        mappings = cursor.fetchall()
        
        if not mappings:
            self.log("   ⚠️  No team mapping data found in backup - skipping team ID mapping fix")
            return
        
        self.log(f"   🔧 Processing {len(mappings)} team mappings for restoration...")
        
        # Create mapping dictionary
        team_id_mapping = {}
        for mapping in mappings:
            old_team_id, old_team_name, old_team_alias, old_league_string_id, old_club_id, old_series_id = mapping
            
            # Find new team ID based on context
            cursor.execute("""
                SELECT t.id 
                FROM teams t
                JOIN leagues l ON t.league_id = l.id
                WHERE l.league_id = %s 
                AND t.club_id = %s 
                AND t.series_id = %s
                AND (t.team_name = %s OR t.team_alias = %s)
            """, (old_league_string_id, old_club_id, old_series_id, old_team_name, old_team_alias))
            
            new_team = cursor.fetchone()
            if new_team:
                team_id_mapping[old_team_id] = new_team[0]
        
        # Handle missing teams with fallback mappings
        # Map Tennaqua Series 22 to Tennaqua Series 22 (teams with users)
        cursor.execute("""
            SELECT t.id 
            FROM teams t
            JOIN leagues l ON t.league_id = l.id
            WHERE l.league_id = 'APTA_CHICAGO' 
            AND t.team_name LIKE 'Tennaqua - 22'
            LIMIT 1
        """)
        tennaqua_22 = cursor.fetchone()
        if tennaqua_22:
            team_id_mapping[67600] = tennaqua_22[0]  # Tennaqua - 22
            team_id_mapping[67854] = tennaqua_22[0]  # Test Chicago 22 @ Tennaqua
        
        # Map Tennaqua S2B to Tennaqua S2B (teams with users)
        cursor.execute("""
            SELECT t.id 
            FROM teams t
            JOIN leagues l ON t.league_id = l.id
            WHERE l.league_id = 'NSTF' 
            AND t.team_name LIKE 'Tennaqua S2B'
            LIMIT 1
        """)
        tennaqua_s2b = cursor.fetchone()
        if tennaqua_s2b:
            team_id_mapping[67620] = tennaqua_s2b[0]  # Tennaqua S2B
            team_id_mapping[67855] = tennaqua_s2b[0]  # Test Series 2B @ Tennaqua
        
        # Fix polls
        polls_fixed = 0
        try:
            cursor.execute("SELECT id, team_id FROM polls WHERE team_id IS NOT NULL")
            polls = cursor.fetchall()
            for poll_id, old_team_id in polls:
                if old_team_id in team_id_mapping:
                    new_team_id = team_id_mapping[old_team_id]
                    cursor.execute("UPDATE polls SET team_id = %s WHERE id = %s", (new_team_id, poll_id))
                    polls_fixed += 1
        except Exception as e:
            self.log(f"   ⚠️  Error fixing polls: {e}")
        
        # Fix captain messages
        messages_fixed = 0
        try:
            cursor.execute("SELECT id, team_id FROM captain_messages WHERE team_id IS NOT NULL")
            messages = cursor.fetchall()
            for msg_id, old_team_id in messages:
                if old_team_id in team_id_mapping:
                    new_team_id = team_id_mapping[old_team_id]
                    cursor.execute("UPDATE captain_messages SET team_id = %s WHERE id = %s", (new_team_id, msg_id))
                    messages_fixed += 1
        except Exception as e:
            self.log(f"   ⚠️  Error fixing captain messages: {e}")
        
        self.log(f"   🔧 Fixed {polls_fixed} polls and {messages_fixed} captain messages")

    def _validate_user_data_restoration(self, conn):
        """
        Comprehensive validation of user data restoration.
        
        Returns a dictionary with validation results for all data types.
        """
        self.log("🔍 Validating user data restoration...")
        
        cursor = conn.cursor()
        validation_results = {}
        
        # Validate polls
        cursor.execute("""
            SELECT COUNT(*) as total_polls,
                   COUNT(CASE WHEN team_id IS NOT NULL THEN 1 END) as polls_with_team,
                   COUNT(CASE WHEN team_id IS NULL THEN 1 END) as polls_without_team
            FROM polls
        """)
        
        poll_stats = cursor.fetchone()
        validation_results['polls'] = {
            'total': poll_stats[0],
            'with_team': poll_stats[1],
            'without_team': poll_stats[2],
            'orphaned': 0
        }
        
        # Check for orphaned poll references
        cursor.execute("""
            SELECT COUNT(*) 
            FROM polls p 
            LEFT JOIN teams t ON p.team_id = t.id 
            WHERE p.team_id IS NOT NULL AND t.id IS NULL
        """)
        
        orphaned_polls = cursor.fetchone()[0]
        validation_results['polls']['orphaned'] = orphaned_polls
        
        # Validate captain messages
        cursor.execute("""
            SELECT COUNT(*) as total_messages,
                   COUNT(CASE WHEN team_id IS NOT NULL THEN 1 END) as messages_with_team,
                   COUNT(CASE WHEN team_id IS NULL THEN 1 END) as messages_without_team
            FROM captain_messages
        """)
        
        message_stats = cursor.fetchone()
        validation_results['captain_messages'] = {
            'total': message_stats[0],
            'with_team': message_stats[1],
            'without_team': message_stats[2],
            'orphaned': 0
        }
        
        # Check for orphaned captain message references
        cursor.execute("""
            SELECT COUNT(*) 
            FROM captain_messages cm 
            LEFT JOIN teams t ON cm.team_id = t.id 
            WHERE cm.team_id IS NOT NULL AND t.id IS NULL
        """)
        
        orphaned_messages = cursor.fetchone()[0]
        validation_results['captain_messages']['orphaned'] = orphaned_messages
        
        # Validate practice times
        cursor.execute("""
            SELECT COUNT(*) as total_practice_times
            FROM schedule 
            WHERE home_team LIKE '%Practice%' OR home_team LIKE '%practice%'
        """)
        
        practice_times_count = cursor.fetchone()[0]
        validation_results['practice_times'] = {
            'total': practice_times_count
        }
        
        # Validate user associations
        cursor.execute("SELECT COUNT(*) FROM user_player_associations")
        associations_count = cursor.fetchone()[0]
        validation_results['user_associations'] = {
            'total': associations_count
        }
        
        # Validate availability data
        cursor.execute("SELECT COUNT(*) FROM player_availability")
        availability_count = cursor.fetchone()[0]
        validation_results['availability'] = {
            'total': availability_count
        }
        
        # Log validation results
        self.log("📊 Validation Results:")
        self.log(f"   📊 Polls: {validation_results['polls']['total']} total, {validation_results['polls']['with_team']} with team, {validation_results['polls']['orphaned']} orphaned")
        self.log(f"   💬 Captain Messages: {validation_results['captain_messages']['total']} total, {validation_results['captain_messages']['with_team']} with team, {validation_results['captain_messages']['orphaned']} orphaned")
        self.log(f"   ⏰ Practice Times: {validation_results['practice_times']['total']} total")
        self.log(f"   👥 User Associations: {validation_results['user_associations']['total']} total")
        self.log(f"   📅 Availability: {validation_results['availability']['total']} total")
        
        # Check for critical issues
        total_orphaned = validation_results['polls']['orphaned'] + validation_results['captain_messages']['orphaned']
        
        if total_orphaned > 0:
            self.log(f"⚠️  WARNING: {total_orphaned} orphaned references found", "WARNING")
            validation_results['has_issues'] = True
        else:
            self.log("✅ No orphaned references found - all data properly restored")
            validation_results['has_issues'] = False
        
        return validation_results


def main():
    """Main entry point"""
    etl = ComprehensiveETL()
    success = etl.run()

    if success:
        print("\n🎉 ETL process completed successfully!")
        return 0
    else:
        print("\n💥 ETL process failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
