#!/usr/bin/env python3
"""
Enhanced ETL League Context Protection System

This script provides enhanced league context backup and restoration logic
that can be integrated into existing ETL scripts to prevent users from
losing their league context during ETL imports.
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

class EnhancedLeagueContextProtection:
    """Enhanced league context protection for ETL processes"""
    
    def __init__(self, logger=None):
        self.logger = logger
        
    def log(self, message, level="INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if self.logger:
            if level == "ERROR":
                self.logger.error(f"[{timestamp}] {message}")
            elif level == "WARNING":
                self.logger.warning(f"[{timestamp}] {message}")
            else:
                self.logger.info(f"[{timestamp}] {message}")
        else:
            print(f"[{timestamp}] {message}")
    
    def enhanced_backup_league_contexts(self, conn):
        """Enhanced backup of league contexts with validation"""
        self.log("💾 Starting enhanced league context backup...")
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Create enhanced backup table with user association data
        cursor.execute("""
            DROP TABLE IF EXISTS enhanced_league_contexts_backup;
            CREATE TABLE enhanced_league_contexts_backup AS
            SELECT 
                u.id as user_id,
                u.email,
                u.first_name,
                u.last_name,
                u.league_context as original_league_context_id,
                l.league_id as original_league_string_id,
                l.league_name as original_league_name,
                -- Get user's association data for fallback restoration
                ARRAY_AGG(DISTINCT p.league_id) as user_league_ids,
                ARRAY_AGG(DISTINCT l2.league_name) as user_league_names,
                COUNT(DISTINCT p.league_id) as league_count,
                -- Get team assignments for prioritization
                SUM(CASE WHEN p.team_id IS NOT NULL THEN 1 ELSE 0 END) as teams_assigned,
                -- Get match activity for prioritization
                COUNT(DISTINCT ms.id) as total_matches,
                MAX(ms.match_date) as last_match_date,
                CURRENT_TIMESTAMP as backup_created_at
            FROM users u
            LEFT JOIN leagues l ON u.league_context = l.id
            LEFT JOIN user_player_associations upa ON u.id = upa.user_id
            LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
            LEFT JOIN leagues l2 ON p.league_id = l2.id
            LEFT JOIN match_scores ms ON (
                (ms.home_player_1_id = p.tenniscores_player_id OR 
                 ms.home_player_2_id = p.tenniscores_player_id OR
                 ms.away_player_1_id = p.tenniscores_player_id OR 
                 ms.away_player_2_id = p.tenniscores_player_id)
                AND ms.league_id = p.league_id
            )
            WHERE u.league_context IS NOT NULL
            GROUP BY u.id, u.email, u.first_name, u.last_name, u.league_context, 
                     l.league_id, l.league_name
        """)
        
        cursor.execute("SELECT COUNT(*) FROM enhanced_league_contexts_backup")
        backup_count = cursor.fetchone()['count']
        
        # Validate backup data
        cursor.execute("""
            SELECT 
                COUNT(*) as total_users,
                COUNT(CASE WHEN original_league_context_id IS NOT NULL THEN 1 END) as users_with_context,
                COUNT(CASE WHEN original_league_string_id IS NOT NULL THEN 1 END) as valid_league_mappings,
                COUNT(CASE WHEN league_count > 0 THEN 1 END) as users_with_associations
            FROM enhanced_league_contexts_backup
        """)
        
        validation = cursor.fetchone()
        
        self.log(f"✅ Enhanced backup created: {backup_count} users")
        self.log(f"   📊 Users with context: {validation['users_with_context']}")
        self.log(f"   📊 Valid league mappings: {validation['valid_league_mappings']}")
        self.log(f"   📊 Users with associations: {validation['users_with_associations']}")
        
        # Check for potential issues
        if validation['valid_league_mappings'] < validation['users_with_context']:
            missing_mappings = validation['users_with_context'] - validation['valid_league_mappings']
            self.log(f"⚠️ Warning: {missing_mappings} users have contexts but no valid league mappings", "WARNING")
        
        conn.commit()
        return backup_count
    
    def enhanced_restore_league_contexts(self, conn):
        """Enhanced restoration with multiple fallback strategies"""
        self.log("🔄 Starting enhanced league context restoration...")
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if backup exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'enhanced_league_contexts_backup'
            )
        """)
        
        if not cursor.fetchone()['exists']:
            self.log("❌ No enhanced backup found - cannot restore", "ERROR")
            return {'restored': 0, 'failed': 0}
        
        restoration_stats = {
            'direct_restored': 0,
            'fallback_restored': 0,
            'failed': 0,
            'strategies_used': []
        }
        
        # Strategy 1: Direct restoration using league string ID mapping
        self.log("🔧 Strategy 1: Direct league string ID mapping...")
        cursor.execute("""
            UPDATE users 
            SET league_context = (
                SELECT l.id 
                FROM enhanced_league_contexts_backup backup
                JOIN leagues l ON l.league_id = backup.original_league_string_id
                WHERE backup.user_id = users.id
                LIMIT 1
            )
            WHERE id IN (
                SELECT backup.user_id
                FROM enhanced_league_contexts_backup backup
                JOIN leagues l ON l.league_id = backup.original_league_string_id
                WHERE backup.user_id = users.id
            )
        """)
        
        direct_restored = cursor.rowcount
        restoration_stats['direct_restored'] = direct_restored
        restoration_stats['strategies_used'].append('direct_mapping')
        self.log(f"   ✅ Direct restoration: {direct_restored} users")
        
        # Strategy 2: Fallback for users with failed direct restoration
        self.log("🔧 Strategy 2: Intelligent fallback for failed restorations...")
        
        # Find users who still need restoration
        cursor.execute("""
            SELECT 
                backup.user_id,
                backup.first_name,
                backup.last_name,
                backup.original_league_string_id,
                backup.user_league_ids,
                backup.user_league_names,
                backup.teams_assigned,
                backup.total_matches,
                backup.last_match_date
            FROM enhanced_league_contexts_backup backup
            LEFT JOIN users u ON backup.user_id = u.id
            WHERE u.league_context IS NULL
            ORDER BY backup.teams_assigned DESC, backup.total_matches DESC
        """)
        
        users_needing_fallback = cursor.fetchall()
        fallback_restored = 0
        
        self.log(f"   🔍 Found {len(users_needing_fallback)} users needing fallback restoration")
        
        for user in users_needing_fallback:
            # Find best league for this user
            best_league = self._find_best_league_for_user(cursor, user['user_id'])
            
            if best_league:
                cursor.execute("""
                    UPDATE users 
                    SET league_context = %s
                    WHERE id = %s
                """, [best_league['league_id'], user['user_id']])
                
                fallback_restored += 1
                self.log(f"   🔧 {user['first_name']} {user['last_name']}: → {best_league['league_name']} (fallback)")
            else:
                restoration_stats['failed'] += 1
                self.log(f"   ❌ {user['first_name']} {user['last_name']}: No suitable league found", "WARNING")
        
        restoration_stats['fallback_restored'] = fallback_restored
        restoration_stats['strategies_used'].append('intelligent_fallback')
        
        # Strategy 3: Final validation and health check
        self.log("🔧 Strategy 3: Final validation and health check...")
        validation_results = self._validate_restoration(cursor)
        
        conn.commit()
        
        # Clean up backup table
        cursor.execute("DROP TABLE IF EXISTS enhanced_league_contexts_backup")
        
        # Log final results
        total_restored = direct_restored + fallback_restored
        self.log("📊 Enhanced Restoration Summary:")
        self.log(f"   ✅ Direct restorations: {direct_restored}")
        self.log(f"   🔧 Fallback restorations: {fallback_restored}")
        self.log(f"   ❌ Failed restorations: {restoration_stats['failed']}")
        self.log(f"   🎯 Total restored: {total_restored}")
        self.log(f"   📈 Success rate: {(total_restored / (total_restored + restoration_stats['failed']) * 100):.1f}%" if total_restored + restoration_stats['failed'] > 0 else "100.0%")
        
        return restoration_stats
    
    def _find_best_league_for_user(self, cursor, user_id):
        """Find the best league for a user using prioritization logic"""
        cursor.execute("""
            SELECT 
                p.league_id,
                l.league_name,
                COUNT(ms.id) as match_count,
                MAX(ms.match_date) as last_match_date,
                SUM(CASE WHEN p.team_id IS NOT NULL THEN 1 ELSE 0 END) as teams_assigned,
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
            GROUP BY p.league_id, l.league_name
            ORDER BY 
                SUM(CASE WHEN p.team_id IS NOT NULL THEN 1 ELSE 0 END) DESC,  -- Teams assigned
                COUNT(ms.id) DESC,                                           -- Match activity
                MAX(ms.match_date) DESC NULLS LAST,                          -- Recent activity
                MAX(upa.created_at) DESC                                     -- Recent association
            LIMIT 1
        """, [user_id])
        
        return cursor.fetchone()
    
    def _validate_restoration(self, cursor):
        """Validate the restoration process"""
        cursor.execute("""
            SELECT 
                COUNT(*) as total_users,
                COUNT(CASE WHEN u.league_context IS NULL THEN 1 END) as null_contexts,
                COUNT(CASE WHEN l.id IS NULL AND u.league_context IS NOT NULL THEN 1 END) as broken_contexts
            FROM users u
            LEFT JOIN leagues l ON u.league_context = l.id
            JOIN user_player_associations upa ON u.id = upa.user_id
        """)
        
        validation = cursor.fetchone()
        
        self.log("🔍 Restoration Validation:")
        self.log(f"   👥 Total users: {validation['total_users']}")
        self.log(f"   ❌ NULL contexts: {validation['null_contexts']}")
        self.log(f"   💥 Broken contexts: {validation['broken_contexts']}")
        
        health_score = ((validation['total_users'] - validation['null_contexts'] - validation['broken_contexts']) / validation['total_users'] * 100) if validation['total_users'] > 0 else 100
        self.log(f"   📊 Health score: {health_score:.1f}%")
        
        return validation

