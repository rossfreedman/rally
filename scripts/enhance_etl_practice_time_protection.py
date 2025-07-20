#!/usr/bin/env python3
"""
Enhanced ETL Practice Time Protection
====================================

This script enhances the ETL process to prevent practice time orphaning
by improving team ID preservation and adding robust fallback mechanisms.

Key improvements:
1. Pre-ETL validation of team ID preservation constraints
2. Enhanced backup with team name pattern matching
3. Post-ETL validation and automatic fixing
4. Health checks and rollback mechanisms

Usage:
    python scripts/enhance_etl_practice_time_protection.py --validate-etl-safety
"""

import argparse
import os
import sys
from datetime import datetime

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from database_config import get_db

def validate_etl_safety_preconditions(cursor):
    """Validate that ETL can safely preserve team IDs"""
    print("🔍 Validating ETL Safety Preconditions...")
    
    issues = []
    
    # Check 1: Verify UPSERT constraints exist
    print("  Checking UPSERT constraints...")
    cursor.execute("""
        SELECT constraint_name 
        FROM information_schema.table_constraints 
        WHERE table_name = 'teams' 
        AND constraint_type = 'UNIQUE'
        AND constraint_name = 'unique_team_club_series_league'
    """)
    
    if not cursor.fetchone():
        issues.append("❌ Missing unique_team_club_series_league constraint - team ID preservation will fail")
    else:
        print("  ✅ UPSERT constraint exists")
    
    # Check 2: Look for potential constraint violations that would force recreation
    print("  Checking for constraint violations...")
    cursor.execute("""
        SELECT club_id, series_id, league_id, COUNT(*) as count, 
               string_agg(team_name, ', ') as team_names
        FROM teams 
        GROUP BY club_id, series_id, league_id
        HAVING COUNT(*) > 1
    """)
    
    violations = cursor.fetchall()
    if violations:
        issues.append(f"❌ Found {len(violations)} constraint violations that will force team recreation")
        for violation in violations[:3]:  # Show first 3
            print(f"    Violation: Club {violation[0]}, Series {violation[1]}, League {violation[2]} -> {violation[4]}")
    else:
        print("  ✅ No constraint violations found")
    
    # Check 3: Verify practice times exist and have valid team references
    print("  Checking practice time integrity...")
    cursor.execute("""
        SELECT COUNT(*) as total_practices,
               SUM(CASE WHEN home_team_id IS NULL THEN 1 ELSE 0 END) as orphaned_practices,
               SUM(CASE WHEN t.id IS NULL THEN 1 ELSE 0 END) as invalid_team_refs
        FROM schedule s
        LEFT JOIN teams t ON s.home_team_id = t.id
        WHERE s.home_team ILIKE '%practice%'
    """)
    
    practice_health = cursor.fetchone()
    if practice_health:
        total, orphaned, invalid = practice_health
        print(f"    Total practice times: {total}")
        print(f"    Orphaned (NULL team_id): {orphaned}")
        print(f"    Invalid team references: {invalid}")
        
        if orphaned > 0 or invalid > 0:
            issues.append(f"❌ Found {orphaned + invalid} practice times with invalid team references")
        else:
            print("  ✅ All practice times have valid team references")
    
    return issues

def create_enhanced_practice_time_backup(cursor):
    """Create enhanced backup with team name patterns for fallback matching"""
    print("💾 Creating enhanced practice time backup...")
    
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
    print(f"  ✅ Backed up {backup_count} practice times with enhanced metadata")
    
    return backup_count

