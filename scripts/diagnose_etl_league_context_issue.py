#!/usr/bin/env python3
"""
ETL League Context Issue Diagnostic and Fix Script

This script diagnoses and fixes the issue where users lose league context
after ETL import runs due to failed league context restoration.
"""

import sys
import os
import json
from datetime import datetime

# Add project root to Python path
sys.path.append('.')
sys.path.append('data/etl/database_import')

from database_config import get_db
import psycopg2
from psycopg2.extras import RealDictCursor

def check_users_with_null_league_context():
    """Check for users with NULL league_context who should have one"""
    print("🔍 Checking for users with NULL league context...")
    
    try:
        with get_db() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Find users with NULL league_context who have player associations
            cursor.execute("""
                SELECT 
                    u.id,
                    u.email,
                    u.first_name,
                    u.last_name,
                    u.league_context,
                    COUNT(DISTINCT upa.tenniscores_player_id) as association_count,
                    STRING_AGG(DISTINCT l.league_name, ', ') as associated_leagues,
                    STRING_AGG(DISTINCT l.league_id, ', ') as league_ids
                FROM users u
                JOIN user_player_associations upa ON u.id = upa.user_id
                JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                JOIN leagues l ON p.league_id = l.id
                WHERE u.league_context IS NULL
                GROUP BY u.id, u.email, u.first_name, u.last_name, u.league_context
                ORDER BY u.first_name, u.last_name
            """)
            
            null_context_users = cursor.fetchall()
            
            if null_context_users:
                print(f"❌ Found {len(null_context_users)} users with NULL league context:")
                for user in null_context_users:
                    print(f"   👤 {user['first_name']} {user['last_name']} ({user['email']})")
                    print(f"      Associated leagues: {user['associated_leagues']}")
                    print(f"      League IDs: {user['league_ids']}")
                    print()
                return null_context_users
            else:
                print("✅ No users with NULL league context found")
                return []
                
    except Exception as e:
        print(f"❌ Error checking users with NULL league context: {e}")
        return []

def check_users_with_broken_league_context():
    """Check for users with broken league_context (pointing to non-existent leagues)"""
    print("🔍 Checking for users with broken league context...")
    
    try:
        with get_db() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Find users with broken league_context
            cursor.execute("""
                SELECT 
                    u.id,
                    u.email,
                    u.first_name,
                    u.last_name,
                    u.league_context,
                    COUNT(DISTINCT upa.tenniscores_player_id) as association_count,
                    STRING_AGG(DISTINCT l2.league_name, ', ') as associated_leagues
                FROM users u
                JOIN user_player_associations upa ON u.id = upa.user_id
                JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                JOIN leagues l2 ON p.league_id = l2.id
                LEFT JOIN leagues l ON u.league_context = l.id
                WHERE u.league_context IS NOT NULL AND l.id IS NULL
                GROUP BY u.id, u.email, u.first_name, u.last_name, u.league_context
                ORDER BY u.first_name, u.last_name
            """)
            
            broken_context_users = cursor.fetchall()
            
            if broken_context_users:
                print(f"❌ Found {len(broken_context_users)} users with broken league context:")
                for user in broken_context_users:
                    print(f"   👤 {user['first_name']} {user['last_name']} ({user['email']})")
                    print(f"      Broken league_context ID: {user['league_context']}")
                    print(f"      Should be: {user['associated_leagues']}")
                    print()
                return broken_context_users
            else:
                print("✅ No users with broken league context found")
                return []
                
    except Exception as e:
        print(f"❌ Error checking users with broken league context: {e}")
        return []

def analyze_league_id_mapping():
    """Analyze current league ID structure to understand mapping issues"""
    print("🔍 Analyzing league ID structure...")
    
    try:
        with get_db() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get current leagues
            cursor.execute("""
                SELECT id, league_id, league_name
                FROM leagues
                ORDER BY league_id
            """)
            
            leagues = cursor.fetchall()
            
            print("📊 Current leagues in database:")
            for league in leagues:
                print(f"   🏆 ID: {league['id']} | String ID: {league['league_id']} | Name: {league['league_name']}")
            print()
            
            return {league['league_id']: league['id'] for league in leagues}
            
    except Exception as e:
        print(f"❌ Error analyzing league ID mapping: {e}")
        return {}

