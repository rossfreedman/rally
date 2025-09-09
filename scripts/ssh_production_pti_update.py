#!/usr/bin/env python3
"""
SSH Production PTI Update Script for APTA Chicago Players
Optimized for running via SSH on production server.

This script should be run on the production server via SSH to avoid network timeouts.

Usage on production server:
    python3 ssh_production_pti_update.py --dry-run    # Preview changes
    python3 ssh_production_pti_update.py --execute    # Apply changes
"""

import json
import sys
import os
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

# Production database connection (local on server)
PRODUCTION_DB_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

# Reference file path (should be uploaded to server)
REFERENCE_FILE_PATH = "players_reference.json"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'production_pti_update_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SSHProductionPTIUpdater:
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
    
    def batch_update_pti(self, updates: List[Dict]):
        """Perform batch PTI updates for better performance"""
        if not updates:
            return
            
        logger.info(f"🔄 Updating {len(updates)} players in batch...")
        
        # Use batch update for better performance
        update_query = """
            UPDATE players 
            SET pti = data.new_pti, updated_at = CURRENT_TIMESTAMP
            FROM (VALUES %s) AS data(player_id, new_pti)
            WHERE players.tenniscores_player_id = data.player_id 
            AND players.league_id = %s
        """
        
        # Prepare batch data
        batch_data = []
        for update in updates:
            batch_data.append((update['tenniscores_player_id'], update['new_pti']))
        
        try:
            if not self.dry_run:
                # Use psycopg2's execute_values for efficient batch updates
                from psycopg2.extras import execute_values
                execute_values(
                    self.cursor,
                    update_query.replace('%s', '%s'),
                    batch_data,
                    template=None,
                    page_size=1000
                )
                self.connection.commit()
            
            self.successful_updates += len(updates)
            logger.info(f"✅ Batch updated {len(updates)} players")
            
        except Exception as e:
            logger.error(f"❌ Batch update failed: {e}")
            # Fallback to individual updates
            for update in updates:
                try:
                    individual_query = """
                        UPDATE players 
                        SET pti = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE tenniscores_player_id = %s AND league_id = %s
                    """
                    if not self.dry_run:
                        self.cursor.execute(individual_query, [
                            update['new_pti'], 
                            update['tenniscores_player_id'], 
                            self.apta_league_id
                        ])
                        self.connection.commit()
                    self.successful_updates += 1
                except Exception as individual_error:
                    logger.error(f"❌ Failed to update {update.get('first_name', '')} {update.get('last_name', '')}: {individual_error}")
                    self.failed_updates += 1
    
    def process_players_optimized(self, players_data: List[Dict]):
        """Optimized processing with batch updates"""
        logger.info("🚀 Starting optimized PTI update process for PRODUCTION")
        
        # Collect all updates first
        updates_to_process = []
        batch_size = 1000
        
        logger.info("🔍 Collecting players that need PTI updates...")
        
        for i, player_info in enumerate(players_data):
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
            query = """
                SELECT p.id, p.tenniscores_player_id, p.pti as current_pti
                FROM players p
                WHERE p.tenniscores_player_id = %s 
                AND p.league_id = %s
                AND p.is_active = true
            """
            
            self.cursor.execute(query, [player_id, self.apta_league_id])
            db_player = self.cursor.fetchone()
            
            if not db_player:
                self.not_found += 1
                continue
            
            # Check if PTI needs updating
            current_pti = db_player['current_pti']
            if current_pti is not None and abs(float(current_pti) - new_pti) < 0.01:
                self.skipped_same_pti += 1
                continue
            
            # Add to updates
            updates_to_process.append({
                'tenniscores_player_id': player_id,
                'new_pti': new_pti,
                'first_name': first_name,
                'last_name': last_name,
                'current_pti': current_pti
            })
            
            # Progress logging
            if self.total_processed % 1000 == 0:
                logger.info(f"📊 Progress: {self.total_processed}/{len(players_data)} | "
                          f"To update: {len(updates_to_process)} | Not found: {self.not_found}")
        
        logger.info(f"🔍 Collection complete: {len(updates_to_process)} players need updates")
        
        # Process updates in batches
        total_batches = (len(updates_to_process) + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(updates_to_process))
            batch_updates = updates_to_process[start_idx:end_idx]
            
            logger.info(f"📦 Processing batch {batch_num + 1}/{total_batches} ({len(batch_updates)} players)")
            
            # Log first few updates in each batch
            for update in batch_updates[:5]:
                logger.info(f"🔄 {update['first_name']} {update['last_name']}: {update['current_pti']} -> {update['new_pti']}")
            
            self.batch_update_pti(batch_updates)
    
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
        report_filename = f"production_pti_update_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
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
            logger.info("🚀 Starting SSH PRODUCTION APTA Chicago PTI Update")
            logger.info(f"🔧 Mode: {'DRY RUN' if self.dry_run else 'EXECUTE'}")
            logger.info(f"📁 Reference File: {REFERENCE_FILE_PATH}")
            logger.info(f"🗄️  Target Database: PRODUCTION")
            
            # Connect to database
            self.connect_to_database()
            
            # Load reference data
            players_data = self.load_reference_data()
            
            # Process players with optimized batch updates
            self.process_players_optimized(players_data)
            
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
    parser = argparse.ArgumentParser(description='SSH Production APTA Chicago PTI Update')
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
        updater = SSHProductionPTIUpdater(dry_run=dry_run)
        updater.run()
    except Exception as e:
        logger.error(f"❌ Script failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
