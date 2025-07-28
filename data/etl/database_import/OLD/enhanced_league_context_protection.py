#!/usr/bin/env python3
"""
Enhanced League Context Protection for ETL
==========================================

This module provides enhanced league context backup and restoration functionality
to prevent users from losing their league context during ETL imports.

The issue: ETL clears and recreates the leagues table with new IDs, but user 
league_context fields still point to old, non-existent league IDs.

The solution: Backup league contexts before ETL, then restore/repair them after.
"""

import sys
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
sys.path.insert(0, project_root)

from database_config import get_db


def backup_user_league_contexts(cursor, logger=None) -> int:
    """
    Create backup of user league contexts before ETL process
    
    Returns:
        int: Number of league contexts backed up
    """
    def log(message):
        if logger:
            logger.log(message)
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    
    try:
        # Create backup table
        cursor.execute("DROP TABLE IF EXISTS etl_backup_user_league_contexts")
        cursor.execute("""
            CREATE TABLE etl_backup_user_league_contexts AS
            SELECT 
                u.id as user_id,
                u.email,
                u.first_name,
                u.last_name,
                u.league_context as original_league_context,
                l.league_name as original_league_name,
                l.id as original_league_id
            FROM users u
            LEFT JOIN leagues l ON u.league_context = l.id
            WHERE u.league_context IS NOT NULL
        """)
        
        # Get count of backed up contexts
        cursor.execute("SELECT COUNT(*) FROM etl_backup_user_league_contexts")
        backup_count = cursor.fetchone()[0]
        
        log(f"💾 Backed up {backup_count} user league contexts")
        return backup_count
        
    except Exception as e:
        log(f"❌ League context backup failed: {str(e)}")
        raise


