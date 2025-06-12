#!/usr/bin/env python3
"""
Safe ID Mapping Migration - Comprehensive solution for foreign key issues
This script safely migrates data by properly mapping IDs without disabling constraints
"""

import psycopg2
from urllib.parse import urlparse
import logging
import sys
import os
import json
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_config import get_db

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

RAILWAY_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

def connect_to_railway():
    """Connect to Railway database"""
    parsed = urlparse(RAILWAY_URL)
    conn_params = {
        'dbname': parsed.path[1:],
        'user': parsed.username,
        'password': parsed.password,
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'sslmode': 'require',
        'connect_timeout': 10
    }
    return psycopg2.connect(**conn_params)

class IDMappingAnalyzer:
    """Analyzes and creates safe ID mappings between local and Railway databases"""
    
    def __init__(self):
        self.local_conn = None
        self.railway_conn = None
        self.club_mapping = {}
        self.series_mapping = {}
        self.mapping_report = {
            'clubs': {'mapped': 0, 'missing': 0, 'ambiguous': 0, 'details': []},
            'series': {'mapped': 0, 'missing': 0, 'ambiguous': 0, 'details': []},
            'created_timestamp': datetime.now().isoformat()
        }
    
    def connect_databases(self):
        """Establish database connections"""
        logger.info("🔌 Connecting to databases...")
        self.local_db_context = get_db()
        self.local_conn = self.local_db_context.__enter__()
        self.railway_conn = connect_to_railway()
        
    def disconnect_databases(self):
        """Close database connections"""
        if hasattr(self, 'local_db_context') and self.local_db_context:
            try:
                self.local_db_context.__exit__(None, None, None)
            except:
                pass
        if self.railway_conn:
            try:
                self.railway_conn.close()
            except:
                pass
    
    def analyze_club_mapping(self):
        """Create comprehensive club ID mapping"""
        logger.info("🏌️ Analyzing club mappings...")
        
        local_cursor = self.local_conn.cursor()
        railway_cursor = self.railway_conn.cursor()
        
        # Get all clubs with detailed info
        local_cursor.execute("SELECT id, name FROM clubs ORDER BY name")
        local_clubs = local_cursor.fetchall()
        
        railway_cursor.execute("SELECT id, name FROM clubs ORDER BY name")
        railway_clubs = railway_cursor.fetchall()
        
        # Create name-based mappings
        railway_by_name = {name.strip().lower(): id for id, name in railway_clubs}
        local_by_name = {name.strip().lower(): id for id, name in local_clubs}
        
        logger.info(f"  📊 Local clubs: {len(local_clubs)}, Railway clubs: {len(railway_clubs)}")
        
        for local_id, local_name in local_clubs:
            name_key = local_name.strip().lower()
            
            if name_key in railway_by_name:
                railway_id = railway_by_name[name_key]
                self.club_mapping[local_id] = railway_id
                self.mapping_report['clubs']['mapped'] += 1
                self.mapping_report['clubs']['details'].append({
                    'local_id': local_id,
                    'railway_id': railway_id,
                    'name': local_name,
                    'status': 'mapped'
                })
                logger.info(f"  ✅ {local_name}: local_id {local_id} → railway_id {railway_id}")
            else:
                self.mapping_report['clubs']['missing'] += 1
                self.mapping_report['clubs']['details'].append({
                    'local_id': local_id,
                    'railway_id': None,
                    'name': local_name,
                    'status': 'missing'
                })
                logger.warning(f"  ❌ Missing in Railway: {local_name} (local_id: {local_id})")
        
        # Check for potential alternate matches for missing clubs
        self._find_alternate_club_matches(local_clubs, railway_clubs)
        
        return self.club_mapping
    
    def _find_alternate_club_matches(self, local_clubs, railway_clubs):
        """Find potential alternate matches for missing clubs"""
        logger.info("🔍 Searching for alternate club matches...")
        
        missing_clubs = [detail for detail in self.mapping_report['clubs']['details'] if detail['status'] == 'missing']
        railway_names = [name.strip().lower() for _, name in railway_clubs]
        
        for missing in missing_clubs:
            local_name = missing['name'].strip().lower()
            
            # Check for partial matches
            potential_matches = []
            for r_name in railway_names:
                if local_name in r_name or r_name in local_name:
                    potential_matches.append(r_name)
                elif self._calculate_similarity(local_name, r_name) > 0.8:
                    potential_matches.append(r_name)
            
            if potential_matches:
                missing['potential_matches'] = potential_matches
                logger.info(f"  🔍 {missing['name']} → potential matches: {potential_matches}")
    
    def _calculate_similarity(self, s1, s2):
        """Calculate string similarity (simple implementation)"""
        # Simple Jaccard similarity
        set1 = set(s1.split())
        set2 = set(s2.split())
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        return intersection / union if union > 0 else 0
    
    def analyze_series_mapping(self):
        """Create comprehensive series ID mapping"""
        logger.info("🏆 Analyzing series mappings...")
        
        local_cursor = self.local_conn.cursor()
        railway_cursor = self.railway_conn.cursor()
        
        # Get all series with detailed info
        local_cursor.execute("SELECT id, name FROM series ORDER BY name")
        local_series = local_cursor.fetchall()
        
        railway_cursor.execute("SELECT id, name FROM series ORDER BY name")
        railway_series = railway_cursor.fetchall()
        
        # Create name-based mappings
        railway_by_name = {name.strip().lower(): id for id, name in railway_series}
        
        logger.info(f"  📊 Local series: {len(local_series)}, Railway series: {len(railway_series)}")
        
        for local_id, local_name in local_series:
            name_key = local_name.strip().lower()
            
            if name_key in railway_by_name:
                railway_id = railway_by_name[name_key]
                self.series_mapping[local_id] = railway_id
                self.mapping_report['series']['mapped'] += 1
                self.mapping_report['series']['details'].append({
                    'local_id': local_id,
                    'railway_id': railway_id,
                    'name': local_name,
                    'status': 'mapped'
                })
                logger.info(f"  ✅ {local_name}: local_id {local_id} → railway_id {railway_id}")
            else:
                self.series_mapping[local_id] = None  # Mark as unmappable
                self.mapping_report['series']['missing'] += 1
                self.mapping_report['series']['details'].append({
                    'local_id': local_id,
                    'railway_id': None,
                    'name': local_name,
                    'status': 'missing'
                })
                logger.warning(f"  ❌ Missing in Railway: {local_name} (local_id: {local_id})")
        
        return self.series_mapping
    
    def create_missing_entities_plan(self):
        """Create a plan for handling missing entities"""
        missing_clubs = [d for d in self.mapping_report['clubs']['details'] if d['status'] == 'missing']
        missing_series = [d for d in self.mapping_report['series']['details'] if d['status'] == 'missing']
        
        plan = {
            'missing_clubs': missing_clubs,
            'missing_series': missing_series,
            'recommendations': []
        }
        
        if missing_clubs:
            plan['recommendations'].append(f"Create {len(missing_clubs)} missing clubs in Railway")
            
        if missing_series:
            plan['recommendations'].append(f"Create {len(missing_series)} missing series in Railway")
            plan['recommendations'].append("Alternative: Filter out players from unmapped series")
            
        return plan
    
    def save_mapping_report(self, filename="mapping_analysis_report.json"):
        """Save comprehensive mapping report"""
        filepath = os.path.join("scripts", filename)
        with open(filepath, 'w') as f:
            json.dump(self.mapping_report, f, indent=2)
        logger.info(f"📄 Mapping report saved to {filepath}")
        return filepath

