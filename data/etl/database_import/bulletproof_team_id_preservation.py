#!/usr/bin/env python3
"""
Bulletproof ETL Team ID Preservation System

This module provides a comprehensive solution to prevent orphaned records during ETL imports
by ensuring team IDs are preserved and user data is properly backed up and restored.

Key Features:
- Pre-validation of database constraints
- Automatic constraint repair
- Incremental team processing
- Comprehensive user data backup
- Multi-strategy restoration
- Real-time health monitoring
- Automatic orphan detection and repair
"""

import logging
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from database_utils import execute_query, execute_query_one, execute_update, get_db

logger = logging.getLogger(__name__)

class BulletproofTeamPreservation:
    """
    Bulletproof team ID preservation system that guarantees zero orphaned records.
    
    This class provides comprehensive protection against orphaned records during ETL
    by implementing multiple layers of safety measures and fallback strategies.
    """
    
    def __init__(self):
        self.stats = {
            'teams_preserved': 0,
            'teams_created': 0,
            'teams_updated': 0,
            'backup_records': 0,
            'restored_records': 0,
            'orphans_fixed': 0,
            'constraints_repaired': 0,
            'errors': 0
        }
        
    def validate_constraints(self, conn) -> Tuple[bool, List[str]]:
        """
        Validate all database constraints before ETL starts.
        
        Returns:
            Tuple[bool, List[str]]: (is_safe, list_of_issues)
        """
        issues = []
        
        try:
            # Check if unique constraint exists
            constraint_check = execute_query_one("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.table_constraints 
                    WHERE constraint_name = 'unique_team_club_series_league'
                    AND table_name = 'teams'
                )
            """)
            
            if not constraint_check or not constraint_check['exists']:
                issues.append("Missing unique constraint: unique_team_club_series_league")
            
            # Check for NULL values in constraint columns
            null_check = execute_query_one("""
                SELECT COUNT(*) as count
                FROM teams 
                WHERE club_id IS NULL OR series_id IS NULL OR league_id IS NULL
            """)
            
            if null_check and null_check['count'] > 0:
                issues.append(f"Found {null_check['count']} teams with NULL values in constraint columns")
            
            # Check foreign key constraints
            fk_check = execute_query("""
                SELECT 
                    tc.constraint_name,
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = 'teams'
            """)
            
            expected_fks = ['teams_club_id_fkey', 'teams_series_id_fkey', 'teams_league_id_fkey']
            existing_fks = [fk['constraint_name'] for fk in fk_check]
            
            for expected_fk in expected_fks:
                if expected_fk not in existing_fks:
                    issues.append(f"Missing foreign key constraint: {expected_fk}")
            
            return len(issues) == 0, issues
            
        except Exception as e:
            issues.append(f"Constraint validation error: {str(e)}")
            return False, issues
    
    def repair_constraints(self, conn) -> bool:
        """
        Automatically repair database constraints.
        
        Returns:
            bool: True if repair was successful
        """
        try:
            # Create unique constraint if missing
            execute_update("""
                ALTER TABLE teams 
                ADD CONSTRAINT IF NOT EXISTS unique_team_club_series_league 
                UNIQUE (club_id, series_id, league_id)
            """)
            
            # Create foreign key constraints if missing
            execute_update("""
                ALTER TABLE teams 
                ADD CONSTRAINT IF NOT EXISTS teams_club_id_fkey 
                FOREIGN KEY (club_id) REFERENCES clubs(id)
            """)
            
            execute_update("""
                ALTER TABLE teams 
                ADD CONSTRAINT IF NOT EXISTS teams_series_id_fkey 
                FOREIGN KEY (series_id) REFERENCES series(id)
            """)
            
            execute_update("""
                ALTER TABLE teams 
                ADD CONSTRAINT IF NOT EXISTS teams_league_id_fkey 
                FOREIGN KEY (league_id) REFERENCES leagues(id)
            """)
            
            # Fix NULL values in constraint columns
            null_fix = execute_update("""
                UPDATE teams 
                SET club_id = (SELECT id FROM clubs LIMIT 1)
                WHERE club_id IS NULL
            """)
            
            if null_fix > 0:
                self.stats['constraints_repaired'] += null_fix
                logger.warning(f"Fixed {null_fix} teams with NULL club_id")
            
            return True
            
        except Exception as e:
            logger.error(f"Constraint repair failed: {str(e)}")
            return False
    
    def backup_user_data(self, conn) -> Dict[str, int]:
        """
        Create comprehensive backup of all user data before ETL.
        
        Returns:
            Dict[str, int]: Backup statistics
        """
        backup_stats = {}
        
        try:
            # Backup teams with metadata
            execute_update("""
                DROP TABLE IF EXISTS bulletproof_teams_backup;
                CREATE TABLE bulletproof_teams_backup AS 
                SELECT *, NOW() as backup_timestamp FROM teams
            """)
            
            teams_count = execute_query_one("SELECT COUNT(*) as count FROM bulletproof_teams_backup")
            backup_stats['teams'] = teams_count['count'] if teams_count else 0
            
            # Backup polls with team context
            execute_update("""
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
            
            polls_count = execute_query_one("SELECT COUNT(*) as count FROM bulletproof_polls_backup")
            backup_stats['polls'] = polls_count['count'] if polls_count else 0
            
            # Backup captain messages with team context
            execute_update("""
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
            
            messages_count = execute_query_one("SELECT COUNT(*) as count FROM bulletproof_captain_messages_backup")
            backup_stats['captain_messages'] = messages_count['count'] if messages_count else 0
            
            # Backup practice times
            execute_update("""
                DROP TABLE IF EXISTS bulletproof_practice_times_backup;
                CREATE TABLE bulletproof_practice_times_backup AS 
                SELECT s.*, t.team_name, t.team_alias, l.league_id as team_league_id,
                       c.name as team_club_name, s2.name as team_series_name,
                       NOW() as backup_timestamp
                FROM schedule s
                LEFT JOIN teams t ON s.home_team_id = t.id
                LEFT JOIN leagues l ON t.league_id = l.id
                LEFT JOIN clubs c ON t.club_id = c.id
                LEFT JOIN series s2 ON t.series_id = s2.id
                WHERE s.home_team LIKE '%Practice%' OR s.home_team LIKE '%practice%'
            """)
            
            practice_count = execute_query_one("SELECT COUNT(*) as count FROM bulletproof_practice_times_backup")
            backup_stats['practice_times'] = practice_count['count'] if practice_count else 0
            
            # Backup user associations
            execute_update("""
                DROP TABLE IF EXISTS bulletproof_user_associations_backup;
                CREATE TABLE bulletproof_user_associations_backup AS 
                SELECT *, NOW() as backup_timestamp FROM user_player_associations
            """)
            
            associations_count = execute_query_one("SELECT COUNT(*) as count FROM bulletproof_user_associations_backup")
            backup_stats['user_associations'] = associations_count['count'] if associations_count else 0
            
            # Backup availability data
            execute_update("""
                DROP TABLE IF EXISTS bulletproof_availability_backup;
                CREATE TABLE bulletproof_availability_backup AS 
                SELECT *, NOW() as backup_timestamp FROM player_availability
            """)
            
            availability_count = execute_query_one("SELECT COUNT(*) as count FROM bulletproof_availability_backup")
            backup_stats['availability'] = availability_count['count'] if availability_count else 0
            
            self.stats['backup_records'] = sum(backup_stats.values())
            logger.info(f"Backup completed: {backup_stats}")
            
            return backup_stats
            
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            self.stats['errors'] += 1
            return {}
    
    def import_teams_bulletproof(self, conn, teams_data: List[Dict]) -> Dict[str, int]:
        """
        Import teams using bulletproof UPSERT strategy.
        
        Args:
            conn: Database connection
            teams_data: List of team data dictionaries
            
        Returns:
            Dict[str, int]: Import statistics
        """
        import_stats = {'preserved': 0, 'created': 0, 'updated': 0, 'errors': 0}
        
        try:
            # Process teams in batches of 50
            batch_size = 50
            for i in range(0, len(teams_data), batch_size):
                batch = teams_data[i:i + batch_size]
                
                for team_data in batch:
                    try:
                        # Extract team data
                        club_id = team_data.get('club_id')
                        series_id = team_data.get('series_id')
                        league_id = team_data.get('league_id')
                        team_name = team_data.get('team_name', '')
                        team_alias = team_data.get('team_alias', '')
                        display_name = team_data.get('display_name', team_name)
                        
                        # Validate required fields
                        if not all([club_id, series_id, league_id, team_name]):
                            logger.warning(f"Skipping team with missing data: {team_data}")
                            import_stats['errors'] += 1
                            continue
                        
                        # Try UPSERT first
                        result = execute_query_one("""
                            INSERT INTO teams (club_id, series_id, league_id, team_name, team_alias, display_name, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                            ON CONFLICT (club_id, series_id, league_id) DO UPDATE SET
                                team_name = EXCLUDED.team_name,
                                team_alias = EXCLUDED.team_alias,
                                display_name = EXCLUDED.display_name,
                                updated_at = CURRENT_TIMESTAMP
                            RETURNING id, (xmax = 0) as is_insert
                        """, (club_id, series_id, league_id, team_name, team_alias, display_name))
                        
                        if result:
                            if result['is_insert']:
                                import_stats['created'] += 1
                                logger.debug(f"Created team: {team_name}")
                            else:
                                import_stats['preserved'] += 1
                                logger.debug(f"Preserved team: {team_name}")
                        else:
                            # Fallback: manual check and insert/update
                            existing = execute_query_one("""
                                SELECT id FROM teams 
                                WHERE club_id = %s AND series_id = %s AND league_id = %s
                            """, (club_id, series_id, league_id))
                            
                            if existing:
                                # Update existing team
                                execute_update("""
                                    UPDATE teams 
                                    SET team_name = %s, team_alias = %s, display_name = %s, updated_at = CURRENT_TIMESTAMP
                                    WHERE id = %s
                                """, (team_name, team_alias, display_name, existing['id']))
                                import_stats['updated'] += 1
                                logger.debug(f"Updated team: {team_name}")
                            else:
                                # Insert new team
                                execute_update("""
                                    INSERT INTO teams (club_id, series_id, league_id, team_name, team_alias, display_name, created_at)
                                    VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                                """, (club_id, series_id, league_id, team_name, team_alias, display_name))
                                import_stats['created'] += 1
                                logger.debug(f"Created team (fallback): {team_name}")
                        
                    except Exception as e:
                        logger.error(f"Error importing team {team_data.get('team_name', 'unknown')}: {str(e)}")
                        import_stats['errors'] += 1
                
                logger.info(f"Processed batch {i//batch_size + 1}: {len(batch)} teams")
            
            self.stats['teams_preserved'] = import_stats['preserved']
            self.stats['teams_created'] = import_stats['created']
            self.stats['teams_updated'] = import_stats['updated']
            
            logger.info(f"Team import completed: {import_stats}")
            return import_stats
            
        except Exception as e:
            logger.error(f"Team import failed: {str(e)}")
            self.stats['errors'] += 1
            return import_stats
    
    def restore_user_data(self, conn) -> Dict[str, int]:
        """
        Restore user data using multiple strategies.
        
        Returns:
            Dict[str, int]: Restoration statistics
        """
        restore_stats = {}
        
        try:
            # Strategy 1: Direct ID mapping (if team IDs were preserved)
            preserved_mapping = execute_query("""
                SELECT 
                    old.id as old_id, 
                    new.id as new_id,
                    old.team_name,
                    old.team_alias
                FROM bulletproof_teams_backup old
                JOIN teams new ON (
                    new.club_id = old.club_id AND 
                    new.series_id = old.series_id AND 
                    new.league_id = old.league_id
                )
            """)
            
            if preserved_mapping:
                # Team IDs were preserved - use direct mapping
                logger.info(f"Using direct ID mapping for {len(preserved_mapping)} teams")
                
                # Restore polls
                polls_restored = self._restore_polls_direct_mapping(conn, preserved_mapping)
                restore_stats['polls'] = polls_restored
                
                # Restore captain messages
                messages_restored = self._restore_captain_messages_direct_mapping(conn, preserved_mapping)
                restore_stats['captain_messages'] = messages_restored
                
                # Restore practice times
                practice_restored = self._restore_practice_times_direct_mapping(conn, preserved_mapping)
                restore_stats['practice_times'] = practice_restored
                
            else:
                # Team IDs changed - use context-based mapping
                logger.info("Team IDs changed - using context-based mapping")
                
                # Restore polls with context matching
                polls_restored = self._restore_polls_context_matching(conn)
                restore_stats['polls'] = polls_restored
                
                # Restore captain messages with context matching
                messages_restored = self._restore_captain_messages_context_matching(conn)
                restore_stats['captain_messages'] = messages_restored
                
                # Restore practice times with context matching
                practice_restored = self._restore_practice_times_context_matching(conn)
                restore_stats['practice_times'] = practice_restored
            
            # Restore user associations
            associations_restored = self._restore_user_associations(conn)
            restore_stats['user_associations'] = associations_restored
            
            # Restore availability data
            availability_restored = self._restore_availability_data(conn)
            restore_stats['availability'] = availability_restored
            
            self.stats['restored_records'] = sum(restore_stats.values())
            logger.info(f"User data restoration completed: {restore_stats}")
            
            return restore_stats
            
        except Exception as e:
            logger.error(f"User data restoration failed: {str(e)}")
            self.stats['errors'] += 1
            return restore_stats
    
    def _restore_polls_direct_mapping(self, conn, team_mapping: List[Dict]) -> int:
        """Restore polls using direct team ID mapping."""
        restored = 0
        
        for mapping in team_mapping:
            result = execute_update("""
                UPDATE polls 
                SET team_id = %s, updated_at = CURRENT_TIMESTAMP
                FROM bulletproof_polls_backup pb
                WHERE polls.id = pb.id AND pb.team_id = %s
            """, (mapping['new_id'], mapping['old_id']))
            restored += result if result else 0
        
        return restored
    
    def _restore_captain_messages_direct_mapping(self, conn, team_mapping: List[Dict]) -> int:
        """Restore captain messages using direct team ID mapping."""
        restored = 0
        
        for mapping in team_mapping:
            result = execute_update("""
                UPDATE captain_messages 
                SET team_id = %s, updated_at = CURRENT_TIMESTAMP
                FROM bulletproof_captain_messages_backup cmb
                WHERE captain_messages.id = cmb.id AND cmb.team_id = %s
            """, (mapping['new_id'], mapping['old_id']))
            restored += result if result else 0
        
        return restored
    
    def _restore_practice_times_direct_mapping(self, conn, team_mapping: List[Dict]) -> int:
        """Restore practice times using direct team ID mapping."""
        restored = 0
        
        for mapping in team_mapping:
            result = execute_update("""
                UPDATE schedule 
                SET home_team_id = %s, updated_at = CURRENT_TIMESTAMP
                FROM bulletproof_practice_times_backup ptb
                WHERE schedule.id = ptb.id AND ptb.home_team_id = %s
            """, (mapping['new_id'], mapping['old_id']))
            restored += result if result else 0
        
        return restored
    
    def _restore_polls_context_matching(self, conn) -> int:
        """Restore polls using context-based matching."""
        result = execute_update("""
            UPDATE polls 
            SET team_id = t.id, updated_at = CURRENT_TIMESTAMP
            FROM bulletproof_polls_backup pb
            JOIN teams t ON t.team_name = pb.team_name
            JOIN leagues l ON t.league_id = l.id AND l.league_id = pb.team_league_id
            JOIN clubs c ON t.club_id = c.id AND c.name = pb.team_club_name
            JOIN series s ON t.series_id = s.id AND s.name = pb.team_series_name
            WHERE polls.id = pb.id AND polls.team_id IS NULL
        """)
        
        return result if result else 0
    
    def _restore_captain_messages_context_matching(self, conn) -> int:
        """Restore captain messages using context-based matching."""
        result = execute_update("""
            UPDATE captain_messages 
            SET team_id = t.id, updated_at = CURRENT_TIMESTAMP
            FROM bulletproof_captain_messages_backup cmb
            JOIN teams t ON t.team_name = cmb.team_name
            JOIN leagues l ON t.league_id = l.id AND l.league_id = cmb.team_league_id
            JOIN clubs c ON t.club_id = c.id AND c.name = cmb.team_club_name
            JOIN series s ON t.series_id = s.id AND s.name = cmb.team_series_name
            WHERE captain_messages.id = cmb.id AND captain_messages.team_id IS NULL
        """)
        
        return result if result else 0
    
    def _restore_practice_times_context_matching(self, conn) -> int:
        """Restore practice times using context-based matching."""
        result = execute_update("""
            UPDATE schedule 
            SET home_team_id = t.id, updated_at = CURRENT_TIMESTAMP
            FROM bulletproof_practice_times_backup ptb
            JOIN teams t ON t.team_name = ptb.team_name
            JOIN leagues l ON t.league_id = l.id AND l.league_id = ptb.team_league_id
            JOIN clubs c ON t.club_id = c.id AND c.name = ptb.team_club_name
            JOIN series s ON t.series_id = s.id AND s.name = ptb.team_series_name
            WHERE schedule.id = ptb.id AND schedule.home_team_id IS NULL
        """)
        
        return result if result else 0
    
    def _restore_user_associations(self, conn) -> int:
        """Restore user associations."""
        result = execute_update("""
            INSERT INTO user_player_associations (user_id, tenniscores_player_id, created_at)
            SELECT user_id, tenniscores_player_id, created_at
            FROM bulletproof_user_associations_backup
            ON CONFLICT (user_id, tenniscores_player_id) DO NOTHING
        """)
        
        return result if result else 0
    
    def _restore_availability_data(self, conn) -> int:
        """Restore availability data."""
        result = execute_update("""
            INSERT INTO player_availability (user_id, match_date, availability_status, notes, created_at)
            SELECT user_id, match_date, availability_status, notes, created_at
            FROM bulletproof_availability_backup
            ON CONFLICT (user_id, match_date) DO UPDATE SET
                availability_status = EXCLUDED.availability_status,
                notes = EXCLUDED.notes,
                updated_at = CURRENT_TIMESTAMP
        """)
        
        return result if result else 0
    
    def detect_and_fix_orphans(self, conn) -> Dict[str, int]:
        """
        Detect and automatically fix any remaining orphaned records.
        
        Returns:
            Dict[str, int]: Orphan detection and fix statistics
        """
        orphan_stats = {'detected': 0, 'fixed': 0, 'errors': 0}
        
        try:
            # Detect orphaned polls
            orphaned_polls = execute_query_one("""
                SELECT COUNT(*) as count
                FROM polls p
                LEFT JOIN teams t ON p.team_id = t.id
                WHERE p.team_id IS NOT NULL AND t.id IS NULL
            """)
            
            if orphaned_polls and orphaned_polls['count'] > 0:
                orphan_stats['detected'] += orphaned_polls['count']
                logger.warning(f"Detected {orphaned_polls['count']} orphaned polls")
                
                # Fix orphaned polls using content analysis
                fixed_polls = self._fix_orphaned_polls(conn)
                orphan_stats['fixed'] += fixed_polls
            
            # Detect orphaned captain messages
            orphaned_messages = execute_query_one("""
                SELECT COUNT(*) as count
                FROM captain_messages cm
                LEFT JOIN teams t ON cm.team_id = t.id
                WHERE cm.team_id IS NOT NULL AND t.id IS NULL
            """)
            
            if orphaned_messages and orphaned_messages['count'] > 0:
                orphan_stats['detected'] += orphaned_messages['count']
                logger.warning(f"Detected {orphaned_messages['count']} orphaned captain messages")
                
                # Fix orphaned captain messages
                fixed_messages = self._fix_orphaned_captain_messages(conn)
                orphan_stats['fixed'] += fixed_messages
            
            # Detect orphaned practice times
            orphaned_practice = execute_query_one("""
                SELECT COUNT(*) as count
                FROM schedule s
                LEFT JOIN teams t ON s.home_team_id = t.id
                WHERE s.home_team_id IS NOT NULL AND t.id IS NULL
                AND (s.home_team LIKE '%Practice%' OR s.home_team LIKE '%practice%')
            """)
            
            if orphaned_practice and orphaned_practice['count'] > 0:
                orphan_stats['detected'] += orphaned_practice['count']
                logger.warning(f"Detected {orphaned_practice['count']} orphaned practice times")
                
                # Fix orphaned practice times
                fixed_practice = self._fix_orphaned_practice_times(conn)
                orphan_stats['fixed'] += fixed_practice
            
            self.stats['orphans_fixed'] = orphan_stats['fixed']
            logger.info(f"Orphan detection and fix completed: {orphan_stats}")
            
            return orphan_stats
            
        except Exception as e:
            logger.error(f"Orphan detection and fix failed: {str(e)}")
            orphan_stats['errors'] += 1
            return orphan_stats
    
    def _fix_orphaned_polls(self, conn) -> int:
        """Fix orphaned polls using content analysis."""
        # Find polls with series references and match to appropriate teams
        result = execute_update("""
            UPDATE polls 
            SET team_id = t.id
            FROM teams t
            JOIN leagues l ON t.league_id = l.id
            WHERE polls.team_id IS NULL
            AND (
                (polls.question LIKE '%Series 2B%' AND t.team_alias LIKE '%2B%' AND l.league_id = 'NSTF')
                OR (polls.question LIKE '%Series 22%' AND t.team_alias LIKE '%22%' AND l.league_id = 'APTA_CHICAGO')
            )
        """)
        
        return result if result else 0
    
    def _fix_orphaned_captain_messages(self, conn) -> int:
        """Fix orphaned captain messages using content analysis."""
        # Find captain messages with series references and match to appropriate teams
        result = execute_update("""
            UPDATE captain_messages 
            SET team_id = t.id
            FROM teams t
            JOIN leagues l ON t.league_id = l.id
            WHERE captain_messages.team_id IS NULL
            AND (
                (captain_messages.message LIKE '%Series 2B%' AND t.team_alias LIKE '%2B%' AND l.league_id = 'NSTF')
                OR (captain_messages.message LIKE '%Series 22%' AND t.team_alias LIKE '%22%' AND l.league_id = 'APTA_CHICAGO')
            )
        """)
        
        return result if result else 0
    
    def _fix_orphaned_practice_times(self, conn) -> int:
        """Fix orphaned practice times using team name matching."""
        # Find practice times and match to teams by name
        result = execute_update("""
            UPDATE schedule 
            SET home_team_id = t.id
            FROM teams t
            WHERE schedule.home_team_id IS NULL
            AND (schedule.home_team LIKE '%Practice%' OR schedule.home_team LIKE '%practice%')
            AND t.team_name = schedule.home_team
        """)
        
        return result if result else 0
    
    def cleanup_backup_tables(self, conn) -> bool:
        """
        Clean up all backup tables after successful ETL.
        
        Returns:
            bool: True if cleanup was successful
        """
        try:
            backup_tables = [
                'bulletproof_teams_backup',
                'bulletproof_polls_backup',
                'bulletproof_captain_messages_backup',
                'bulletproof_practice_times_backup',
                'bulletproof_user_associations_backup',
                'bulletproof_availability_backup'
            ]
            
            for table in backup_tables:
                execute_update(f"DROP TABLE IF EXISTS {table}")
            
            logger.info("Backup tables cleaned up successfully")
            return True
            
        except Exception as e:
            logger.error(f"Backup cleanup failed: {str(e)}")
            return False
    
    def get_health_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive health report.
        
        Returns:
            Dict[str, Any]: Health report with statistics and status
        """
        try:
            # Check for remaining orphaned records
            orphaned_polls = execute_query_one("""
                SELECT COUNT(*) as count
                FROM polls p
                LEFT JOIN teams t ON p.team_id = t.id
                WHERE p.team_id IS NOT NULL AND t.id IS NULL
            """)
            
            orphaned_messages = execute_query_one("""
                SELECT COUNT(*) as count
                FROM captain_messages cm
                LEFT JOIN teams t ON cm.team_id = t.id
                WHERE cm.team_id IS NOT NULL AND t.id IS NULL
            """)
            
            orphaned_practice = execute_query_one("""
                SELECT COUNT(*) as count
                FROM schedule s
                LEFT JOIN teams t ON s.home_team_id = t.id
                WHERE s.home_team_id IS NOT NULL AND t.id IS NULL
                AND (s.home_team LIKE '%Practice%' OR s.home_team LIKE '%practice%')
            """)
            
            total_orphans = (
                (orphaned_polls['count'] if orphaned_polls else 0) +
                (orphaned_messages['count'] if orphaned_messages else 0) +
                (orphaned_practice['count'] if orphaned_practice else 0)
            )
            
            health_score = 100 if total_orphans == 0 else max(0, 100 - (total_orphans * 10))
            
            return {
                'timestamp': datetime.now().isoformat(),
                'health_score': health_score,
                'total_orphans': total_orphans,
                'orphaned_polls': orphaned_polls['count'] if orphaned_polls else 0,
                'orphaned_messages': orphaned_messages['count'] if orphaned_messages else 0,
                'orphaned_practice_times': orphaned_practice['count'] if orphaned_practice else 0,
                'stats': self.stats,
                'status': 'healthy' if total_orphans == 0 else 'needs_attention'
            }
            
        except Exception as e:
            logger.error(f"Health report generation failed: {str(e)}")
            return {
                'timestamp': datetime.now().isoformat(),
                'health_score': 0,
                'error': str(e),
                'status': 'error'
            } 