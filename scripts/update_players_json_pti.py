#!/usr/bin/env python3
"""
Update APTA Chicago players.json with PTI values from players_reference.json
This script synchronizes the local JSON file with the updated PTI values.

Usage:
    python scripts/update_players_json_pti.py --dry-run    # Preview changes
    python scripts/update_players_json_pti.py --execute    # Apply changes
"""

import json
import sys
import os
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Optional

# File paths
REFERENCE_FILE = "data/leagues/APTA_CHICAGO/players_reference.json"
PLAYERS_FILE = "data/leagues/APTA_CHICAGO/players.json"
BACKUP_DIR = "backups"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/players_json_pti_update_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PlayersJSONPTIUpdater:
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.reference_data = {}
        self.players_data = []
        self.total_processed = 0
        self.successful_updates = 0
        self.failed_updates = 0
        self.not_found = 0
        self.skipped_no_pti = 0
        
    def load_reference_data(self) -> Dict[str, Dict]:
        """Load PTI data from reference file and create lookup dictionary"""
        if not os.path.exists(REFERENCE_FILE):
            raise FileNotFoundError(f"Reference file not found: {REFERENCE_FILE}")
        
        try:
            with open(REFERENCE_FILE, 'r') as file:
                data = json.load(file)
                logger.info(f"📊 Loaded {len(data)} players from reference file")
                
                # Create lookup dictionary by Player ID
                reference_lookup = {}
                for player in data:
                    player_id = player.get('Player ID', '').strip()
                    pti_value = player.get('PTI', '').strip()
                    
                    if player_id and pti_value and pti_value != 'N/A':
                        try:
                            pti_float = float(pti_value)
                            reference_lookup[player_id] = {
                                'PTI': pti_float,
                                'First Name': player.get('First Name', ''),
                                'Last Name': player.get('Last Name', ''),
                                'Club': player.get('Club', ''),
                                'Series': player.get('Series', '')
                            }
                        except (ValueError, TypeError):
                            logger.warning(f"⚠️  Invalid PTI value for {player.get('First Name', '')} {player.get('Last Name', '')}: {pti_value}")
                
                logger.info(f"📊 Created lookup for {len(reference_lookup)} players with valid PTI values")
                return reference_lookup
                
        except Exception as e:
            logger.error(f"❌ Error reading reference file: {e}")
            raise
    
    def load_players_data(self) -> List[Dict]:
        """Load players data from JSON file"""
        if not os.path.exists(PLAYERS_FILE):
            raise FileNotFoundError(f"Players file not found: {PLAYERS_FILE}")
        
        try:
            with open(PLAYERS_FILE, 'r') as file:
                data = json.load(file)
                logger.info(f"📊 Loaded {len(data)} players from players.json")
                return data
        except Exception as e:
            logger.error(f"❌ Error reading players file: {e}")
            raise
    
    def create_backup(self):
        """Create backup of original players.json file"""
        os.makedirs(BACKUP_DIR, exist_ok=True)
        
        backup_filename = f"{BACKUP_DIR}/players_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(PLAYERS_FILE, 'r') as source:
                with open(backup_filename, 'w') as backup:
                    backup.write(source.read())
            
            logger.info(f"💾 Backup created: {backup_filename}")
            return backup_filename
        except Exception as e:
            logger.error(f"❌ Failed to create backup: {e}")
            raise
    
    def update_players_pti(self, reference_lookup: Dict[str, Dict]):
        """Update PTI values in players data"""
        logger.info("🔄 Starting PTI updates in players.json...")
        
        for player in self.players_data:
            self.total_processed += 1
            
            player_id = player.get('Player ID', '').strip()
            first_name = player.get('First Name', '')
            last_name = player.get('Last Name', '')
            
            if not player_id:
                continue
            
            # Check if player exists in reference data
            if player_id in reference_lookup:
                reference_player = reference_lookup[player_id]
                new_pti = reference_player['PTI']
                current_pti = player.get('PTI')
                
                # Check if PTI needs updating
                needs_update = False
                old_pti = current_pti
                
                if current_pti is None or current_pti == 'N/A' or current_pti == '':
                    needs_update = True
                else:
                    try:
                        current_pti_float = float(current_pti)
                        if abs(current_pti_float - new_pti) > 0.01:
                            needs_update = True
                    except (ValueError, TypeError):
                        needs_update = True
                
                if needs_update:
                    player['PTI'] = str(new_pti)  # Store as string to match JSON format
                    self.successful_updates += 1
                    
                    if self.successful_updates <= 10:  # Log first 10 updates
                        logger.info(f"✅ Updated {first_name} {last_name}: {old_pti} -> {new_pti}")
                else:
                    # PTI is essentially the same, skip
                    pass
            else:
                self.not_found += 1
                if self.not_found <= 10:  # Log first 10 not found
                    logger.warning(f"⚠️  Player not found in reference: {first_name} {last_name} (ID: {player_id})")
            
            # Progress logging
            if self.total_processed % 1000 == 0:
                logger.info(f"📊 Progress: {self.total_processed}/{len(self.players_data)} processed | "
                          f"Updated: {self.successful_updates} | Not found: {self.not_found}")
    
    def save_updated_players(self):
        """Save updated players data to JSON file"""
        if self.dry_run:
            logger.info("🔍 DRY RUN: Would save updated players.json")
            return
        
        try:
            # Create backup first
            self.create_backup()
            
            # Save updated data
            with open(PLAYERS_FILE, 'w') as file:
                json.dump(self.players_data, file, indent=2)
            
            logger.info(f"💾 Updated players.json saved successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to save updated players.json: {e}")
            raise
    
    def create_summary_report(self):
        """Create a summary report of the update process"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'mode': 'DRY RUN' if self.dry_run else 'EXECUTE',
            'file': 'players.json',
            'total_processed': self.total_processed,
            'successful_updates': self.successful_updates,
            'failed_updates': self.failed_updates,
            'not_found': self.not_found,
            'skipped_no_pti': self.skipped_no_pti,
            'success_rate': (self.successful_updates / max(self.total_processed, 1)) * 100
        }
        
        # Save report to file
        report_filename = f"{BACKUP_DIR}/players_json_pti_update_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info("📊 PLAYERS.JSON UPDATE SUMMARY:")
        logger.info(f"   Total players processed: {self.total_processed}")
        logger.info(f"   Successful updates: {self.successful_updates}")
        logger.info(f"   Failed updates: {self.failed_updates}")
        logger.info(f"   Players not found: {self.not_found}")
        logger.info(f"   Skipped (no PTI): {self.skipped_no_pti}")
        logger.info(f"   Success rate: {report['success_rate']:.1f}%")
        logger.info(f"   Report saved: {report_filename}")
    
    def run(self):
        """Main execution method"""
        try:
            logger.info("🚀 Starting players.json PTI update from reference file")
            logger.info(f"🔧 Mode: {'DRY RUN' if self.dry_run else 'EXECUTE'}")
            logger.info(f"📁 Reference File: {REFERENCE_FILE}")
            logger.info(f"📁 Target File: {PLAYERS_FILE}")
            
            # Load reference data
            reference_lookup = self.load_reference_data()
            
            # Load players data
            self.players_data = self.load_players_data()
            
            # Update PTI values
            self.update_players_pti(reference_lookup)
            
            # Save updated data
            self.save_updated_players()
            
            # Create summary report
            self.create_summary_report()
            
            logger.info("🎉 players.json PTI update process completed successfully")
            
        except Exception as e:
            logger.error(f"❌ players.json PTI update failed: {e}")
            raise

def main():
    parser = argparse.ArgumentParser(description='Update players.json with PTI values from reference file')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying them')
    parser.add_argument('--execute', action='store_true', help='Apply changes to players.json')
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.execute:
        print("❌ Please specify either --dry-run or --execute")
        sys.exit(1)
        
    if args.dry_run and args.execute:
        print("❌ Please specify only one of --dry-run or --execute")
        sys.exit(1)
    
    dry_run = args.dry_run
    
    try:
        updater = PlayersJSONPTIUpdater(dry_run=dry_run)
        updater.run()
    except Exception as e:
        logger.error(f"❌ Script failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