def fix_null_league_contexts(dry_run=True):
    """Fix users with NULL league contexts using intelligent prioritization"""
    print(f"🔧 Fixing NULL league contexts {'(DRY RUN)' if dry_run else '(LIVE RUN)'}...")
    
    try:
        with get_db() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get users with NULL league contexts
            cursor.execute("""
                SELECT DISTINCT u.id, u.first_name, u.last_name, u.email
                FROM users u
                JOIN user_player_associations upa ON u.id = upa.user_id
                WHERE u.league_context IS NULL
            """)
            
            users_to_fix = cursor.fetchall()
            fixed_count = 0
            
            print(f"📋 Found {len(users_to_fix)} users to fix")
            
            for user in users_to_fix:
                # Get their best league using prioritization logic
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
                        has_team DESC,
                        COUNT(ms.id) DESC,
                        MAX(ms.match_date) DESC NULLS LAST
                    LIMIT 1
                """, [user['id']])
                
                best_league = cursor.fetchone()
                
                if best_league:
                    print(f"   🔧 {user['first_name']} {user['last_name']}: → {best_league['league_name']} ({best_league['match_count']} matches, team: {bool(best_league['has_team'])})")
                    
                    if not dry_run:
                        cursor.execute("""
                            UPDATE users 
                            SET league_context = %s
                            WHERE id = %s
                        """, [best_league['league_id'], user['id']])
                    
                    fixed_count += 1
                else:
                    print(f"   ⚠️ {user['first_name']} {user['last_name']}: No suitable league found")
            
            if not dry_run:
                conn.commit()
                print(f"✅ Fixed {fixed_count} users with NULL league contexts")
            else:
                print(f"📋 Would fix {fixed_count} users (run with --live to apply)")
                
            return fixed_count
            
    except Exception as e:
        print(f"❌ Error fixing NULL league contexts: {e}")
        return 0

def fix_broken_league_contexts(dry_run=True):
    """Fix users with broken league contexts"""
    print(f"🔧 Fixing broken league contexts {'(DRY RUN)' if dry_run else '(LIVE RUN)'}...")
    
    try:
        with get_db() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get users with broken league contexts
            cursor.execute("""
                SELECT DISTINCT u.id, u.first_name, u.last_name, u.email, u.league_context
                FROM users u
                JOIN user_player_associations upa ON u.id = upa.user_id
                LEFT JOIN leagues l ON u.league_context = l.id
                WHERE u.league_context IS NOT NULL AND l.id IS NULL
            """)
            
            users_to_fix = cursor.fetchall()
            fixed_count = 0
            
            print(f"📋 Found {len(users_to_fix)} users with broken league contexts")
            
            for user in users_to_fix:
                # Get their best league using same prioritization logic
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
                        has_team DESC,
                        COUNT(ms.id) DESC,
                        MAX(ms.match_date) DESC NULLS LAST
                    LIMIT 1
                """, [user['id']])
                
                best_league = cursor.fetchone()
                
                if best_league:
                    print(f"   🔧 {user['first_name']} {user['last_name']}: {user['league_context']} → {best_league['league_id']} ({best_league['league_name']})")
                    
                    if not dry_run:
                        cursor.execute("""
                            UPDATE users 
                            SET league_context = %s
                            WHERE id = %s
                        """, [best_league['league_id'], user['id']])
                    
                    fixed_count += 1
                else:
                    print(f"   ⚠️ {user['first_name']} {user['last_name']}: No suitable league found")
            
            if not dry_run:
                conn.commit()
                print(f"✅ Fixed {fixed_count} users with broken league contexts")
            else:
                print(f"📋 Would fix {fixed_count} users (run with --live to apply)")
                
            return fixed_count
            
    except Exception as e:
        print(f"❌ Error fixing broken league contexts: {e}")
        return 0

