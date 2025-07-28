#!/usr/bin/env python3
"""
Enhanced Practice Time Protection Module
========================================

This module provides enhanced protection functions for practice times
during ETL imports. These functions can be integrated into the main
ETL script to prevent practice time orphaning issues.

Functions:
- validate_etl_safety_preconditions(): Check safety before ETL
- create_enhanced_practice_time_backup(): Better backup with metadata
- restore_practice_times_with_fallback(): Robust restoration logic
- validate_practice_time_health(): Post-ETL health check
"""

def validate_etl_safety_preconditions(cursor, logger=None):
    """
    Validate that ETL can safely preserve team IDs
    
    Returns:
        (bool, list): (is_safe, list_of_issues)
    """
    if logger:
        logger.info("🔍 Validating ETL Safety Preconditions...")
    
    issues = []
    
    # Check 1: Verify UPSERT constraints exist
    cursor.execute("""
        SELECT constraint_name 
        FROM information_schema.table_constraints 
        WHERE table_name = 'teams' 
        AND constraint_type = 'UNIQUE'
        AND constraint_name = 'unique_team_club_series_league'
    """)
    
    if not cursor.fetchone():
        issues.append("Missing unique_team_club_series_league constraint - team ID preservation will fail")
        if logger:
            logger.error("❌ Missing UPSERT constraint")
    elif logger:
        logger.info("✅ UPSERT constraint exists")
    
    # Check 2: Look for potential constraint violations
    cursor.execute("""
        SELECT club_id, series_id, league_id, COUNT(*) as count
        FROM teams 
        GROUP BY club_id, series_id, league_id
        HAVING COUNT(*) > 1
    """)
    
    violations = cursor.fetchall()
    if violations:
        issues.append(f"Found {len(violations)} constraint violations that will force team recreation")
        if logger:
            logger.warning(f"⚠️  Found {len(violations)} constraint violations")
            for violation in violations[:3]:
                logger.warning(f"   Violation: Club {violation[0]}, Series {violation[1]}, League {violation[2]}")
    elif logger:
        logger.info("✅ No constraint violations found")
    
    # Check 3: Verify practice times exist and have valid team references
    cursor.execute("""
        SELECT COUNT(*) as total_practices,
               COALESCE(SUM(CASE WHEN home_team_id IS NULL THEN 1 ELSE 0 END), 0) as orphaned_practices,
               COALESCE(SUM(CASE WHEN t.id IS NULL THEN 1 ELSE 0 END), 0) as invalid_team_refs
        FROM schedule s
        LEFT JOIN teams t ON s.home_team_id = t.id
        WHERE s.home_team ILIKE '%practice%'
    """)
    
    practice_health = cursor.fetchone()
    if practice_health:
        total, orphaned, invalid = practice_health
        if logger:
            logger.info(f"Practice times: {total} total, {orphaned} orphaned, {invalid} invalid refs")
        
        if orphaned > 0 or invalid > 0:
            issues.append(f"Found {orphaned + invalid} practice times with invalid team references")
            if logger:
                logger.error(f"❌ Invalid practice time references found")
        elif logger:
            logger.info("✅ All practice times have valid team references")
    
    is_safe = len(issues) == 0
    return is_safe, issues

def create_enhanced_practice_time_backup(cursor, logger=None):
    """
    Create enhanced backup with team name patterns for fallback matching
    
    Returns:
        int: Number of practice times backed up
    """
    if logger:
        logger.info("💾 Creating enhanced practice time backup...")
    
    # Create backup with both team IDs and team name patterns
    cursor.execute("""
        DROP TABLE IF EXISTS enhanced_practice_times_backup;
        CREATE TABLE enhanced_practice_times_backup AS
        SELECT 
            s.*,
            t.team_name,
            t.team_alias,
            c.name as club_name,
            ser.name as series_name,
            l.league_id as league_string_id
        FROM schedule s
        LEFT JOIN teams t ON s.home_team_id = t.id
        LEFT JOIN clubs c ON t.club_id = c.id
        LEFT JOIN series ser ON t.series_id = ser.id
        LEFT JOIN leagues l ON t.league_id = l.id
        WHERE s.home_team ILIKE '%practice%'
    """)
    
    cursor.execute("SELECT COUNT(*) FROM enhanced_practice_times_backup")
    backup_count = cursor.fetchone()[0]
    
    if logger:
        logger.info(f"✅ Backed up {backup_count} practice times with enhanced metadata")
    
    return backup_count