class SafeMigrator:
    """Handles safe migration using validated ID mappings"""
    
    def __init__(self, club_mapping, series_mapping):
        self.club_mapping = club_mapping
        self.series_mapping = series_mapping
        self.local_conn = None
        self.railway_conn = None
        self.migration_stats = {
            'players': {'attempted': 0, 'migrated': 0, 'skipped': 0, 'errors': []},
            'player_history': {'attempted': 0, 'migrated': 0, 'skipped': 0, 'errors': []},
            'user_player_associations': {'attempted': 0, 'migrated': 0, 'skipped': 0, 'errors': []}
        }
    
    def connect_databases(self):
        """Establish database connections"""
        self.local_db_context = get_db()
        self.local_conn = self.local_db_context.__enter__()
        self.railway_conn = connect_to_railway()
    
    def disconnect_databases(self):
        """Close database connections"""
        if hasattr(self, 'local_db_context') and self.local_db_context:
            try:
                self.local_db_context.__exit__(None, None, None)
            except:
                pass
        if self.railway_conn:
            try:
                self.railway_conn.close()
            except:
                pass
    
    def validate_mappings(self):
        """Validate that all mapped IDs exist in Railway"""
        logger.info("✅ Validating ID mappings...")
        
        railway_cursor = self.railway_conn.cursor()
        
        # Validate club mappings
        club_ids = list(self.club_mapping.values())
        if club_ids:
            railway_cursor.execute("SELECT id FROM clubs WHERE id = ANY(%s)", (club_ids,))
            valid_club_ids = {row[0] for row in railway_cursor.fetchall()}
            invalid_club_mappings = {k: v for k, v in self.club_mapping.items() if v not in valid_club_ids}
            
            if invalid_club_mappings:
                logger.error(f"❌ Invalid club mappings found: {invalid_club_mappings}")
                return False
        
        # Validate series mappings
        series_ids = [v for v in self.series_mapping.values() if v is not None]
        if series_ids:
            railway_cursor.execute("SELECT id FROM series WHERE id = ANY(%s)", (series_ids,))
            valid_series_ids = {row[0] for row in railway_cursor.fetchall()}
            invalid_series_mappings = {k: v for k, v in self.series_mapping.items() 
                                     if v is not None and v not in valid_series_ids}
            
            if invalid_series_mappings:
                logger.error(f"❌ Invalid series mappings found: {invalid_series_mappings}")
                return False
        
        logger.info("✅ All mappings validated successfully")
        return True
    
    def migrate_players_safe(self):
        """Safely migrate players with proper ID mapping"""
        logger.info("🏃 Migrating players with safe ID mapping...")
        
        local_cursor = self.local_conn.cursor()
        railway_cursor = self.railway_conn.cursor()
        
        # Get all players
        local_cursor.execute("SELECT * FROM players ORDER BY id")
        players = local_cursor.fetchall()
        
        # Get column names
        local_cursor.execute("SELECT * FROM players LIMIT 1")
        columns = [desc[0] for desc in local_cursor.description]
        columns_without_id = [col for col in columns if col != 'id']
        
        self.migration_stats['players']['attempted'] = len(players)
        
        for player_row in players:
            player_dict = dict(zip(columns, player_row))
            
            # Check if we can map the foreign keys
            original_club_id = player_dict['club_id']
            original_series_id = player_dict['series_id']
            
            skip_reasons = []
            
            # Map club_id
            if original_club_id is not None:
                if original_club_id in self.club_mapping:
                    player_dict['club_id'] = self.club_mapping[original_club_id]
                else:
                    skip_reasons.append(f"unmapped club_id {original_club_id}")
            
            # Map series_id
            if original_series_id is not None:
                if original_series_id in self.series_mapping:
                    mapped_series_id = self.series_mapping[original_series_id]
                    if mapped_series_id is not None:
                        player_dict['series_id'] = mapped_series_id
                    else:
                        skip_reasons.append(f"null-mapped series_id {original_series_id}")
                else:
                    skip_reasons.append(f"unmapped series_id {original_series_id}")
            
            # Skip if we can't map required foreign keys
            if skip_reasons:
                self.migration_stats['players']['skipped'] += 1
                logger.debug(f"  ⚠️  Skipped {player_dict['first_name']} {player_dict['last_name']}: {', '.join(skip_reasons)}")
                continue
            
            # Attempt to insert player
            try:
                placeholders = ', '.join(['%s'] * len(columns_without_id))
                column_names = ', '.join(columns_without_id)
                values = [player_dict[col] for col in columns_without_id]
                
                railway_cursor.execute(f"""
                    INSERT INTO players ({column_names}) 
                    VALUES ({placeholders})
                """, values)
                
                self.migration_stats['players']['migrated'] += 1
                
                if self.migration_stats['players']['migrated'] % 500 == 0:
                    logger.info(f"    ✅ Migrated {self.migration_stats['players']['migrated']} players...")
                    
            except Exception as e:
                self.migration_stats['players']['errors'].append({
                    'player': f"{player_dict['first_name']} {player_dict['last_name']}",
                    'error': str(e)
                })
                logger.error(f"  ❌ Failed to migrate {player_dict['first_name']} {player_dict['last_name']}: {e}")
        
        self.railway_conn.commit()
        logger.info(f"  ✅ Players migration: {self.migration_stats['players']['migrated']} migrated, {self.migration_stats['players']['skipped']} skipped")
        
        return self.migration_stats['players']['migrated'] > 0