def restore_user_league_contexts(cursor, logger=None) -> Dict[str, int]:
    """
    Restore user league contexts after ETL process using intelligent mapping
    
    Returns:
        Dict with restoration statistics
    """
    def log(message):
        if logger:
            logger.log(message)
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    
    try:
        # Check if backup exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_name = 'etl_backup_user_league_contexts'
        """)
        
        if cursor.fetchone()[0] == 0:
            log("⚠️ No league context backup found - skipping restoration")
            return {"restored": 0, "failed": 0, "already_valid": 0}
        
        # Get all users who need restoration
        cursor.execute("""
            SELECT 
                b.user_id,
                b.email,
                b.original_league_name,
                u.league_context as current_league_context
            FROM etl_backup_user_league_contexts b
            JOIN users u ON b.user_id = u.id
        """)
        
        users_to_restore = cursor.fetchall()
        log(f"🔍 Found {len(users_to_restore)} users with league context backup")
        
        restored_count = 0
        failed_count = 0
        already_valid_count = 0
        
        for user in users_to_restore:
            user_id = user[0]
            email = user[1]
            original_league_name = user[2]
            current_league_context = user[3]
            
            # Check if current league context is valid
            if current_league_context:
                cursor.execute("SELECT id FROM leagues WHERE id = %s", (current_league_context,))
                if cursor.fetchone():
                    already_valid_count += 1
                    continue
            
            # Find new league ID by name
            cursor.execute("SELECT id FROM leagues WHERE league_name = %s", (original_league_name,))
            new_league = cursor.fetchone()
            
            if new_league:
                new_league_id = new_league[0]
                
                # Update user's league context
                cursor.execute("""
                    UPDATE users 
                    SET league_context = %s 
                    WHERE id = %s
                """, (new_league_id, user_id))
                
                restored_count += 1
                log(f"✅ Restored {email}: {original_league_name} → ID {new_league_id}")
            else:
                # Try to find a reasonable default league for this user
                # Look up their player associations to find active leagues
                cursor.execute("""
                    SELECT DISTINCT l.id, l.league_name, COUNT(ms.id) as match_count
                    FROM user_player_associations upa
                    JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                    JOIN leagues l ON p.league_id = l.id
                    LEFT JOIN match_scores ms ON (
                        (ms.home_player_1_id = p.tenniscores_player_id OR 
                         ms.home_player_2_id = p.tenniscores_player_id OR 
                         ms.away_player_1_id = p.tenniscores_player_id OR 
                         ms.away_player_2_id = p.tenniscores_player_id) AND
                        ms.match_date >= CURRENT_DATE - INTERVAL '1 year'
                    )
                    WHERE upa.user_id = %s
                    GROUP BY l.id, l.league_name
                    ORDER BY match_count DESC, l.id
                    LIMIT 1
                """, (user_id,))
                
                fallback_league = cursor.fetchone()
                
                if fallback_league:
                    fallback_league_id = fallback_league[0]
                    fallback_league_name = fallback_league[1]
                    
                    cursor.execute("""
                        UPDATE users 
                        SET league_context = %s 
                        WHERE id = %s
                    """, (fallback_league_id, user_id))
                    
                    restored_count += 1
                    log(f"🔄 Fallback restored {email}: {original_league_name} → {fallback_league_name} (ID {fallback_league_id})")
                else:
                    failed_count += 1
                    log(f"❌ Failed to restore {email}: No matching league found for '{original_league_name}'")
        
        stats = {
            "restored": restored_count,
            "failed": failed_count,
            "already_valid": already_valid_count,
            "total_processed": len(users_to_restore)
        }
        
        log(f"📊 League context restoration: {restored_count} restored, {failed_count} failed, {already_valid_count} already valid")
        return stats
        
    except Exception as e:
        log(f"❌ League context restoration failed: {str(e)}")
        raise


def auto_fix_broken_league_contexts(cursor, logger=None) -> int:
    """
    Find and fix users with broken league contexts and missing associations
    
    This enhanced function:
    1. Creates missing user_player_associations for users who should have them
    2. Fixes users with broken league contexts (pointing to non-existent league IDs)
    3. Sets league contexts for users with NULL contexts who have associations
    
    Returns:
        int: Number of users fixed (associations created + contexts fixed)
    """
    def log(message):
        if logger:
            logger.log(message)
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    
    try:
        total_fixed = 0
        
        # STEP 1: Create missing user_player_associations for users who should have them
        log("🔍 Step 1: Finding users missing player associations...")
        
        cursor.execute("""
            SELECT 
                u.id,
                u.email,
                u.first_name,
                u.last_name,
                u.tenniscores_player_id
            FROM users u
            LEFT JOIN user_player_associations upa ON u.id = upa.user_id
            WHERE u.tenniscores_player_id IS NOT NULL
            AND upa.user_id IS NULL
        """)
        
        users_missing_associations = cursor.fetchall()
        
        if users_missing_associations:
            log(f"🔗 Found {len(users_missing_associations)} users missing player associations")
            
            for user in users_missing_associations:
                user_id = user[0]
                email = user[1]
                first_name = user[2]
                last_name = user[3]
                player_id = user[4]
                
                # Verify the player exists before creating association
                cursor.execute("""
                    SELECT tenniscores_player_id, first_name, last_name, league_id
                    FROM players 
                    WHERE tenniscores_player_id = %s
                """, [player_id])
                
                player_exists = cursor.fetchone()
                
                if player_exists:
                    # Create the missing association
                    # First check if this player is already associated with another user
                    cursor.execute("""
                        SELECT user_id FROM user_player_associations 
                        WHERE tenniscores_player_id = %s
                    """, [player_id])
                    
                    existing_association = cursor.fetchone()
                    
                    if existing_association:
                        log(f"⚠️  Player {player_id} already associated with user {existing_association[0]}")
                        continue
                    
                    cursor.execute("""
                        INSERT INTO user_player_associations (user_id, tenniscores_player_id, created_at)
                        VALUES (%s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (user_id, tenniscores_player_id) DO NOTHING
                    """, [user_id, player_id])
                    
                    if cursor.rowcount > 0:
                        total_fixed += 1
                        log(f"🔗 Created association: {first_name} {last_name} → {player_id} (League {player_exists[3]})")
                else:
                    log(f"⚠️  Player {player_id} not found for {first_name} {last_name}")
        
        # STEP 2: Find users with broken league contexts
        log("🔍 Step 2: Finding users with broken league contexts...")
        
        cursor.execute("""
            SELECT 
                u.id,
                u.email,
                u.first_name,
                u.last_name,
                u.league_context
            FROM users u
            LEFT JOIN leagues l ON u.league_context = l.id
            WHERE u.league_context IS NOT NULL 
            AND l.id IS NULL
        """)
        
        broken_users = cursor.fetchall()
        
        if broken_users:
            log(f"🔧 Found {len(broken_users)} users with broken league contexts")
            
            for user in broken_users:
                user_id = user[0]
                email = user[1]
                broken_league_id = user[4]
                
                # Find their best league using player associations
                cursor.execute("""
                    SELECT 
                        l.id,
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
                         ms.away_player_2_id = p.tenniscores_player_id) AND
                        ms.match_date >= CURRENT_DATE - INTERVAL '1 year'
                    )
                    WHERE upa.user_id = %s
                    GROUP BY l.id, l.league_name, has_team
                    ORDER BY 
                        has_team DESC,           -- Prefer leagues where they have team assignment
                        match_count DESC,        -- Then by recent match activity
                        last_match_date DESC,    -- Then by most recent activity
                        l.id                     -- Finally by league ID for consistency
                    LIMIT 1
                """, (user_id,))
                
                best_league = cursor.fetchone()
                
                if best_league:
                    new_league_id = best_league[0]
                    league_name = best_league[1]
                    match_count = best_league[2] or 0
                    
                    # Update the user's league context
                    cursor.execute("""
                        UPDATE users 
                        SET league_context = %s 
                        WHERE id = %s
                    """, (new_league_id, user_id))
                    
                    total_fixed += 1
                    log(f"🔧 Fixed {email}: {broken_league_id} → {league_name} (ID {new_league_id}, {match_count} matches)")
                else:
                    # Set to NULL if no associations found
                    cursor.execute("""
                        UPDATE users 
                        SET league_context = NULL 
                        WHERE id = %s
                    """, (user_id,))
                    
                    log(f"⚠️ Cleared broken context for {email}: {broken_league_id} → NULL (no associations)")
        
        # STEP 3: Find users with NULL league contexts who now have associations
        log("🔍 Step 3: Finding users with NULL league contexts who have associations...")
        
        cursor.execute("""
            SELECT DISTINCT
                u.id,
                u.email,
                u.first_name,
                u.last_name
            FROM users u
            JOIN user_player_associations upa ON u.id = upa.user_id
            WHERE u.league_context IS NULL
        """)
        
        null_context_users = cursor.fetchall()
        
        if null_context_users:
            log(f"🔧 Found {len(null_context_users)} users with NULL contexts who have associations")
            
            for user in null_context_users:
                user_id = user[0]
                email = user[1]
                
                # Find their best league using player associations
                cursor.execute("""
                    SELECT 
                        l.id,
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
                         ms.away_player_2_id = p.tenniscores_player_id) AND
                        ms.match_date >= CURRENT_DATE - INTERVAL '1 year'
                    )
                    WHERE upa.user_id = %s
                    GROUP BY l.id, l.league_name, has_team
                    ORDER BY 
                        has_team DESC,           -- Prefer leagues where they have team assignment
                        match_count DESC,        -- Then by recent match activity
                        last_match_date DESC,    -- Then by most recent activity
                        l.id                     -- Finally by league ID for consistency
                    LIMIT 1
                """, (user_id,))
                
                best_league = cursor.fetchone()
                
                if best_league:
                    new_league_id = best_league[0]
                    league_name = best_league[1]
                    match_count = best_league[2] or 0
                    
                    # Update the user's league context and player ID
                    cursor.execute("""
                        UPDATE users 
                        SET league_context = %s
                        WHERE id = %s
                    """, (new_league_id, user_id))
                    
                    total_fixed += 1
                    log(f"✅ Set context for {email}: NULL → {league_name} (ID {new_league_id}, {match_count} matches)")
        
        # STEP 4: Fix league_id inconsistency (sync league_id = league_context)
        log("🔍 Step 4: Fixing league_id inconsistency...")
        
        cursor.execute("""
            UPDATE users 
            SET league_id = league_context
            WHERE league_context IS NOT NULL
            AND (league_id != league_context OR league_id IS NULL)
        """)
        
        sync_count = cursor.rowcount
        if sync_count > 0:
            total_fixed += sync_count
            log(f"🔄 Synced league_id = league_context for {sync_count} users")
        
        # Clear orphaned league_id values
        cursor.execute("""
            UPDATE users 
            SET league_id = NULL
            WHERE league_context IS NULL AND league_id IS NOT NULL
        """)
        
        clear_count = cursor.rowcount
        if clear_count > 0:
            total_fixed += clear_count
            log(f"🧹 Cleared orphaned league_id for {clear_count} users")
        
        if total_fixed > 0:
            log(f"🎉 Total users fixed: {total_fixed}")
        else:
            log("✅ No users needed fixing")
            
        return total_fixed
        
    except Exception as e:
        log(f"❌ Auto-fix broken league contexts failed: {str(e)}")
        raise


def validate_league_context_health(cursor, logger=None) -> Dict[str, int]:
    """
    Validate the health of league contexts after ETL
    
    Returns:
        Dict with health statistics
    """
    def log(message):
        if logger:
            logger.log(message)
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    
    try:
        # Count users with valid league contexts
        cursor.execute("""
            SELECT COUNT(*) 
            FROM users u
            JOIN leagues l ON u.league_context = l.id
            WHERE u.league_context IS NOT NULL
        """)
        valid_contexts = cursor.fetchone()[0]
        
        # Count users with broken league contexts
        cursor.execute("""
            SELECT COUNT(*) 
            FROM users u
            LEFT JOIN leagues l ON u.league_context = l.id
            WHERE u.league_context IS NOT NULL 
            AND l.id IS NULL
        """)
        broken_contexts = cursor.fetchone()[0]
        
        # Count users with NULL league contexts who should have one
        cursor.execute("""
            SELECT COUNT(DISTINCT u.id)
            FROM users u
            JOIN user_player_associations upa ON u.id = upa.user_id
            WHERE u.league_context IS NULL
        """)
        missing_contexts = cursor.fetchone()[0]
        
        # Total users with associations
        cursor.execute("""
            SELECT COUNT(DISTINCT u.id)
            FROM users u
            JOIN user_player_associations upa ON u.id = upa.user_id
        """)
        total_users_with_associations = cursor.fetchone()[0]
        
        health_stats = {
            "valid_contexts": valid_contexts,
            "broken_contexts": broken_contexts,
            "missing_contexts": missing_contexts,
            "total_users_with_associations": total_users_with_associations,
            "health_percentage": (valid_contexts / max(total_users_with_associations, 1)) * 100
        }
        
        is_healthy = broken_contexts == 0 and missing_contexts < (total_users_with_associations * 0.1)  # Allow 10% missing
        
        if is_healthy:
            log(f"✅ League context health: {valid_contexts} valid, {broken_contexts} broken, {missing_contexts} missing ({health_stats['health_percentage']:.1f}% healthy)")
        else:
            log(f"⚠️ League context health issues: {valid_contexts} valid, {broken_contexts} broken, {missing_contexts} missing ({health_stats['health_percentage']:.1f}% healthy)")
        
        health_stats["is_healthy"] = is_healthy
        return health_stats
        
    except Exception as e:
        log(f"❌ League context health validation failed: {str(e)}")
        raise


def cleanup_league_context_backup_tables(cursor, logger=None):
    """
    Clean up temporary backup tables created during ETL process
    """
    def log(message):
        if logger:
            logger.log(message)
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    
    try:
        cursor.execute("DROP TABLE IF EXISTS etl_backup_user_league_contexts")
        log("🧹 Cleaned up league context backup tables")
        
    except Exception as e:
        log(f"❌ Cleanup failed: {str(e)}")
        # Don't raise - cleanup failure shouldn't break ETL


def run_complete_league_context_protection(cursor, logger=None) -> Dict[str, any]:
    """
    Run the complete league context protection workflow:
    1. Backup existing contexts
    2. (ETL runs externally)
    3. Restore contexts
    4. Auto-fix any remaining broken contexts
    5. Validate health
    6. Cleanup
    
    Returns:
        Dict with complete statistics
    """
    def log(message):
        if logger:
            logger.log(message)
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    
    try:
        log("🛡️ Starting complete league context protection...")
        
        # Step 1: Backup
        backup_count = backup_user_league_contexts(cursor, logger)
        
        # Note: ETL import happens externally between backup and restore
        
        # Step 2: Restore
        restore_stats = restore_user_league_contexts(cursor, logger)
        
        # Step 3: Auto-fix any remaining broken contexts
        fixed_count = auto_fix_broken_league_contexts(cursor, logger)
        
        # Step 4: Validate health
        health_stats = validate_league_context_health(cursor, logger)
        
        # Step 5: Cleanup
        cleanup_league_context_backup_tables(cursor, logger)
        
        complete_stats = {
            "backup_count": backup_count,
            "restore_stats": restore_stats,
            "fixed_count": fixed_count,
            "health_stats": health_stats,
            "overall_success": health_stats["is_healthy"]
        }
        
        if complete_stats["overall_success"]:
            log("🎉 League context protection completed successfully!")
        else:
            log("⚠️ League context protection completed with warnings")
        
        return complete_stats
        
    except Exception as e:
        log(f"❌ League context protection failed: {str(e)}")
        raise


if __name__ == "__main__":
    """Test the league context protection functions"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test League Context Protection')
    parser.add_argument('--backup', action='store_true', help='Test backup function')
    parser.add_argument('--restore', action='store_true', help='Test restore function')
    parser.add_argument('--auto-fix', action='store_true', help='Test auto-fix function')
    parser.add_argument('--validate', action='store_true', help='Test validation function')
    parser.add_argument('--complete', action='store_true', help='Run complete protection workflow')
    
    args = parser.parse_args()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        if args.backup:
            backup_user_league_contexts(cursor)
        elif args.restore:
            restore_user_league_contexts(cursor)
        elif args.auto_fix:
            auto_fix_broken_league_contexts(cursor)
        elif args.validate:
            validate_league_context_health(cursor)
        elif args.complete:
            run_complete_league_context_protection(cursor)
        else:
            print("Usage: python enhanced_league_context_protection.py --complete")
            print("   or: python enhanced_league_context_protection.py --validate") 