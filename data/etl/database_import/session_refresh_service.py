#!/usr/bin/env python3
"""
Session Refresh Service
=======================

This service manages automatic session refresh after ETL imports when league IDs change.
It handles creation of refresh signals, checking for refresh needs, and updating user sessions.

Key Functions:
- should_refresh_session(): Check if user needs session refresh
- refresh_user_session(): Update session with fresh database data  
- create_refresh_signals_after_etl(): Flag users needing refresh after ETL
- cleanup_old_refresh_signals(): Remove old completed refresh signals
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import threading

from database_config import get_db
from app.services.session_service import get_session_data_for_user

logger = logging.getLogger(__name__)

# Thread lock to prevent concurrent database operations
_session_refresh_lock = threading.Lock()


class SessionRefreshService:
    """Service for managing automatic session refresh after ETL imports"""
    
    @staticmethod
    def should_refresh_session(user_email: str) -> bool:
        """
        Check if user's session should be refreshed
        
        Args:
            user_email: User's email address
            
        Returns:
            True if user has pending refresh signal, False otherwise
        """
        # Use thread lock to prevent concurrent database operations
        with _session_refresh_lock:
            try:
                with get_db() as conn:
                    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                        # Check for pending refresh signals
                        cursor.execute("""
                        SELECT user_id, created_at 
                        FROM user_session_refresh_signals 
                        WHERE email = %s AND is_refreshed = FALSE
                        ORDER BY created_at DESC
                        LIMIT 1
                    """, (user_email,))
                        
                        result = cursor.fetchone()
                        
                        if result:
                            logger.info(f"Found pending refresh signal for {user_email}")
                            return True
                            
                        return False
                        
            except psycopg2.Error as e:
                # Handle specific database errors
                if "cursor already closed" in str(e):
                    logger.warning(f"Database cursor closed for {user_email}, retrying...")
                    # Return False to avoid infinite retry loops
                    return False
                elif "connection" in str(e).lower():
                    logger.error(f"Database connection error for {user_email}: {str(e)}")
                    return False
                else:
                    logger.error(f"Database error checking refresh status for {user_email}: {str(e)}")
                    return False
            except Exception as e:
                logger.error(f"Unexpected error checking refresh status for {user_email}: {str(e)}")
                return False
    
    @staticmethod
    def refresh_user_session(user_email: str) -> Optional[Dict[str, Any]]:
        """
        Refresh user's session with updated data from database
        
        Args:
            user_email: User's email address
            
        Returns:
            Updated session data dict or None if failed
        """
        # Use thread lock to prevent concurrent database operations
        with _session_refresh_lock:
            try:
                # Get fresh session data from database
                fresh_session_data = get_session_data_for_user(user_email)
                
                if not fresh_session_data:
                    logger.warning(f"Could not get fresh session data for {user_email}")
                    return None
                
                # Mark refresh signal as completed
                with get_db() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            UPDATE user_session_refresh_signals 
                            SET is_refreshed = TRUE, refreshed_at = NOW()
                            WHERE email = %s AND is_refreshed = FALSE
                        """, (user_email,))
                        conn.commit()
                        
                        affected_rows = cursor.rowcount
                        if affected_rows > 0:
                            logger.info(f"Marked {affected_rows} refresh signals as completed for {user_email}")
                
                logger.info(f"Successfully refreshed session for {user_email}")
                return fresh_session_data
                
            except psycopg2.Error as e:
                # Handle specific database errors
                if "cursor already closed" in str(e):
                    logger.warning(f"Database cursor closed during refresh for {user_email}")
                    return None
                elif "connection" in str(e).lower():
                    logger.error(f"Database connection error during refresh for {user_email}: {str(e)}")
                    return None
                else:
                    logger.error(f"Database error refreshing session for {user_email}: {str(e)}")
                    return None
            except Exception as e:
                logger.error(f"Unexpected error refreshing session for {user_email}: {str(e)}")
                return None
    
    @staticmethod
    def get_refresh_status() -> Dict[str, Any]:
        """
        Get system-wide refresh status for monitoring
        
        Returns:
            Dict with refresh signal counts and statistics
        """
        # Use thread lock to prevent concurrent database operations
        with _session_refresh_lock:
            try:
                with get_db() as conn:
                    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                        # Get counts of refresh signals
                        cursor.execute("""
                        SELECT 
                            COUNT(*) as total_signals,
                            COUNT(CASE WHEN is_refreshed = FALSE THEN 1 END) as pending_refreshes,
                            COUNT(CASE WHEN is_refreshed = TRUE THEN 1 END) as completed_refreshes,
                            MIN(created_at) as oldest_signal,
                            MAX(created_at) as newest_signal
                        FROM user_session_refresh_signals
                    """)
                        
                        stats = cursor.fetchone()
                        
                        return {
                            "total_signals": stats["total_signals"] if stats else 0,
                            "pending_refreshes": stats["pending_refreshes"] if stats else 0,
                            "completed_refreshes": stats["completed_refreshes"] if stats else 0,
                            "oldest_signal": stats["oldest_signal"].isoformat() if stats and stats["oldest_signal"] else None,
                            "newest_signal": stats["newest_signal"].isoformat() if stats and stats["newest_signal"] else None
                        }
                        
            except psycopg2.Error as e:
                # Handle specific database errors
                if "cursor already closed" in str(e):
                    logger.warning("Database cursor closed while getting refresh status")
                    return {"error": "Database connection issue"}
                elif "connection" in str(e).lower():
                    logger.error(f"Database connection error getting refresh status: {str(e)}")
                    return {"error": "Database connection issue"}
                else:
                    logger.error(f"Database error getting refresh status: {str(e)}")
                    return {"error": str(e)}
            except Exception as e:
                logger.error(f"Unexpected error getting refresh status: {str(e)}")
                return {"error": str(e)}
    
    @staticmethod
    def cleanup_old_refresh_signals(days_old: int = 7) -> int:
        """
        Clean up old completed refresh signals
        
        Args:
            days_old: Remove signals older than this many days (default: 7)
            
        Returns:
            Number of signals cleaned up
        """
        # Use thread lock to prevent concurrent database operations
        with _session_refresh_lock:
            try:
                cutoff_date = datetime.now() - timedelta(days=days_old)
                
                with get_db() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("""
                    DELETE FROM user_session_refresh_signals 
                    WHERE is_refreshed = TRUE 
                    AND refreshed_at < %s
                """, (cutoff_date,))
                
                cleaned_count = cursor.rowcount
                conn.commit()
                
                if cleaned_count > 0:
                    logger.info(f"Cleaned up {cleaned_count} old refresh signals (older than {days_old} days)")
                
                return cleaned_count
                
            except psycopg2.Error as e:
                # Handle specific database errors
                if "cursor already closed" in str(e):
                    logger.warning(f"Database cursor closed during cleanup for {days_old} days old signals")
                    return 0
                elif "connection" in str(e).lower():
                    logger.error(f"Database connection error during cleanup for {days_old} days old signals: {str(e)}")
                    return 0
                else:
                    logger.error(f"Database error cleaning up refresh signals: {str(e)}")
                    return 0
            except Exception as e:
                logger.error(f"Unexpected error cleaning up refresh signals: {str(e)}")
                return 0
    
    @staticmethod
    def create_refresh_signals_after_etl(cursor, league_changes: List[Dict[str, Any]] = None) -> int:
        """
        Create refresh signals for users affected by league ID changes after ETL
        
        Args:
            cursor: Database cursor (for transaction consistency)
            league_changes: Optional list of league ID changes detected
            
        Returns:
            Number of refresh signals created
        """
        # Use thread lock to prevent concurrent database operations
        with _session_refresh_lock:
            try:
                signals_created = 0
                
                # If no specific league changes provided, create signals for all active users
                # This is a fallback to ensure users get refreshed after any ETL
                if not league_changes:
                    logger.info("No specific league changes provided, creating refresh signals for all active users")
                    
                    cursor.execute("""
                        INSERT INTO user_session_refresh_signals 
                        (user_id, email, refresh_reason, created_at, is_refreshed)
                        SELECT DISTINCT 
                            u.id,
                            u.email,
                            'etl_general_refresh',
                            NOW(),
                            FALSE
                        FROM users u 
                        WHERE u.email IS NOT NULL 
                        AND u.is_active = TRUE
                        AND NOT EXISTS (
                            SELECT 1 FROM user_session_refresh_signals s 
                            WHERE s.email = u.email AND s.is_refreshed = FALSE
                        )
                    """)
                    
                    signals_created = cursor.rowcount
                    logger.info(f"Created {signals_created} general refresh signals for active users")
                    
                else:
                    # Create specific signals for users affected by league changes
                    for change in league_changes:
                        old_league_id = change.get('old_league_id')
                        new_league_id = change.get('new_league_id') 
                        league_name = change.get('league_name', 'Unknown')
                        
                        if not old_league_id or not new_league_id:
                            continue
                            
                        cursor.execute("""
                            INSERT INTO user_session_refresh_signals 
                            (user_id, email, old_league_id, new_league_id, league_name, refresh_reason, created_at, is_refreshed)
                            SELECT DISTINCT 
                                u.id,
                                u.email,
                                %s,
                                %s,
                                %s,
                                'etl_league_id_change',
                                NOW(),
                                FALSE
                            FROM users u 
                            WHERE u.league_context = %s
                            AND u.email IS NOT NULL
                            AND NOT EXISTS (
                                SELECT 1 FROM user_session_refresh_signals s 
                                WHERE s.email = u.email AND s.is_refreshed = FALSE
                            )
                        """, (old_league_id, new_league_id, league_name, new_league_id))
                        
                        change_signals = cursor.rowcount
                        signals_created += change_signals
                        
                        logger.info(f"Created {change_signals} refresh signals for league {league_name} change ({old_league_id} → {new_league_id})")
                
                logger.info(f"Total refresh signals created: {signals_created}")
                return signals_created
                
            except psycopg2.Error as e:
                # Handle specific database errors
                if "cursor already closed" in str(e):
                    logger.warning(f"Database cursor closed during ETL refresh signal creation")
                    return 0
                elif "connection" in str(e).lower():
                    logger.error(f"Database connection error during ETL refresh signal creation: {str(e)}")
                    return 0
                else:
                    logger.error(f"Database error creating refresh signals after ETL: {str(e)}")
                    return 0
            except Exception as e:
                logger.error(f"Unexpected error creating refresh signals after ETL: {str(e)}")
                return 0
    
    @staticmethod
    def detect_league_id_changes(cursor) -> List[Dict[str, Any]]:
        """
        Detect league ID changes by comparing backup data with current leagues
        
        Args:
            cursor: Database cursor
            
        Returns:
            List of league change dictionaries
        """
        # Use thread lock to prevent concurrent database operations
        with _session_refresh_lock:
            try:
                # Check if backup table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'etl_backup_user_league_contexts'
                    )
                """)
                
                backup_exists = cursor.fetchone()[0]
                
                if not backup_exists:
                    logger.warning("No ETL backup table found, cannot detect league ID changes")
                    return []
                
                # Find league ID changes
                cursor.execute("""
                    SELECT DISTINCT
                        backup.original_league_id as old_league_id,
                        current_league.id as new_league_id,
                        current_league.league_name
                    FROM etl_backup_user_league_contexts backup
                    JOIN leagues current_league ON backup.original_league_name = current_league.league_name
                    WHERE backup.original_league_id != current_league.id
                """)
                
                changes = cursor.fetchall()
                
                if changes:
                    logger.info(f"Detected {len(changes)} league ID changes")
                    for change in changes:
                        logger.info(f"League '{change[2]}': {change[0]} → {change[1]}")
                else:
                    logger.info("No league ID changes detected")
                
                return [
                    {
                        'old_league_id': change[0],
                        'new_league_id': change[1], 
                        'league_name': change[2]
                    }
                    for change in changes
                ]
                
            except psycopg2.Error as e:
                # Handle specific database errors
                if "cursor already closed" in str(e):
                    logger.warning("Database cursor closed while detecting league ID changes")
                    return []
                elif "connection" in str(e).lower():
                    logger.error(f"Database connection error detecting league ID changes: {str(e)}")
                    return []
                else:
                    logger.error(f"Database error detecting league ID changes: {str(e)}")
                    return []
            except Exception as e:
                logger.error(f"Unexpected error detecting league ID changes: {str(e)}")
                return []