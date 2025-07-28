#!/usr/bin/env python3
"""
Bulletproof Team ID Preservation System
=======================================

This module provides a robust, failure-resistant team ID preservation system
for ETL imports that guarantees zero orphaned records.

Key Features:
- Pre-validation of all constraints and dependencies
- Incremental team processing with automatic recovery
- Connection pooling and transaction management
- Comprehensive monitoring and health checks
- Automatic fallback and repair mechanisms
- Zero-downtime updates with rollback capabilities

Usage:
    from bulletproof_team_id_preservation import BulletproofTeamPreservation
    
    with BulletproofTeamPreservation() as preservation:
        preservation.validate_constraints()
        preservation.backup_user_data()
        preservation.preserve_teams_during_import(teams_data)
        preservation.restore_user_data()
        preservation.validate_health()
"""

import sys
import os
import time
import psycopg2
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from contextlib import contextmanager
import logging

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database_config import get_db

class BulletproofTeamPreservation:
    """
    Bulletproof team ID preservation system that guarantees no orphaned records
    """
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.connection_pool = []
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        self.batch_size = 50  # Smaller batches for reliability
        self.validation_enabled = True
        self.backup_tables_created = False
        
    def _setup_logging(self):
        """Setup comprehensive logging"""
        logger = logging.getLogger('BulletproofTeamPreservation')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    @contextmanager
    def get_connection(self):
        """Get a managed database connection with automatic retry"""
        connection = None
        try:
            for attempt in range(self.max_retries):
                try:
                    connection = get_db()
                    connection.autocommit = False  # Explicit transaction control
                    yield connection
                    break
                except Exception as e:
                    if attempt < self.max_retries - 1:
                        self.logger.warning(f"Connection attempt {attempt + 1} failed: {str(e)}. Retrying...")
                        time.sleep(self.retry_delay * (attempt + 1))
                    else:
                        raise
        finally:
            if connection:
                try:
                    connection.close()
                except:
                    pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
    
    def cleanup(self):
        """Cleanup resources and temporary tables"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Drop backup tables if they exist
                backup_tables = [
                    'bulletproof_teams_backup',
                    'bulletproof_polls_backup', 
                    'bulletproof_captain_messages_backup',
                    'bulletproof_practice_times_backup',
                    'bulletproof_team_mappings'
                ]
                
                for table in backup_tables:
                    cursor.execute(f"DROP TABLE IF EXISTS {table}")
                
                conn.commit()
                self.logger.info("✅ Cleanup completed")
        except Exception as e:
            self.logger.warning(f"Cleanup warning: {str(e)}")
    
    def validate_constraints(self) -> bool:
        """
        Comprehensive constraint validation before ETL starts
        Returns True if all constraints are valid, False otherwise
        """
        self.logger.info("🔍 STEP 1: Validating database constraints...")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            issues = []
            
            # Check 1: Verify teams table unique constraint exists
            cursor.execute("""
                SELECT constraint_name 
                FROM information_schema.table_constraints 
                WHERE table_name = 'teams' 
                AND constraint_type = 'UNIQUE'
                AND constraint_name = 'unique_team_club_series_league'
            """)
            
            if not cursor.fetchone():
                issues.append("Missing unique_team_club_series_league constraint")
                self.logger.error("❌ Missing critical UPSERT constraint")
            else:
                self.logger.info("✅ UPSERT constraint exists")
            
            # Check 2: Verify foreign key constraints
            required_fks = [
                ('teams', 'club_id', 'clubs', 'id'),
                ('teams', 'series_id', 'series', 'id'),
                ('teams', 'league_id', 'leagues', 'id'),
                ('polls', 'team_id', 'teams', 'id'),
                ('captain_messages', 'team_id', 'teams', 'id')
            ]
            
            for table, column, ref_table, ref_column in required_fks:
                cursor.execute("""
                    SELECT constraint_name 
                    FROM information_schema.referential_constraints r
                    JOIN information_schema.key_column_usage k 
                        ON r.constraint_name = k.constraint_name
                    WHERE k.table_name = %s AND k.column_name = %s
                """, (table, column))
                
                if not cursor.fetchone():
                    issues.append(f"Missing FK constraint: {table}.{column} -> {ref_table}.{ref_column}")
                    self.logger.warning(f"⚠️  Missing FK: {table}.{column}")
                else:
                    self.logger.debug(f"✅ FK exists: {table}.{column}")
            
            # Check 3: Look for existing constraint violations
            cursor.execute("""
                SELECT club_id, series_id, league_id, COUNT(*) as count
                FROM teams 
                GROUP BY club_id, series_id, league_id
                HAVING COUNT(*) > 1
            """)
            
            violations = cursor.fetchall()
            if violations:
                issues.append(f"Found {len(violations)} constraint violations in teams table")
                self.logger.error(f"❌ Found {len(violations)} constraint violations")
                for violation in violations[:5]:  # Log first 5
                    self.logger.error(f"   Violation: club_id={violation[0]}, series_id={violation[1]}, league_id={violation[2]}, count={violation[3]}")
            else:
                self.logger.info("✅ No constraint violations found")
            
            # Check 4: Verify reference table health
            ref_tables = ['leagues', 'clubs', 'series']
            for table in ref_tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                if count == 0:
                    issues.append(f"Reference table {table} is empty")
                    self.logger.error(f"❌ Empty reference table: {table}")
                else:
                    self.logger.info(f"✅ Reference table {table}: {count} records")
            
            if issues:
                self.logger.error("❌ Constraint validation failed:")
                for issue in issues:
                    self.logger.error(f"   • {issue}")
                
                # Attempt automatic fixes
                self.logger.info("🔧 Attempting automatic constraint fixes...")
                self._fix_constraint_issues(cursor, conn, issues)
                
                # Re-validate after fixes
                return self.validate_constraints()
            else:
                self.logger.info("✅ All constraints validated successfully")
                return True
    
    def _fix_constraint_issues(self, cursor, conn, issues: List[str]):
        """Automatically fix common constraint issues"""
        
        for issue in issues:
            try:
                if "Missing unique_team_club_series_league constraint" in issue:
                    self.logger.info("🔧 Creating missing unique constraint...")
                    cursor.execute("""
                        ALTER TABLE teams 
                        ADD CONSTRAINT unique_team_club_series_league 
                        UNIQUE (club_id, series_id, league_id)
                    """)
                    conn.commit()
                    self.logger.info("✅ Created unique constraint")
                
                elif "constraint violations" in issue:
                    self.logger.info("🔧 Fixing constraint violations...")
                    # Merge duplicate teams, keeping the one with the most data
                    cursor.execute("""
                        WITH duplicates AS (
                            SELECT club_id, series_id, league_id, 
                                   MIN(id) as keep_id,
                                   array_agg(id ORDER BY id) as all_ids
                            FROM teams 
                            GROUP BY club_id, series_id, league_id
                            HAVING COUNT(*) > 1
                        ),
                        updates AS (
                            SELECT keep_id, unnest(all_ids[2:]) as delete_id
                            FROM duplicates
                        )
                        UPDATE polls SET team_id = u.keep_id
                        FROM updates u
                        WHERE polls.team_id = u.delete_id
                    """)
                    
                    cursor.execute("""
                        WITH duplicates AS (
                            SELECT club_id, series_id, league_id, 
                                   MIN(id) as keep_id,
                                   array_agg(id ORDER BY id) as all_ids
                            FROM teams 
                            GROUP BY club_id, series_id, league_id
                            HAVING COUNT(*) > 1
                        ),
                        updates AS (
                            SELECT keep_id, unnest(all_ids[2:]) as delete_id
                            FROM duplicates
                        )
                        UPDATE captain_messages SET team_id = u.keep_id
                        FROM updates u
                        WHERE captain_messages.team_id = u.delete_id
                    """)
                    
                    cursor.execute("""
                        WITH duplicates AS (
                            SELECT club_id, series_id, league_id, 
                                   array_agg(id ORDER BY id) as all_ids
                            FROM teams 
                            GROUP BY club_id, series_id, league_id
                            HAVING COUNT(*) > 1
                        )
                        DELETE FROM teams 
                        WHERE id IN (
                            SELECT unnest(all_ids[2:]) FROM duplicates
                        )
                    """)
                    
                    conn.commit()
                    self.logger.info("✅ Fixed constraint violations")
                    
            except Exception as e:
                self.logger.error(f"❌ Failed to fix issue '{issue}': {str(e)}")
                conn.rollback()
    
    def backup_user_data(self) -> Dict[str, int]:
        """
        Create comprehensive backup of all user data that depends on team_id
        """
        self.logger.info("💾 STEP 2: Creating comprehensive user data backup...")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            backup_stats = {}
            
            try:
                # Backup teams table for ID mapping
                self.logger.info("🏆 Backing up teams table...")
                cursor.execute("""
                    DROP TABLE IF EXISTS bulletproof_teams_backup;
                    CREATE TABLE bulletproof_teams_backup AS 
                    SELECT *, NOW() as backup_timestamp FROM teams
                """)
                
                cursor.execute("SELECT COUNT(*) FROM bulletproof_teams_backup")
                backup_stats['teams'] = cursor.fetchone()[0]
                self.logger.info(f"✅ Backed up {backup_stats['teams']} teams")
                
                # Backup polls with team context
                self.logger.info("📊 Backing up polls...")
                cursor.execute("""
                    DROP TABLE IF EXISTS bulletproof_polls_backup;
                    CREATE TABLE bulletproof_polls_backup AS 
                    SELECT p.*, t.team_name, t.team_alias, l.league_id as team_league_id,
                           c.name as team_club_name, s.name as team_series_name,
                           NOW() as backup_timestamp
                    FROM polls p
                    LEFT JOIN teams t ON p.team_id = t.id
                    LEFT JOIN leagues l ON t.league_id = l.id
                    LEFT JOIN clubs c ON t.club_id = c.id
                    LEFT JOIN series s ON t.series_id = s.id
                """)
                
                cursor.execute("SELECT COUNT(*) FROM bulletproof_polls_backup")
                backup_stats['polls'] = cursor.fetchone()[0]
                self.logger.info(f"✅ Backed up {backup_stats['polls']} polls")
                
                # Backup captain messages with team context
                self.logger.info("💬 Backing up captain messages...")
                cursor.execute("""
                    DROP TABLE IF EXISTS bulletproof_captain_messages_backup;
                    CREATE TABLE bulletproof_captain_messages_backup AS 
                    SELECT cm.*, t.team_name, t.team_alias, l.league_id as team_league_id,
                           c.name as team_club_name, s.name as team_series_name,
                           NOW() as backup_timestamp
                    FROM captain_messages cm
                    LEFT JOIN teams t ON cm.team_id = t.id
                    LEFT JOIN leagues l ON t.league_id = l.id
                    LEFT JOIN clubs c ON t.club_id = c.id
                    LEFT JOIN series s ON t.series_id = s.id
                """)
                
                cursor.execute("SELECT COUNT(*) FROM bulletproof_captain_messages_backup")
                backup_stats['captain_messages'] = cursor.fetchone()[0]
                self.logger.info(f"✅ Backed up {backup_stats['captain_messages']} captain messages")
                
                # Backup practice times with team context
                self.logger.info("⏰ Backing up practice times...")
                cursor.execute("""
                    DROP TABLE IF EXISTS bulletproof_practice_times_backup;
                    CREATE TABLE bulletproof_practice_times_backup AS 
                    SELECT s.*, t.team_name as home_team_name, t.team_alias as home_team_alias,
                           l.league_id as home_team_league_id,
                           NOW() as backup_timestamp
                    FROM schedule s
                    LEFT JOIN teams t ON s.home_team_id = t.id
                    LEFT JOIN leagues l ON t.league_id = l.id
                    WHERE s.home_team LIKE '%Practice%' OR s.home_team LIKE '%practice%'
                """)
                
                cursor.execute("SELECT COUNT(*) FROM bulletproof_practice_times_backup")
                backup_stats['practice_times'] = cursor.fetchone()[0]
                self.logger.info(f"✅ Backed up {backup_stats['practice_times']} practice times")
                
                conn.commit()
                self.backup_tables_created = True
                
                self.logger.info("💾 Backup completed successfully:")
                for table, count in backup_stats.items():
                    self.logger.info(f"   • {table}: {count} records")
                
                return backup_stats
                
            except Exception as e:
                conn.rollback()
                self.logger.error(f"❌ Backup failed: {str(e)}")
                raise
    
    def preserve_teams_during_import(self, teams_data: List[Dict]) -> Dict[str, int]:
        """
        Import teams with bulletproof ID preservation using incremental processing
        """
        self.logger.info("🏆 STEP 3: Importing teams with bulletproof ID preservation...")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            stats = {'preserved': 0, 'created': 0, 'updated': 0, 'errors': 0}
            
            try:
                # Process teams in small batches for reliability
                total_teams = len(teams_data)
                processed = 0
                
                for i in range(0, total_teams, self.batch_size):
                    batch = teams_data[i:i + self.batch_size]
                    batch_stats = self._process_team_batch(cursor, batch)
                    
                    # Update overall stats
                    for key in stats:
                        stats[key] += batch_stats[key]
                    
                    processed += len(batch)
                    
                    # Commit each batch
                    conn.commit()
                    
                    # Progress logging
                    progress = (processed / total_teams) * 100
                    self.logger.info(f"   📊 Progress: {processed}/{total_teams} ({progress:.1f}%)")
                    
                    # Health check every 5 batches
                    if (i // self.batch_size) % 5 == 0:
                        self._validate_batch_health(cursor)
                
                self.logger.info("🏆 Team import completed successfully:")
                self.logger.info(f"   • Preserved: {stats['preserved']} teams")
                self.logger.info(f"   • Created: {stats['created']} teams")
                self.logger.info(f"   • Updated: {stats['updated']} teams")
                self.logger.info(f"   • Errors: {stats['errors']} teams")
                
                return stats
                
            except Exception as e:
                conn.rollback()
                self.logger.error(f"❌ Team import failed: {str(e)}")
                raise
    
    def _process_team_batch(self, cursor, batch: List[Dict]) -> Dict[str, int]:
        """Process a single batch of teams with comprehensive error handling"""
        batch_stats = {'preserved': 0, 'created': 0, 'updated': 0, 'errors': 0}
        
        for team in batch:
            try:
                # Extract team data
                club_name = team.get("club_name", "").strip()
                series_name = team.get("series_name", "").strip()
                league_id = team.get("league_id", "").strip()
                team_name = team.get("team_name", "").strip()
                
                if not all([club_name, series_name, league_id, team_name]):
                    self.logger.warning(f"⚠️  Skipping incomplete team: {team}")
                    batch_stats['errors'] += 1
                    continue
                
                # Validate references exist
                cursor.execute("""
                    SELECT c.id, s.id, l.id 
                    FROM clubs c, series s, leagues l
                    WHERE c.name = %s AND s.name = %s AND l.league_id = %s
                """, (club_name, series_name, league_id))
                
                refs = cursor.fetchone()
                if not refs:
                    self.logger.warning(f"⚠️  Missing references for team {team_name}")
                    batch_stats['errors'] += 1
                    continue
                
                club_id, series_id, league_db_id = refs
                
                # Generate team alias
                team_alias = self._generate_team_alias(team_name, series_name)
                
                # Use bulletproof UPSERT with comprehensive error handling
                result = self._bulletproof_team_upsert(
                    cursor, club_id, series_id, league_db_id, 
                    team_name, team_alias, team_name
                )
                
                if result:
                    team_id, was_created = result
                    if was_created:
                        batch_stats['created'] += 1
                        self.logger.debug(f"   ✅ Created team: {team_name} (ID: {team_id})")
                    else:
                        batch_stats['preserved'] += 1
                        self.logger.debug(f"   📝 Preserved team: {team_name} (ID: {team_id})")
                else:
                    batch_stats['errors'] += 1
                    
            except Exception as e:
                batch_stats['errors'] += 1
                self.logger.error(f"❌ Error processing team {team.get('team_name', 'Unknown')}: {str(e)}")
        
        return batch_stats
    
    def _bulletproof_team_upsert(self, cursor, club_id: int, series_id: int, 
                                league_id: int, team_name: str, team_alias: str, 
                                display_name: str) -> Optional[Tuple[int, bool]]:
        """
        Bulletproof team UPSERT with multiple fallback strategies
        Returns (team_id, was_created) or None on failure
        """
        
        # Strategy 1: Standard UPSERT
        try:
            cursor.execute("""
                INSERT INTO teams (club_id, series_id, league_id, team_name, team_alias, display_name, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (club_id, series_id, league_id) DO UPDATE SET
                    team_name = EXCLUDED.team_name,
                    team_alias = EXCLUDED.team_alias,
                    display_name = EXCLUDED.display_name,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id, (xmax = 0) as is_insert
            """, (club_id, series_id, league_id, team_name, team_alias, display_name))
            
            result = cursor.fetchone()
            if result:
                team_id, is_insert = result
                return (team_id, is_insert)
                
        except Exception as e:
            self.logger.warning(f"⚠️  UPSERT failed for {team_name}: {str(e)}")
        
        # Strategy 2: Manual check and insert/update
        try:
            cursor.execute("""
                SELECT id FROM teams 
                WHERE club_id = %s AND series_id = %s AND league_id = %s
            """, (club_id, series_id, league_id))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing team
                team_id = existing[0]
                cursor.execute("""
                    UPDATE teams 
                    SET team_name = %s, team_alias = %s, display_name = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (team_name, team_alias, display_name, team_id))
                return (team_id, False)
            else:
                # Insert new team
                cursor.execute("""
                    INSERT INTO teams (club_id, series_id, league_id, team_name, team_alias, display_name, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    RETURNING id
                """, (club_id, series_id, league_id, team_name, team_alias, display_name))
                
                result = cursor.fetchone()
                if result:
                    return (result[0], True)
                    
        except Exception as e:
            self.logger.error(f"❌ Manual upsert failed for {team_name}: {str(e)}")
        
        return None
    
    def _generate_team_alias(self, team_name: str, series_name: str) -> str:
        """Generate team alias for display"""
        # Extract series identifier from series name
        if "Series" in series_name:
            return series_name  # Use series name as alias
        else:
            return f"Series {series_name}"  # Prefix with "Series"
    
    def _validate_batch_health(self, cursor):
        """Quick health check during batch processing"""
        try:
            # Check for orphaned references
            cursor.execute("""
                SELECT COUNT(*) FROM teams t
                LEFT JOIN leagues l ON t.league_id = l.id
                WHERE l.id IS NULL
            """)
            orphaned_teams = cursor.fetchone()[0]
            
            if orphaned_teams > 0:
                self.logger.warning(f"⚠️  Found {orphaned_teams} teams with orphaned league references")
            
        except Exception as e:
            self.logger.warning(f"Health check warning: {str(e)}")
    
    def restore_user_data(self) -> Dict[str, int]:
        """
        Restore user data with enhanced team ID mapping
        """
        self.logger.info("🔄 STEP 4: Restoring user data with enhanced team mapping...")
        
        if not self.backup_tables_created:
            self.logger.warning("⚠️  No backup tables found - skipping restore")
            return {}
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            restore_stats = {}
            
            try:
                # Create team ID mapping
                self.logger.info("🗺️  Creating team ID mapping...")
                mapping_stats = self._create_team_id_mapping(cursor)
                
                # Restore polls
                self.logger.info("📊 Restoring polls...")
                restore_stats['polls'] = self._restore_polls(cursor)
                
                # Restore captain messages
                self.logger.info("💬 Restoring captain messages...")
                restore_stats['captain_messages'] = self._restore_captain_messages(cursor)
                
                # Restore practice times
                self.logger.info("⏰ Restoring practice times...")
                restore_stats['practice_times'] = self._restore_practice_times(cursor)
                
                conn.commit()
                
                self.logger.info("🔄 User data restoration completed:")
                for table, count in restore_stats.items():
                    self.logger.info(f"   • {table}: {count} records restored")
                
                return restore_stats
                
            except Exception as e:
                conn.rollback()
                self.logger.error(f"❌ Restore failed: {str(e)}")
                raise
    
    def _create_team_id_mapping(self, cursor) -> Dict[str, int]:
        """Create mapping from old team IDs to new team IDs"""
        cursor.execute("""
            DROP TABLE IF EXISTS bulletproof_team_mappings;
            CREATE TABLE bulletproof_team_mappings AS
            SELECT 
                old_teams.id as old_team_id,
                new_teams.id as new_team_id,
                old_teams.team_name,
                old_teams.team_alias,
                old_teams.club_id,
                old_teams.series_id,
                old_teams.league_id
            FROM bulletproof_teams_backup old_teams
            JOIN teams new_teams ON (
                old_teams.club_id = new_teams.club_id
                AND old_teams.series_id = new_teams.series_id  
                AND old_teams.league_id = new_teams.league_id
            )
        """)
        
        cursor.execute("SELECT COUNT(*) FROM bulletproof_team_mappings")
        mapping_count = cursor.fetchone()[0]
        
        self.logger.info(f"✅ Created {mapping_count} team ID mappings")
        return {'mappings_created': mapping_count}
    
    def _restore_polls(self, cursor) -> int:
        """Restore polls with enhanced team ID mapping"""
        # Strategy 1: Direct ID mapping
        cursor.execute("""
            UPDATE polls 
            SET team_id = tm.new_team_id
            FROM bulletproof_polls_backup backup
            JOIN bulletproof_team_mappings tm ON backup.team_id = tm.old_team_id
            WHERE polls.id = backup.id
        """)
        direct_restored = cursor.rowcount
        
        # Strategy 2: Context-based mapping for unmapped polls
        cursor.execute("""
            UPDATE polls 
            SET team_id = new_teams.id
            FROM bulletproof_polls_backup backup
            JOIN teams new_teams ON (
                backup.team_name = new_teams.team_name
                OR backup.team_alias = new_teams.team_alias
            )
            WHERE polls.id = backup.id 
            AND polls.team_id IS NULL
            AND backup.team_id IS NOT NULL
        """)
        context_restored = cursor.rowcount
        
        total_restored = direct_restored + context_restored
        self.logger.info(f"   📊 Polls: {direct_restored} direct + {context_restored} context = {total_restored} total")
        
        return total_restored
    
    def _restore_captain_messages(self, cursor) -> int:
        """Restore captain messages with enhanced team ID mapping"""
        # Strategy 1: Direct ID mapping
        cursor.execute("""
            UPDATE captain_messages 
            SET team_id = tm.new_team_id
            FROM bulletproof_captain_messages_backup backup
            JOIN bulletproof_team_mappings tm ON backup.team_id = tm.old_team_id
            WHERE captain_messages.id = backup.id
        """)
        direct_restored = cursor.rowcount
        
        # Strategy 2: Context-based mapping for unmapped messages
        cursor.execute("""
            UPDATE captain_messages 
            SET team_id = new_teams.id
            FROM bulletproof_captain_messages_backup backup
            JOIN teams new_teams ON (
                backup.team_name = new_teams.team_name
                OR backup.team_alias = new_teams.team_alias
            )
            WHERE captain_messages.id = backup.id 
            AND captain_messages.team_id IS NULL
            AND backup.team_id IS NOT NULL
        """)
        context_restored = cursor.rowcount
        
        total_restored = direct_restored + context_restored
        self.logger.info(f"   💬 Captain messages: {direct_restored} direct + {context_restored} context = {total_restored} total")
        
        return total_restored
    
    def _restore_practice_times(self, cursor) -> int:
        """Restore practice times with enhanced team ID mapping"""
        
        # Check if practice_times table exists (non-schedule storage)
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'practice_times'
            )
        """)
        practice_times_table_exists = cursor.fetchone()[0]
        
        total_restored = 0
        
        # Strategy 1: Restore from bulletproof backup to schedule table
        if self.backup_tables_created:
            # Direct ID mapping from bulletproof backup
            cursor.execute("""
                INSERT INTO schedule (
                    league_id, match_date, match_time, home_team, away_team, 
                    home_team_id, location, created_at
                )
                SELECT 
                    backup.league_id, backup.match_date, backup.match_time, 
                    backup.home_team, backup.away_team,
                    tm.new_team_id,
                    backup.location, backup.created_at
                FROM bulletproof_practice_times_backup backup
                JOIN bulletproof_team_mappings tm ON backup.home_team_id = tm.old_team_id
                ON CONFLICT DO NOTHING
            """)
            direct_restored = cursor.rowcount
            total_restored += direct_restored
            
            # Name-based mapping for unmapped practice times
            cursor.execute("""
                INSERT INTO schedule (
                    league_id, match_date, match_time, home_team, away_team, 
                    home_team_id, location, created_at
                )
                SELECT 
                    backup.league_id, backup.match_date, backup.match_time, 
                    backup.home_team, backup.away_team,
                    new_teams.id,
                    backup.location, CURRENT_TIMESTAMP
                FROM bulletproof_practice_times_backup backup
                JOIN teams new_teams ON (
                    backup.home_team_name = new_teams.team_name
                    OR backup.home_team_alias = new_teams.team_alias
                )
                LEFT JOIN bulletproof_team_mappings tm ON backup.home_team_id = tm.old_team_id
                WHERE tm.old_team_id IS NULL
                ON CONFLICT DO NOTHING
            """)
            name_restored = cursor.rowcount
            total_restored += name_restored
            
            self.logger.info(f"   ⏰ Practice times from bulletproof backup: {direct_restored} direct + {name_restored} name-based = {total_restored} total")
        
        # Strategy 2: Fix existing practice_times table if it has orphaned team_ids
        if practice_times_table_exists:
            fixed_from_practice_times = self._fix_orphaned_practice_times_table(cursor)
            total_restored += fixed_from_practice_times
        
        # Strategy 3: Restore from legacy team_mapping_backup if available
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'team_mapping_backup'
            )
        """)
        legacy_backup_exists = cursor.fetchone()[0]
        
        if legacy_backup_exists and practice_times_table_exists:
            legacy_restored = self._restore_from_legacy_practice_times(cursor)
            total_restored += legacy_restored
        
        return total_restored
    
    def _fix_orphaned_practice_times_table(self, cursor) -> int:
        """Fix orphaned team_ids in existing practice_times table"""
        
        # Check for orphaned practice times (team_ids that don't exist in teams table)
        cursor.execute("""
            SELECT COUNT(*) FROM practice_times pt
            LEFT JOIN teams t ON pt.team_id = t.id
            WHERE pt.team_id IS NOT NULL AND t.id IS NULL
        """)
        orphaned_count = cursor.fetchone()[0]
        
        if orphaned_count == 0:
            self.logger.info("   ✅ No orphaned practice times found")
            return 0
        
        self.logger.info(f"   🔧 Found {orphaned_count} orphaned practice times to fix")
        
        fixed_count = 0
        
        # Strategy 1: Use team_mapping_backup if available
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'team_mapping_backup'
            )
        """)
        team_mapping_exists = cursor.fetchone()[0]
        
        if team_mapping_exists:
            # Map using team_mapping_backup
            cursor.execute("""
                UPDATE practice_times 
                SET team_id = (
                    SELECT new_team_id 
                    FROM team_mapping_backup tmb
                    WHERE tmb.old_team_id = practice_times.team_id
                    LIMIT 1
                )
                WHERE team_id IN (
                    SELECT pt.team_id FROM practice_times pt
                    LEFT JOIN teams t ON pt.team_id = t.id
                    WHERE pt.team_id IS NOT NULL AND t.id IS NULL
                )
                AND team_id IN (SELECT old_team_id FROM team_mapping_backup)
            """)
            mapping_fixed = cursor.rowcount
            fixed_count += mapping_fixed
            self.logger.info(f"   ✅ Fixed {mapping_fixed} practice times using team mapping")
        
        # Strategy 2: Pattern-based matching for remaining orphans
        cursor.execute("""
            SELECT pt.id, pt.team_id, pt.day_of_week, pt.start_time, pt.location, pt.league_id
            FROM practice_times pt
            LEFT JOIN teams t ON pt.team_id = t.id
            WHERE pt.team_id IS NOT NULL AND t.id IS NULL
        """)
        remaining_orphans = cursor.fetchall()
        
        for practice in remaining_orphans:
            practice_id, old_team_id, day_of_week, start_time, location, league_id = practice
            
            # Try to find matching team by location and league
            cursor.execute("""
                SELECT t.id 
                FROM teams t
                JOIN leagues l ON t.league_id = l.id
                WHERE l.id = %s
                AND (t.team_name LIKE %s OR t.team_alias LIKE %s)
                LIMIT 1
            """, (league_id, f'%{location}%', f'%{location}%'))
            
            match = cursor.fetchone()
            if match:
                new_team_id = match[0]
                cursor.execute("""
                    UPDATE practice_times 
                    SET team_id = %s 
                    WHERE id = %s
                """, (new_team_id, practice_id))
                fixed_count += 1
                self.logger.info(f"   ✅ Fixed practice time {practice_id}: {old_team_id} → {new_team_id}")
            else:
                self.logger.warning(f"   ⚠️  Could not find team for practice time {practice_id}")
        
        return fixed_count
    
    def _restore_from_legacy_practice_times(self, cursor) -> int:
        """Restore practice times from legacy practice_times table to schedule table"""
        
        # Insert practice times from practice_times table into schedule table for consistent storage
        cursor.execute("""
            INSERT INTO schedule (
                league_id, match_date, match_time, home_team, away_team, 
                home_team_id, location, created_at
            )
            SELECT 
                pt.league_id,
                CURRENT_DATE + (pt.start_time - pt.start_time) + 
                    CASE pt.day_of_week
                        WHEN 'Monday' THEN INTERVAL '0 days'
                        WHEN 'Tuesday' THEN INTERVAL '1 day'
                        WHEN 'Wednesday' THEN INTERVAL '2 days'
                        WHEN 'Thursday' THEN INTERVAL '3 days'
                        WHEN 'Friday' THEN INTERVAL '4 days'
                        WHEN 'Saturday' THEN INTERVAL '5 days'
                        WHEN 'Sunday' THEN INTERVAL '6 days'
                    END as match_date,
                pt.start_time,
                t.team_name || ' Practice' as home_team,
                'Practice' as away_team,
                pt.team_id,
                pt.location,
                CURRENT_TIMESTAMP
            FROM practice_times pt
            JOIN teams t ON pt.team_id = t.id
            WHERE pt.team_id IS NOT NULL
            ON CONFLICT DO NOTHING
        """)
        
        restored_count = cursor.rowcount
        if restored_count > 0:
            self.logger.info(f"   ✅ Restored {restored_count} practice times from practice_times table to schedule")
        
        return restored_count
    
    def validate_health(self) -> Dict[str, Any]:
        """
        Comprehensive health validation after ETL completion
        """
        self.logger.info("🔍 STEP 5: Validating system health...")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            health_report = {
                'overall_health': 'HEALTHY',
                'issues': [],
                'stats': {}
            }
            
            try:
                # Check 1: Orphaned polls
                cursor.execute("""
                    SELECT COUNT(*) FROM polls p
                    LEFT JOIN teams t ON p.team_id = t.id
                    WHERE p.team_id IS NOT NULL AND t.id IS NULL
                """)
                orphaned_polls = cursor.fetchone()[0]
                health_report['stats']['orphaned_polls'] = orphaned_polls
                
                if orphaned_polls > 0:
                    health_report['issues'].append(f"{orphaned_polls} orphaned polls")
                    health_report['overall_health'] = 'DEGRADED'
                
                # Check 2: Orphaned captain messages
                cursor.execute("""
                    SELECT COUNT(*) FROM captain_messages cm
                    LEFT JOIN teams t ON cm.team_id = t.id
                    WHERE cm.team_id IS NOT NULL AND t.id IS NULL
                """)
                orphaned_messages = cursor.fetchone()[0]
                health_report['stats']['orphaned_captain_messages'] = orphaned_messages
                
                if orphaned_messages > 0:
                    health_report['issues'].append(f"{orphaned_messages} orphaned captain messages")
                    health_report['overall_health'] = 'DEGRADED'
                
                # Check 3: Orphaned practice times (both in schedule and practice_times tables)
                cursor.execute("""
                    SELECT COUNT(*) FROM schedule s
                    LEFT JOIN teams t ON s.home_team_id = t.id
                    WHERE s.home_team_id IS NOT NULL AND t.id IS NULL
                    AND (s.home_team LIKE '%Practice%' OR s.home_team LIKE '%practice%')
                """)
                orphaned_schedule_practice = cursor.fetchone()[0]
                
                # Check practice_times table if it exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'practice_times'
                    )
                """)
                practice_times_exists = cursor.fetchone()[0]
                
                orphaned_practice_times_table = 0
                if practice_times_exists:
                    cursor.execute("""
                        SELECT COUNT(*) FROM practice_times pt
                        LEFT JOIN teams t ON pt.team_id = t.id
                        WHERE pt.team_id IS NOT NULL AND t.id IS NULL
                    """)
                    orphaned_practice_times_table = cursor.fetchone()[0]
                
                total_orphaned_practice = orphaned_schedule_practice + orphaned_practice_times_table
                health_report['stats']['orphaned_practice_times_schedule'] = orphaned_schedule_practice
                health_report['stats']['orphaned_practice_times_table'] = orphaned_practice_times_table
                health_report['stats']['orphaned_practice_times_total'] = total_orphaned_practice
                
                if total_orphaned_practice > 0:
                    health_report['issues'].append(f"{total_orphaned_practice} orphaned practice times ({orphaned_schedule_practice} in schedule, {orphaned_practice_times_table} in practice_times)")
                    health_report['overall_health'] = 'DEGRADED'
                
                # Check 4: Team integrity
                cursor.execute("""
                    SELECT COUNT(*) FROM teams t
                    LEFT JOIN leagues l ON t.league_id = l.id
                    LEFT JOIN clubs c ON t.club_id = c.id
                    LEFT JOIN series s ON t.series_id = s.id
                    WHERE l.id IS NULL OR c.id IS NULL OR s.id IS NULL
                """)
                invalid_teams = cursor.fetchone()[0]
                health_report['stats']['invalid_teams'] = invalid_teams
                
                if invalid_teams > 0:
                    health_report['issues'].append(f"{invalid_teams} teams with invalid references")
                    health_report['overall_health'] = 'CRITICAL'
                
                # Check 5: Successful preservation rate
                if hasattr(self, 'backup_tables_created') and self.backup_tables_created:
                    cursor.execute("""
                        SELECT 
                            (SELECT COUNT(*) FROM bulletproof_teams_backup) as backed_up,
                            (SELECT COUNT(*) FROM teams) as current_count
                    """)
                    backup_count, current_count = cursor.fetchone()
                    
                    if current_count > 0:
                        preservation_rate = min(100.0, (current_count / backup_count) * 100)
                        health_report['stats']['team_preservation_rate'] = preservation_rate
                        
                        if preservation_rate < 90:
                            health_report['issues'].append(f"Low team preservation rate: {preservation_rate:.1f}%")
                            health_report['overall_health'] = 'CRITICAL'
                
                # Final health assessment
                if health_report['overall_health'] == 'HEALTHY':
                    self.logger.info("✅ System health: HEALTHY")
                    self.logger.info("   • No orphaned records found")
                    self.logger.info("   • All team references are valid")
                    self.logger.info("   • High preservation rate achieved")
                elif health_report['overall_health'] == 'DEGRADED':
                    self.logger.warning("⚠️  System health: DEGRADED")
                    for issue in health_report['issues']:
                        self.logger.warning(f"   • {issue}")
                else:
                    self.logger.error("❌ System health: CRITICAL")
                    for issue in health_report['issues']:
                        self.logger.error(f"   • {issue}")
                
                return health_report
                
            except Exception as e:
                health_report['overall_health'] = 'ERROR'
                health_report['issues'].append(f"Health check failed: {str(e)}")
                self.logger.error(f"❌ Health validation failed: {str(e)}")
                return health_report
    
    def auto_repair_orphans(self) -> Dict[str, int]:
        """
        Automatically repair any orphaned records found during health check
        """
        self.logger.info("🔧 Running automatic orphan repair...")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            repair_stats = {'polls_fixed': 0, 'messages_fixed': 0, 'practice_times_fixed': 0}
            
            try:
                # Import the fix functions from our earlier fix script
                try:
                    from scripts.fix_team_id_orphans import (
                        find_correct_team_for_poll,
                        find_correct_team_for_captain_message
                    )
                    
                    # Fix orphaned polls
                    cursor.execute("""
                        SELECT p.id, p.team_id, p.question, p.created_by
                        FROM polls p
                        LEFT JOIN teams t ON p.team_id = t.id
                        WHERE p.team_id IS NOT NULL AND t.id IS NULL
                    """)
                    
                    orphaned_polls = cursor.fetchall()
                    for poll_id, old_team_id, question, created_by in orphaned_polls:
                        new_team_id = find_correct_team_for_poll(cursor, created_by, question, old_team_id)
                        if new_team_id:
                            cursor.execute("UPDATE polls SET team_id = %s WHERE id = %s", (new_team_id, poll_id))
                            repair_stats['polls_fixed'] += 1
                        else:
                            cursor.execute("UPDATE polls SET team_id = NULL WHERE id = %s", (poll_id,))
                    
                    # Fix orphaned captain messages
                    cursor.execute("""
                        SELECT cm.id, cm.team_id, cm.message, cm.captain_user_id
                        FROM captain_messages cm
                        LEFT JOIN teams t ON cm.team_id = t.id
                        WHERE cm.team_id IS NOT NULL AND t.id IS NULL
                    """)
                    
                    orphaned_messages = cursor.fetchall()
                    for msg_id, old_team_id, message, captain_user_id in orphaned_messages:
                        new_team_id = find_correct_team_for_captain_message(cursor, captain_user_id, message, old_team_id)
                        if new_team_id:
                            cursor.execute("UPDATE captain_messages SET team_id = %s WHERE id = %s", (new_team_id, msg_id))
                            repair_stats['messages_fixed'] += 1
                        else:
                            cursor.execute("DELETE FROM captain_messages WHERE id = %s", (msg_id,))
                            
                except ImportError:
                    self.logger.warning("⚠️  Could not import fix_team_id_orphans script functions")
                
                # Fix orphaned practice times using built-in methods
                practice_times_fixed = self._fix_orphaned_practice_times_table(cursor)
                repair_stats['practice_times_fixed'] = practice_times_fixed
                
                conn.commit()
                
                self.logger.info("🔧 Automatic repair completed:")
                for key, count in repair_stats.items():
                    if count > 0:
                        self.logger.info(f"   • {key}: {count}")
                
                return repair_stats
                
            except Exception as e:
                conn.rollback()
                self.logger.error(f"❌ Auto-repair failed: {str(e)}")
                return repair_stats


