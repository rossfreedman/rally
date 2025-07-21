#!/usr/bin/env python3
"""
Session Refresh Service for ETL
===============================

This service handles automatic session refresh after ETL imports when 
league IDs change, preventing users from losing their league context
and requiring manual logout/login or league switching.

Key Features:
- Detects league ID changes during ETL
- Creates session refresh signals for active users  
- Provides API endpoints for automatic session refresh
- Maintains session continuity across ETL imports

Usage:
    # During ETL (called automatically)
    session_refresh = SessionRefreshService()
    session_refresh.create_refresh_signals_after_etl()
    
    # In API routes (automatic detection)
    if session_refresh.should_refresh_session(user_email):
        refreshed_session = session_refresh.refresh_user_session(user_email)
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from database_utils import execute_query, execute_query_one
import logging

logger = logging.getLogger(__name__)

class SessionRefreshService:
    """Service for managing session refresh after ETL imports"""
    
    @staticmethod
    def detect_league_id_changes(cursor) -> List[Dict[str, Any]]:
        """
        Detect league ID changes by comparing backup with current leagues
        
        Returns:
            List of league mappings: [{"old_id": int, "new_id": int, "league_name": str}, ...]
        """
        try:
            # Check if league backup exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'etl_backup_user_league_contexts'
                )
            """)
            
            if not cursor.fetchone()[0]:
                logger.info("No league context backup found - no league ID changes to detect")
                return []
            
            # Find league ID changes by comparing backup with current leagues
            cursor.execute("""
                SELECT DISTINCT
                    backup.original_league_id as old_id,
                    current_league.id as new_id,
                    current_league.league_name,
                    backup.original_league_name
                FROM etl_backup_user_league_contexts backup
                JOIN leagues current_league ON backup.original_league_name = current_league.league_name
                WHERE backup.original_league_id != current_league.id
                ORDER BY current_league.league_name
            """)
            
            changes = cursor.fetchall()
            
            if changes:
                logger.info(f"Detected {len(changes)} league ID changes:")
                for change in changes:
                    logger.info(f"  {change[2]}: {change[0]} → {change[1]}")
            else:
                logger.info("No league ID changes detected")
            
            return [
                {
                    "old_id": change[0],
                    "new_id": change[1], 
                    "league_name": change[2],
                    "original_league_name": change[3]
                }
                for change in changes
            ]
            
        except Exception as e:
            logger.error(f"Error detecting league ID changes: {str(e)}")
            return []
    
    @staticmethod
    def create_refresh_signals_after_etl(cursor, league_changes: Optional[List[Dict]] = None) -> int:
        """
        Create refresh signals for users affected by league ID changes
        
        Args:
            cursor: Database cursor
            league_changes: Optional list of league changes (if None, will detect automatically)
            
        Returns:
            Number of refresh signals created
        """
        try:
            if league_changes is None:
                league_changes = SessionRefreshService.detect_league_id_changes(cursor)
            
            if not league_changes:
                logger.info("No league changes detected - no refresh signals needed")
                return 0
            
            # Create refresh signals table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_session_refresh_signals (
                    user_id INTEGER PRIMARY KEY,
                    email VARCHAR(255) NOT NULL,
                    old_league_id INTEGER,
                    new_league_id INTEGER,
                    league_name VARCHAR(255),
                    refresh_reason VARCHAR(255) DEFAULT 'etl_league_id_change',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    refreshed_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
                    is_refreshed BOOLEAN DEFAULT FALSE
                )
            """)
            
            # Create indexes separately (PostgreSQL syntax)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_refresh_email 
                ON user_session_refresh_signals(email)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_refresh_refreshed 
                ON user_session_refresh_signals(is_refreshed)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_refresh_created 
                ON user_session_refresh_signals(created_at)
            """)
            
            signals_created = 0
            
            for change in league_changes:
                old_id = change["old_id"]
                new_id = change["new_id"]
                league_name = change["league_name"]
                
                # Find users affected by this league change
                cursor.execute("""
                    SELECT DISTINCT u.id, u.email
                    FROM users u
                    WHERE u.league_context = %s
                """, (new_id,))  # Users now have the new league ID after restoration
                
                affected_users = cursor.fetchall()
                
                for user in affected_users:
                    user_id, email = user
                    
                    # Create refresh signal
                    cursor.execute("""
                        INSERT INTO user_session_refresh_signals 
                        (user_id, email, old_league_id, new_league_id, league_name)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (user_id) DO UPDATE SET
                            old_league_id = EXCLUDED.old_league_id,
                            new_league_id = EXCLUDED.new_league_id,
                            league_name = EXCLUDED.league_name,
                            created_at = NOW(),
                            is_refreshed = FALSE,
                            refreshed_at = NULL
                    """, (user_id, email, old_id, new_id, league_name))
                    
                    signals_created += 1
            
            if signals_created > 0:
                logger.info(f"Created {signals_created} session refresh signals for ETL league changes")
            
            return signals_created
            
        except Exception as e:
            logger.error(f"Error creating refresh signals: {str(e)}")
            return 0
    
    @staticmethod
    def should_refresh_session(user_email: str) -> bool:
        """
        Check if a user's session should be refreshed due to ETL changes
        
        Args:
            user_email: User's email address
            
        Returns:
            True if session should be refreshed, False otherwise
        """
        try:
            result = execute_query_one("""
                SELECT user_id, old_league_id, new_league_id, league_name
                FROM user_session_refresh_signals
                WHERE email = %s AND is_refreshed = FALSE
                AND created_at > NOW() - INTERVAL '24 hours'
            """, [user_email])
            
            return result is not None
            
        except Exception as e:
            logger.error(f"Error checking refresh status for {user_email}: {str(e)}")
            return False
    
    @staticmethod
    def refresh_user_session(user_email: str) -> Optional[Dict[str, Any]]:
        """
        Refresh a user's session with updated league context
        
        Args:
            user_email: User's email address
            
        Returns:
            Updated session data or None if refresh failed
        """
        try:
            from app.services.session_service import get_session_data_for_user
            
            # Get refresh signal info
            signal_info = execute_query_one("""
                SELECT user_id, old_league_id, new_league_id, league_name
                FROM user_session_refresh_signals
                WHERE email = %s AND is_refreshed = FALSE
            """, [user_email])
            
            if not signal_info:
                logger.info(f"No refresh signal found for {user_email}")
                return None
            
            # Get fresh session data from database (this will include updated league context)
            fresh_session_data = get_session_data_for_user(user_email)
            
            if fresh_session_data:
                # Mark refresh signal as completed
                execute_query("""
                    UPDATE user_session_refresh_signals
                    SET is_refreshed = TRUE, refreshed_at = NOW()
                    WHERE email = %s
                """, [user_email])
                
                logger.info(f"Successfully refreshed session for {user_email}: "
                          f"{signal_info['league_name']} (ID: {signal_info['old_league_id']} → {signal_info['new_league_id']})")
                
                return fresh_session_data
            else:
                logger.error(f"Failed to get fresh session data for {user_email}")
                return None
                
        except Exception as e:
            logger.error(f"Error refreshing session for {user_email}: {str(e)}")
            return None
    
    @staticmethod
    def get_refresh_status() -> Dict[str, Any]:
        """
        Get status of session refresh operations
        
        Returns:
            Dict with refresh statistics
        """
        try:
            # Check if refresh signals table exists
            table_exists = execute_query_one("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_name = 'user_session_refresh_signals'
            """)
            
            if not table_exists or table_exists[0] == 0:
                return {
                    "signals_table_exists": False,
                    "total_signals": 0,
                    "pending_refreshes": 0,
                    "completed_refreshes": 0,
                    "recent_signals": []
                }
            
            # Get refresh statistics
            total_signals = execute_query_one("""
                SELECT COUNT(*) FROM user_session_refresh_signals
            """)[0] or 0
            
            pending_refreshes = execute_query_one("""
                SELECT COUNT(*) FROM user_session_refresh_signals
                WHERE is_refreshed = FALSE
            """)[0] or 0
            
            completed_refreshes = execute_query_one("""
                SELECT COUNT(*) FROM user_session_refresh_signals
                WHERE is_refreshed = TRUE
            """)[0] or 0
            
            # Get recent refresh signals
            recent_signals = execute_query("""
                SELECT email, league_name, old_league_id, new_league_id, 
                       is_refreshed, created_at, refreshed_at
                FROM user_session_refresh_signals
                ORDER BY created_at DESC
                LIMIT 10
            """) or []
            
            return {
                "signals_table_exists": True,
                "total_signals": total_signals,
                "pending_refreshes": pending_refreshes,
                "completed_refreshes": completed_refreshes,
                "recent_signals": [dict(signal) for signal in recent_signals]
            }
            
        except Exception as e:
            logger.error(f"Error getting refresh status: {str(e)}")
            return {
                "signals_table_exists": False,
                "error": str(e)
            }
    
    @staticmethod
    def cleanup_old_refresh_signals(days_old: int = 7) -> int:
        """
        Clean up old refresh signals
        
        Args:
            days_old: Number of days to keep signals (default: 7)
            
        Returns:
            Number of signals cleaned up
        """
        try:
            result = execute_query("""
                DELETE FROM user_session_refresh_signals
                WHERE created_at < NOW() - INTERVAL '%s days'
                AND is_refreshed = TRUE
            """, [days_old])
            
            # Get rowcount from the execute_query result
            cleaned_count = 0  # execute_query doesn't return rowcount, so we'll estimate
            
            logger.info(f"Cleaned up refresh signals older than {days_old} days")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up refresh signals: {str(e)}")
            return 0

def integrate_with_etl_wrapper(etl_wrapper_instance):
    """
    Integration function to add session refresh to ETL wrapper
    Call this after ETL completion to create refresh signals
    """
    try:
        with etl_wrapper_instance.get_connection() as conn:
            cursor = conn.cursor()
            
            # Detect league changes and create refresh signals
            session_refresh = SessionRefreshService()
            signals_created = session_refresh.create_refresh_signals_after_etl(cursor)
            
            if signals_created > 0:
                etl_wrapper_instance.log(f"🔄 Created {signals_created} session refresh signals for affected users")
                etl_wrapper_instance.log("✅ Users will get automatic session refresh on next page load")
            else:
                etl_wrapper_instance.log("ℹ️  No session refresh signals needed (no league ID changes)")
            
            conn.commit()
            return signals_created
            
    except Exception as e:
        etl_wrapper_instance.log(f"❌ Session refresh integration failed: {str(e)}")
        return 0 