def create_enhanced_league_context_restoration():
    """Create enhanced league context restoration logic for future ETL runs"""
    print("🔧 Creating enhanced league context restoration logic...")
    
    enhancement_code = '''
def enhanced_restore_league_contexts(self, conn):
    """Enhanced league context restoration with better error handling and fallbacks"""
    self.log("🏆 Restoring league contexts with enhanced logic...")
    cursor = conn.cursor()
    
    # Step 1: Try direct restoration (existing logic)
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
    
    direct_restored = cursor.rowcount
    self.log(f"✅ Direct restoration: {direct_restored} league contexts")
    
    # Step 2: Check for restoration failures
    cursor.execute("""
        SELECT COUNT(*)
        FROM user_league_contexts_backup backup
        LEFT JOIN leagues l ON l.league_id = backup.league_string_id
        WHERE l.id IS NULL
    """)
    
    failed_mappings = cursor.fetchone()[0]
    if failed_mappings > 0:
        self.log(f"⚠️ Found {failed_mappings} failed league mappings - investigating...")
        
        # Log failed mappings for debugging
        cursor.execute("""
            SELECT DISTINCT backup.league_string_id, backup.league_name
            FROM user_league_contexts_backup backup
            LEFT JOIN leagues l ON l.league_id = backup.league_string_id
            WHERE l.id IS NULL
        """)
        
        failed_leagues = cursor.fetchall()
        for league in failed_leagues:
            self.log(f"   ❌ Failed mapping: {league[0]} ({league[1]})")
    
    # Step 3: Enhanced auto-fix with prioritization
    auto_fixed = self._enhanced_auto_fix_null_league_contexts(conn)
    
    return {
        'direct_restored': direct_restored,
        'auto_fixed': auto_fixed,
        'total_restored': direct_restored + auto_fixed
    }

def _enhanced_auto_fix_null_league_contexts(self, conn):
    """Enhanced auto-fix with better prioritization logic"""
    cursor = conn.cursor()
    
    # Get all users needing fixes (NULL or broken contexts)
    cursor.execute("""
        SELECT DISTINCT u.id, u.first_name, u.last_name, u.league_context
        FROM users u
        JOIN user_player_associations upa ON u.id = upa.user_id
        LEFT JOIN leagues l ON u.league_context = l.id
        WHERE (u.league_context IS NULL OR l.id IS NULL)
    """)
    
    users_to_fix = cursor.fetchall()
    fixed_count = 0
    
    for user in users_to_fix:
        # Enhanced prioritization: primary association > team assignment > recent activity > match count
        cursor.execute("""
            SELECT 
                p.league_id,
                l.league_name,
                COUNT(ms.id) as match_count,
                MAX(ms.match_date) as last_match_date,
                (CASE WHEN p.team_id IS NOT NULL THEN 1 ELSE 0 END) as has_team,
                (CASE WHEN upa.is_primary = true THEN 1 ELSE 0 END) as is_primary,
                MAX(upa.created_at) as association_date
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
            GROUP BY p.league_id, l.league_name, p.team_id, upa.is_primary
            ORDER BY 
                is_primary DESC,           -- Primary association first
                has_team DESC,             -- Users with team assignments
                COUNT(ms.id) DESC,         -- Most active in matches
                MAX(ms.match_date) DESC NULLS LAST,  -- Most recent activity
                MAX(upa.created_at) DESC   -- Most recent association
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
            self.log(f"   🔧 {user[1]} {user[2]}: → {best_league[1]} (matches: {best_league[2]}, primary: {bool(best_league[5])}, team: {bool(best_league[4])})")
    
    return fixed_count
'''
    
    print("📄 Enhanced restoration code generated. This should be integrated into the ETL script.")
    print("💡 Key improvements:")
    print("   - Better error handling for failed league mappings")
    print("   - Enhanced prioritization logic (primary > team > activity)")
    print("   - Detailed logging for debugging restoration issues")
    print("   - Automatic fallback for restoration failures")
    
    return enhancement_code

def main():
    """Main diagnostic function"""
    print("🔍 ETL League Context Issue Diagnostic Tool")
    print("=" * 60)
    
    # Check current state
    null_users = check_users_with_null_league_context()
    broken_users = check_users_with_broken_league_context()
    
    # Analyze league structure
    league_mapping = analyze_league_id_mapping()
    
    # Determine if fixes are needed
    total_issues = len(null_users) + len(broken_users)
    
    if total_issues == 0:
        print("✅ No league context issues found!")
        return
    
    print(f"📊 Summary: {len(null_users)} NULL contexts + {len(broken_users)} broken contexts = {total_issues} total issues")
    print()
    
    # Ask for fix confirmation
    response = input("🔧 Run fixes? (d=dry-run, l=live, n=no): ").lower().strip()
    
    if response in ['d', 'dry', 'dry-run']:
        print("\n🧪 Running dry-run fixes...")
        fix_null_league_contexts(dry_run=True)
        fix_broken_league_contexts(dry_run=True)
    elif response in ['l', 'live']:
        print("\n🚀 Running live fixes...")
        null_fixed = fix_null_league_contexts(dry_run=False)
        broken_fixed = fix_broken_league_contexts(dry_run=False)
        total_fixed = null_fixed + broken_fixed
        print(f"\n🎉 Fixed {total_fixed} users total!")
    else:
        print("🚫 No fixes applied")
    
    # Generate enhancement code
    print("\n🔧 Generating enhancement recommendations...")
    create_enhanced_league_context_restoration()

if __name__ == "__main__":
    main() 