def validate_team_id_preservation_post_etl(cursor, logger=None):
    """
    Validate that team IDs were preserved after ETL
    
    Returns:
        (bool, dict): (preservation_success, stats)
    """
    if logger:
        logger.info("🔍 Validating team ID preservation after ETL...")
    
    # Check if backup table exists
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'enhanced_practice_times_backup'
        )
    """)
    
    if not cursor.fetchone()[0]:
        if logger:
            logger.warning("⚠️  No enhanced backup found - cannot validate preservation")
        return False, {"error": "No backup found"}
    
    # Check how many practice times can be matched by team ID
    cursor.execute("""
        SELECT 
            COUNT(*) as total_backed_up,
            SUM(CASE WHEN t.id IS NOT NULL THEN 1 ELSE 0 END) as id_preserved,
            SUM(CASE WHEN t.id IS NULL AND backup.home_team_id IS NOT NULL THEN 1 ELSE 0 END) as id_lost
        FROM enhanced_practice_times_backup backup
        LEFT JOIN teams t ON backup.home_team_id = t.id
    """)
    
    preservation_stats = cursor.fetchone()
    if preservation_stats:
        total, preserved, lost = preservation_stats
        preservation_rate = (preserved / total * 100) if total > 0 else 0
        
        stats = {
            "total": total,
            "preserved": preserved,
            "lost": lost,
            "preservation_rate": preservation_rate
        }
        
        if logger:
            logger.info(f"Team ID preservation: {preserved}/{total} ({preservation_rate:.1f}%)")
        
        success = preservation_rate >= 90
        return success, stats
    
    return False, {"error": "No preservation stats"}

def restore_practice_times_with_fallback(cursor, logger=None, dry_run=False):
    """
    Restore practice times with enhanced fallback logic
    
    Returns:
        dict: Restoration statistics
    """
    if logger:
        logger.info(f"{'🔍 DRY RUN:' if dry_run else '💾 EXECUTING:'} Restoring practice times with fallback...")
    
    stats = {"direct": 0, "fallback": 0, "total": 0}
    
    # Strategy 1: Direct team ID restoration (for preserved IDs)
    cursor.execute("""
        SELECT COUNT(*)
        FROM enhanced_practice_times_backup backup
        JOIN teams t ON backup.home_team_id = t.id
        WHERE NOT EXISTS (
            SELECT 1 FROM schedule s 
            WHERE s.home_team = backup.home_team 
            AND s.match_date = backup.match_date 
            AND s.home_team_id = backup.home_team_id
        )
    """)
    
    direct_restorable = cursor.fetchone()[0]
    stats["direct"] = direct_restorable
    
    if logger:
        logger.info(f"Strategy 1 (Direct ID): {direct_restorable} practices can be restored")
    
    if not dry_run and direct_restorable > 0:
        cursor.execute("""
            INSERT INTO schedule (
                league_id, match_date, match_time, home_team, away_team,
                home_team_id, away_team_id, location, created_at
            )
            SELECT 
                backup.league_id, backup.match_date, backup.match_time,
                backup.home_team, backup.away_team, backup.home_team_id,
                backup.away_team_id, backup.location, CURRENT_TIMESTAMP
            FROM enhanced_practice_times_backup backup
            JOIN teams t ON backup.home_team_id = t.id
            WHERE NOT EXISTS (
                SELECT 1 FROM schedule s 
                WHERE s.home_team = backup.home_team 
                AND s.match_date = backup.match_date 
                AND s.home_team_id = backup.home_team_id
            )
        """)
        if logger:
            logger.info(f"✅ Restored {direct_restorable} practices via direct ID matching")
    
    # Strategy 2: Team name pattern matching (for lost IDs)
    cursor.execute("""
        SELECT COUNT(*)
        FROM enhanced_practice_times_backup backup
        LEFT JOIN teams preserved_team ON backup.home_team_id = preserved_team.id
        JOIN teams new_team ON (
            new_team.team_name = backup.team_name 
            OR (backup.team_alias IS NOT NULL AND new_team.team_alias = backup.team_alias)
            OR (
                backup.club_name IS NOT NULL 
                AND backup.series_name IS NOT NULL
                AND new_team.team_name LIKE backup.club_name || '%'
                AND (
                    new_team.team_alias LIKE '%' || backup.series_name || '%'
                    OR new_team.team_name LIKE '%' || backup.series_name || '%'
                )
            )
        )
        JOIN leagues l ON new_team.league_id = l.id AND l.league_id = backup.league_string_id
        WHERE preserved_team.id IS NULL  -- Only for lost IDs
        AND NOT EXISTS (
            SELECT 1 FROM schedule s 
            WHERE s.home_team = backup.home_team 
            AND s.match_date = backup.match_date 
            AND s.home_team_id = new_team.id
        )
    """)
    
    fallback_restorable = cursor.fetchone()[0]
    stats["fallback"] = fallback_restorable
    
    if logger:
        logger.info(f"Strategy 2 (Name matching): {fallback_restorable} practices can be restored")
    
    if not dry_run and fallback_restorable > 0:
        cursor.execute("""
            INSERT INTO schedule (
                league_id, match_date, match_time, home_team, away_team,
                home_team_id, away_team_id, location, created_at
            )
            SELECT 
                new_team.league_id, backup.match_date, backup.match_time,
                backup.home_team, backup.away_team, new_team.id,
                backup.away_team_id, backup.location, CURRENT_TIMESTAMP
            FROM enhanced_practice_times_backup backup
            LEFT JOIN teams preserved_team ON backup.home_team_id = preserved_team.id
            JOIN teams new_team ON (
                new_team.team_name = backup.team_name 
                OR (backup.team_alias IS NOT NULL AND new_team.team_alias = backup.team_alias)
                OR (
                    backup.club_name IS NOT NULL 
                    AND backup.series_name IS NOT NULL
                    AND new_team.team_name LIKE backup.club_name || '%'
                    AND (
                        new_team.team_alias LIKE '%' || backup.series_name || '%'
                        OR new_team.team_name LIKE '%' || backup.series_name || '%'
                    )
                )
            )
            JOIN leagues l ON new_team.league_id = l.id AND l.league_id = backup.league_string_id
            WHERE preserved_team.id IS NULL
            AND NOT EXISTS (
                SELECT 1 FROM schedule s 
                WHERE s.home_team = backup.home_team 
                AND s.match_date = backup.match_date 
                AND s.home_team_id = new_team.id
            )
        """)
        if logger:
            logger.info(f"✅ Restored {fallback_restorable} practices via name matching")
    
    stats["total"] = direct_restorable + fallback_restorable
    return stats

def validate_practice_time_health(cursor, pre_etl_count, logger=None):
    """
    Validate practice time health after ETL
    
    Args:
        cursor: Database cursor
        pre_etl_count: Number of practice times before ETL
        logger: Optional logger
        
    Returns:
        dict: Health check results
    """
    if logger:
        logger.info("🔍 Validating practice time health after ETL...")
    
    # Count current practice times
    cursor.execute("""
        SELECT COUNT(*) FROM schedule 
        WHERE home_team ILIKE '%practice%'
    """)
    
    post_etl_count = cursor.fetchone()[0]
    
    # Check for orphaned practice times
    cursor.execute("""
        SELECT COUNT(*) FROM schedule s
        LEFT JOIN teams t ON s.home_team_id = t.id
        WHERE s.home_team ILIKE '%practice%'
        AND (s.home_team_id IS NULL OR t.id IS NULL)
    """)
    
    orphaned_count = cursor.fetchone()[0]
    
    health_stats = {
        "pre_etl_count": pre_etl_count,
        "post_etl_count": post_etl_count,
        "difference": post_etl_count - pre_etl_count,
        "orphaned_count": orphaned_count,
        "is_healthy": post_etl_count >= pre_etl_count and orphaned_count == 0
    }
    
    if logger:
        logger.info(f"Practice times: {pre_etl_count} → {post_etl_count} (Δ{health_stats['difference']})")
        logger.info(f"Orphaned: {orphaned_count}")
        
        if health_stats["is_healthy"]:
            logger.info("✅ Practice time health check passed")
        else:
            logger.error("❌ Practice time health check failed")
            if health_stats["difference"] < 0:
                logger.error(f"Lost {abs(health_stats['difference'])} practice times")
            if orphaned_count > 0:
                logger.error(f"Found {orphaned_count} orphaned practice times")
    
    return health_stats

def cleanup_enhanced_backup_tables(cursor, logger=None):
    """Clean up enhanced backup tables after successful ETL"""
    if logger:
        logger.info("🧹 Cleaning up enhanced backup tables...")
    
    cursor.execute("DROP TABLE IF EXISTS enhanced_practice_times_backup")
    
    if logger:
        logger.info("✅ Enhanced backup tables cleaned up") 