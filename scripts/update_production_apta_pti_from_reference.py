#!/usr/bin/env python3
"""
Production PTI Update Script for All APTA Chicago Players
Updates PTI values from players_reference.json to PRODUCTION database using Player ID matching.

This script processes 6,837 players and updates PTI values for those with valid data.

Usage:
    python scripts/update_production_apta_pti_from_reference.py --dry-run    # Preview changes
    python scripts/update_production_apta_pti_from_reference.py --execute    # Apply changes
"""

import json
import sys
import os
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Production database connection
PRODUCTION_DB_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

# Reference file path
REFERENCE_FILE_PATH = "data/leagues/APTA_CHICAGO/players_reference.json"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/production_apta_pti_update_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ProductionAPTAPTIUpdater:
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.connection = None
        self.cursor = None
        self.apta_league_id = None
        self.total_processed = 0
        self.successful_updates = 0
        self.failed_updates = 0
        self.skipped_no_pti = 0
        self.not_found = 0
        self.skipped_same_pti = 0
        
    def connect_to_database(self):
        """Connect to production database"""
        try:
            self.connection = psycopg2.connect(PRODUCTION_DB_URL)
            self.cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            logger.info("✅ Connected to PRODUCTION database")
            
            # Get APTA Chicago league ID
            self.cursor.execute("SELECT id FROM leagues WHERE league_id = 'APTA_CHICAGO'")
            result = self.cursor.fetchone()
            if not result:
                raise Exception("APTA_CHICAGO league not found in database")
            self.apta_league_id = result['id']
            logger.info(f"📊 APTA Chicago League ID: {self.apta_league_id}")
            
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise
    
    def load_reference_data(self) -> List[Dict]:
        """Load player data from reference JSON file"""
        if not os.path.exists(REFERENCE_FILE_PATH):
            raise FileNotFoundError(f"Reference file not found: {REFERENCE_FILE_PATH}")
        
        try:
            with open(REFERENCE_FILE_PATH, 'r') as file:
                data = json.load(file)
                logger.info(f"📊 Loaded {len(data)} players from reference file")
                return data
        except Exception as e:
            logger.error(f"❌ Error reading reference file: {e}")
            raise
    
    def is_valid_pti(self, pti_value: str) -> bool:
        """Check if PTI value is valid and numeric"""
        if not pti_value or pti_value == "N/A":
            return False
        try:
            float(pti_value)
            return True
        except (ValueError, TypeError):
            return False
    
    def find_player_by_id(self, player_id: str) -> Optional[Dict]:
        """Find player in database by tenniscores_player_id"""
        query = """
            SELECT p.id, p.first_name, p.last_name, p.tenniscores_player_id, 
                   p.pti as current_pti, t.team_name, c.name as club_name, s.name as series_name
            FROM players p
            LEFT JOIN teams t ON p.team_id = t.id
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE p.tenniscores_player_id = %s 
            AND p.league_id = %s
            AND p.is_active = true
        """
        
        self.cursor.execute(query, [player_id, self.apta_league_id])
        return self.cursor.fetchone()
    
    def update_player_pti(self, player_id: str, new_pti: float, player_info: Dict) -> bool:
        """Update PTI value for a specific player"""
        try:
            update_query = """
                UPDATE players 
                SET pti = %s, updated_at = CURRENT_TIMESTAMP
                WHERE tenniscores_player_id = %s AND league_id = %s
            """
            
            if not self.dry_run:
                self.cursor.execute(update_query, [new_pti, player_id, self.apta_league_id])
                self.connection.commit()
            
            return True
        except Exception as e:
            logger.error(f"❌ Failed to update {player_info.get('First Name', '')} {player_info.get('Last Name', '')} (ID: {player_id}): {e}")
            return False
    
    def create_backup(self, players_to_update: List[Dict]):
        """Create backup of current PTI values for players that will be updated"""
        if not players_to_update:
            return
            
        backup_data = []
        for player in players_to_update:
            backup_data.append({
                'player_id': player['id'],
                'tenniscores_player_id': player['tenniscores_player_id'],
                'first_name': player['first_name'],
                'last_name': player['last_name'],
                'current_pti': player['current_pti'],
                'new_pti': player['new_pti'],
                'team_name': player['team_name'],
                'club_name': player['club_name'],
                'series_name': player['series_name'],
                'timestamp': datetime.now().isoformat()
            })
        
        # Save backup to file
        backup_filename = f"backups/production_apta_pti_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs('backups', exist_ok=True)
        
        with open(backup_filename, 'w') as file:
            json.dump(backup_data, file, indent=2)
                
        logger.info(f"💾 Backup created: {backup_filename}")
        logger.info(f"💾 Backed up {len(backup_data)} players")
    
    def process_players(self, players_data: List[Dict]):
        """Process all players and update PTI values"""
        logger.info("🚀 Starting PTI update process for all APTA Chicago players in PRODUCTION")
        
        # First pass: identify players that need updates
        players_to_update = []
        
        # Process in batches for better performance
        batch_size = 100
        total_batches = (len(players_data) + batch_size - 1) // batch_size
        
        logger.info("🔍 First pass: Identifying players that need PTI updates...")
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(players_data))
            batch_players = players_data[start_idx:end_idx]
            
            for player_info in batch_players:
                self.total_processed += 1
                
                # Extract player data
                player_id = player_info.get('Player ID', '').strip()
                pti_str = player_info.get('PTI', '').strip()
                first_name = player_info.get('First Name', '').strip()
                last_name = player_info.get('Last Name', '').strip()
                
                # Skip if no valid PTI
                if not self.is_valid_pti(pti_str):
                    self.skipped_no_pti += 1
                    continue
                
                try:
                    new_pti = float(pti_str)
                except (ValueError, TypeError):
                    self.skipped_no_pti += 1
                    continue
                
                # Find player in database
                db_player = self.find_player_by_id(player_id)
                
                if not db_player:
                    self.not_found += 1
                    continue
                
                # Check if PTI needs updating
                current_pti = db_player['current_pti']
                if current_pti is not None and abs(float(current_pti) - new_pti) < 0.01:
                    # PTI is essentially the same, skip
                    self.skipped_same_pti += 1
                    continue
                
                # Add to update list
                db_player['new_pti'] = new_pti
                players_to_update.append(db_player)
                
                # Progress logging
                if self.total_processed % 1000 == 0:
                    logger.info(f"📊 Progress: {self.total_processed}/{len(players_data)} processed | "
                              f"To update: {len(players_to_update)} | Not found: {self.not_found} | "
                              f"No PTI: {self.skipped_no_pti} | Same PTI: {self.skipped_same_pti}")
        
        logger.info(f"🔍 First pass complete: {len(players_to_update)} players need PTI updates")
        
        # Create backup of players that will be updated
        if players_to_update:
            self.create_backup(players_to_update)
        
        # Second pass: perform updates
        logger.info("🔄 Second pass: Updating PTI values...")
        
        for player in players_to_update:
            player_id = player['tenniscores_player_id']
            new_pti = player['new_pti']
            
            if self.update_player_pti(player_id, new_pti, player):
                self.successful_updates += 1
                if self.successful_updates <= 10:  # Log first 10 updates
                    logger.info(f"✅ Updated {player['first_name']} {player['last_name']}: {player['current_pti']} -> {new_pti}")
            else:
                self.failed_updates += 1
            
            # Progress logging
            if (self.successful_updates + self.failed_updates) % 500 == 0:
                logger.info(f"📊 Update progress: {self.successful_updates + self.failed_updates}/{len(players_to_update)} completed")
    
    def create_summary_report(self):
        """Create a summary report of the update process"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'mode': 'DRY RUN' if self.dry_run else 'EXECUTE',
            'database': 'PRODUCTION',
            'total_processed': self.total_processed,
            'successful_updates': self.successful_updates,
            'failed_updates': self.failed_updates,
            'not_found': self.not_found,
            'skipped_no_pti': self.skipped_no_pti,
            'skipped_same_pti': self.skipped_same_pti,
            'success_rate': (self.successful_updates / max(self.total_processed, 1)) * 100
        }
        
        # Save report to file
        report_filename = f"backups/production_apta_pti_update_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info("📊 PRODUCTION UPDATE SUMMARY:")
        logger.info(f"   Total players processed: {self.total_processed}")
        logger.info(f"   Successful updates: {self.successful_updates}")
        logger.info(f"   Failed updates: {self.failed_updates}")
        logger.info(f"   Players not found: {self.not_found}")
        logger.info(f"   Skipped (no PTI): {self.skipped_no_pti}")
        logger.info(f"   Skipped (same PTI): {self.skipped_same_pti}")
        logger.info(f"   Success rate: {report['success_rate']:.1f}%")
        logger.info(f"   Report saved: {report_filename}")
    
    def run(self):
        """Main execution method"""
        try:
            logger.info("🚀 Starting PRODUCTION APTA Chicago PTI Update from Reference File")
            logger.info(f"🔧 Mode: {'DRY RUN' if self.dry_run else 'EXECUTE'}")
            logger.info(f"📁 Reference File: {REFERENCE_FILE_PATH}")
            logger.info(f"🗄️  Target Database: PRODUCTION")
            
            # Connect to database
            self.connect_to_database()
            
            # Load reference data
            players_data = self.load_reference_data()
            
            # Process players
            self.process_players(players_data)
            
            # Create summary report
            self.create_summary_report()
            
            logger.info("🎉 PRODUCTION PTI update process completed successfully")
            
        except Exception as e:
            logger.error(f"❌ PRODUCTION PTI update failed: {e}")
            if self.connection:
                self.connection.rollback()
            raise
        finally:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()

def main():
    parser = argparse.ArgumentParser(description='Update PRODUCTION APTA Chicago PTI values from reference file')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying them')
    parser.add_argument('--execute', action='store_true', help='Apply changes to PRODUCTION database')
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.execute:
        print("❌ Please specify either --dry-run or --execute")
        sys.exit(1)
        
    if args.dry_run and args.execute:
        print("❌ Please specify only one of --dry-run or --execute")
        sys.exit(1)
    
    dry_run = args.dry_run
    
    # Safety confirmation for production
    if not dry_run:
        print("⚠️  WARNING: You are about to update the PRODUCTION database!")
        print("This will modify PTI values for APTA Chicago players.")
        confirmation = input("Type 'YES' to confirm: ")
        if confirmation != 'YES':
            print("❌ Operation cancelled")
            sys.exit(1)
    
    try:
        updater = ProductionAPTAPTIUpdater(dry_run=dry_run)
        updater.run()
    except Exception as e:
        logger.error(f"❌ Script failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