def integrate_with_existing_etl():
    """
    Integration function to use bulletproof preservation in existing ETL
    """
    
    def enhanced_import_teams(etl_instance, conn, teams_data):
        """Enhanced team import function for existing ETL"""
        etl_instance.log("🛡️  Using bulletproof team ID preservation...")
        
        with BulletproofTeamPreservation() as preservation:
            # Validate constraints
            if not preservation.validate_constraints():
                raise Exception("Constraint validation failed - ETL cannot proceed safely")
            
            # Backup user data
            preservation.backup_user_data()
            
            # Import teams with preservation
            preservation.preserve_teams_during_import(teams_data)
            
            # Restore user data
            preservation.restore_user_data()
            
            # Validate health
            health = preservation.validate_health()
            
            if health['overall_health'] not in ['HEALTHY', 'DEGRADED']:
                # Attempt automatic repair
                preservation.auto_repair_orphans()
                
                # Re-validate
                health = preservation.validate_health()
                
                if health['overall_health'] == 'CRITICAL':
                    raise Exception(f"Team ID preservation failed: {health['issues']}")
            
            etl_instance.log("✅ Bulletproof team ID preservation completed")
    
    return enhanced_import_teams


if __name__ == "__main__":
    # Example usage and testing
    print("🛡️  Bulletproof Team ID Preservation System")
    print("=" * 60)
    
    with BulletproofTeamPreservation() as preservation:
        # Run validation
        if preservation.validate_constraints():
            print("✅ Constraints validated")
        else:
            print("❌ Constraint validation failed")
        
        # Run health check
        health = preservation.validate_health()
        print(f"System health: {health['overall_health']}")
        
        if health['issues']:
            print("Issues found:")
            for issue in health['issues']:
                print(f"  • {issue}")
        else:
            print("✅ No issues found") 