def integrate_with_existing_etl():
    """Show how to integrate with existing ETL scripts"""
    integration_code = '''
# Integration Example for existing ETL scripts:

from scripts.enhance_etl_league_context_protection import EnhancedLeagueContextProtection

class EnhancedComprehensiveETL(ComprehensiveETL):
    def __init__(self):
        super().__init__()
        self.league_context_protection = EnhancedLeagueContextProtection(logger=self)
    
    def backup_user_data_and_team_mappings(self, conn):
        """Enhanced backup with improved league context protection"""
        # Call original backup
        original_results = super().backup_user_data_and_team_mappings(conn)
        
        # Add enhanced league context backup
        enhanced_backup_count = self.league_context_protection.enhanced_backup_league_contexts(conn)
        original_results['enhanced_league_backup_count'] = enhanced_backup_count
        
        return original_results
    
    def restore_user_data_with_team_mappings(self, conn):
        """Enhanced restoration with improved league context restoration"""
        # Call original restoration
        original_results = super().restore_user_data_with_team_mappings(conn)
        
        # Add enhanced league context restoration
        enhanced_results = self.league_context_protection.enhanced_restore_league_contexts(conn)
        original_results['enhanced_league_restoration'] = enhanced_results
        
        return original_results

# Usage in ETL scripts:
# Replace: etl = ComprehensiveETL()
# With:    etl = EnhancedComprehensiveETL()
'''
    
    print("🔧 Integration code for existing ETL scripts:")
    print(integration_code)
    return integration_code

def main():
    """Main function for testing the enhanced protection system"""
    print("🛡️ Enhanced ETL League Context Protection System")
    print("=" * 60)
    
    protection = EnhancedLeagueContextProtection()
    
    try:
        with get_db() as conn:
            print("\n🧪 Testing enhanced backup system...")
            backup_count = protection.enhanced_backup_league_contexts(conn)
            
            print("\n🧪 Testing enhanced restoration system...")
            restoration_results = protection.enhanced_restore_league_contexts(conn)
            
            print(f"\n✅ Test completed successfully!")
            print(f"   📊 Backup: {backup_count} users")
            print(f"   🔄 Restoration: {restoration_results}")
            
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🔧 Generating integration instructions...")
    integrate_with_existing_etl()

if __name__ == "__main__":
    main() 