def main():
    """Main migration process with comprehensive ID mapping"""
    logger.info("🔧 SAFE ID MAPPING MIGRATION")
    logger.info("="*80)
    
    # Step 1: Analyze ID mappings
    analyzer = IDMappingAnalyzer()
    try:
        analyzer.connect_databases()
        
        logger.info("\n📊 ANALYZING ID MAPPINGS...")
        club_mapping = analyzer.analyze_club_mapping()
        series_mapping = analyzer.analyze_series_mapping()
        
        # Create comprehensive report
        missing_plan = analyzer.create_missing_entities_plan()
        report_path = analyzer.save_mapping_report()
        
        logger.info(f"\n📋 MAPPING SUMMARY:")
        logger.info(f"  • Club mappings: {len(club_mapping)} successful")
        logger.info(f"  • Series mappings: {len([v for v in series_mapping.values() if v is not None])} successful")
        logger.info(f"  • Missing clubs: {len(missing_plan['missing_clubs'])}")
        logger.info(f"  • Missing series: {len(missing_plan['missing_series'])}")
        
        # Check if we have enough mappings to proceed
        local_cursor = analyzer.local_conn.cursor()
        local_cursor.execute("SELECT COUNT(DISTINCT club_id) FROM players WHERE club_id IS NOT NULL")
        unique_club_refs = local_cursor.fetchone()[0]
        
        local_cursor.execute("SELECT COUNT(DISTINCT series_id) FROM players WHERE series_id IS NOT NULL")
        unique_series_refs = local_cursor.fetchone()[0]
        
        mapped_clubs = len(club_mapping)
        mapped_series = len([v for v in series_mapping.values() if v is not None])
        
        logger.info(f"\n🎯 MIGRATION FEASIBILITY:")
        logger.info(f"  • Players reference {unique_club_refs} unique clubs, we can map {mapped_clubs}")
        logger.info(f"  • Players reference {unique_series_refs} unique series, we can map {mapped_series}")
        
        if mapped_clubs == 0 and unique_club_refs > 0:
            logger.error("❌ Cannot proceed: No club mappings available")
            return False
        
    finally:
        analyzer.disconnect_databases()
    
    # Step 2: Safe migration with mappings
    migrator = SafeMigrator(club_mapping, series_mapping)
    try:
        migrator.connect_databases()
        
        logger.info(f"\n🔄 STARTING SAFE MIGRATION...")
        
        # Validate mappings first
        if not migrator.validate_mappings():
            logger.error("❌ Mapping validation failed")
            return False
        
        # Migrate players
        success = migrator.migrate_players_safe()
        
        if success:
            logger.info(f"\n✅ MIGRATION COMPLETED SUCCESSFULLY!")
            logger.info(f"📊 Final Stats:")
            for table, stats in migrator.migration_stats.items():
                logger.info(f"  • {table}: {stats['migrated']} migrated, {stats['skipped']} skipped")
        else:
            logger.error("❌ Migration failed or no data migrated")
            
        return success
        
    finally:
        migrator.disconnect_databases()

if __name__ == "__main__":
    success = main()
    logger.info(f"\n🎯 NEXT STEPS:")
    logger.info(f"  1. Review mapping report: scripts/mapping_analysis_report.json")
    logger.info(f"  2. Run data verification: python scripts/compare_data_content.py")
    logger.info(f"  3. Test Railway application: https://www.lovetorally.com")
    sys.exit(0 if success else 1) 