def validate_team_id_preservation_post_etl(cursor):
    """Validate that team IDs were preserved after ETL"""
    print("🔍 Validating team ID preservation after ETL...")
    
    # Check if backup table exists
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'enhanced_practice_times_backup'
        )
    """)
    
    if not cursor.fetchone()[0]:
        print("  ⚠️  No enhanced backup found - cannot validate preservation")
        return False
    
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
        
        print(f"  Total backed up: {total}")
        print(f"  Team IDs preserved: {preserved} ({preservation_rate:.1f}%)")
        print(f"  Team IDs lost: {lost}")
        
        if preservation_rate < 90:
            print(f"  🚨 LOW PRESERVATION RATE: {preservation_rate:.1f}% - fallback restoration needed")
            return False
        else:
            print(f"  ✅ HIGH PRESERVATION RATE: {preservation_rate:.1f}% - team IDs mostly preserved")
            return True
    
    return False

def restore_practice_times_with_fallback(cursor, dry_run=True):
    """Restore practice times with enhanced fallback logic"""
    print(f"{'🔍 DRY RUN:' if dry_run else '💾 EXECUTING:'} Restoring practice times with fallback...")
    
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
    print(f"  Strategy 1 (Direct ID): {direct_restorable} practices can be restored")
    
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
        print(f"    ✅ Restored {direct_restorable} practices via direct ID matching")
    
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
    print(f"  Strategy 2 (Name matching): {fallback_restorable} practices can be restored")
    
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
        print(f"    ✅ Restored {fallback_restorable} practices via name matching")
    
    total_restorable = direct_restorable + fallback_restorable
    return total_restorable

def generate_etl_enhancement_patch():
    """Generate a patch for the main ETL script to include these protections"""
    print("📝 Generating ETL enhancement recommendations...")
    
    recommendations = """
🛡️ ETL Enhancement Recommendations:

1. **Pre-ETL Safety Check** (Add to import_all_jsons_to_database.py):
   - Run validate_etl_safety_preconditions() before clearing tables
   - Abort if critical issues found
   
2. **Enhanced Backup** (Replace existing backup_user_data_and_team_mappings):
   - Use create_enhanced_practice_time_backup() instead
   - Include team name patterns for fallback matching
   
3. **Post-ETL Validation** (Add to restore_user_data_with_team_mappings):
   - Run validate_team_id_preservation_post_etl() after team import
   - Use restore_practice_times_with_fallback() for restoration
   
4. **Health Monitoring** (Add to end of ETL process):
   - Compare practice time counts before/after
   - Alert if significant loss detected
   - Provide rollback recommendations

5. **Environment Consistency** (Add to ETL setup):
   - Verify database schema matches between environments
   - Check constraint differences that could affect UPSERT behavior
   
6. **Rollback Safety** (Add to ETL wrapper):
   - Create full database backup before ETL
   - Provide automatic rollback on critical data loss
"""
    
    print(recommendations)
    return recommendations

def main():
    parser = argparse.ArgumentParser(description='Enhance ETL practice time protection')
    parser.add_argument('--validate-etl-safety', action='store_true',
                       help='Validate current ETL safety preconditions')
    parser.add_argument('--create-enhanced-backup', action='store_true',
                       help='Create enhanced practice time backup')
    parser.add_argument('--test-fallback-restoration', action='store_true',
                       help='Test fallback restoration logic (dry run)')
    parser.add_argument('--generate-patch', action='store_true',
                       help='Generate ETL enhancement recommendations')
    parser.add_argument('--environment', choices=['local', 'staging', 'production'],
                       default='local', help='Target environment')
    
    args = parser.parse_args()
    
    # Set environment
    if args.environment == 'production':
        os.environ['RALLY_ENV'] = 'railway_production'
    elif args.environment == 'staging':
        os.environ['RALLY_ENV'] = 'railway_staging'
    
    print(f"🔧 ETL Protection Enhancement - {args.environment.upper()}")
    print("=" * 60)
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            if args.validate_etl_safety:
                issues = validate_etl_safety_preconditions(cursor)
                if issues:
                    print("\n🚨 ETL SAFETY ISSUES FOUND:")
                    for issue in issues:
                        print(f"  {issue}")
                    print("\n⚠️  Fix these issues before running ETL!")
                else:
                    print("\n✅ ETL safety validation passed - safe to run ETL")
            
            if args.create_enhanced_backup:
                backup_count = create_enhanced_practice_time_backup(cursor)
                conn.commit()
                print(f"✅ Enhanced backup created with {backup_count} practice times")
            
            if args.test_fallback_restoration:
                # First check if we can validate preservation
                preservation_ok = validate_team_id_preservation_post_etl(cursor)
                
                # Then test restoration
                restorable_count = restore_practice_times_with_fallback(cursor, dry_run=True)
                print(f"📊 Total restorable practice times: {restorable_count}")
                
                if not preservation_ok and restorable_count > 0:
                    print("💡 Fallback restoration available for lost team IDs")
                elif preservation_ok:
                    print("✅ Team ID preservation working - direct restoration sufficient")
            
            if args.generate_patch:
                generate_etl_enhancement_patch()
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 