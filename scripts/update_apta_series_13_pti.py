#!/usr/bin/env python3
"""
Safe PTI Update Script for APTA Chicago Series 13 Tennaqua Players
Updates PTI values from tennaqua_13_roster.csv to production database with comprehensive safety checks.
Only updates players from Tennaqua club in APTA Chicago Series 13.

Usage:
    python scripts/update_apta_series_13_pti.py --dry-run    # Preview changes
    python scripts/update_apta_series_13_pti.py --execute    # Apply changes
"""

import csv
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

# CSV file path
CSV_FILE_PATH = "tennaqua_13_roster.csv"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/apta_pti_update_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PTIUpdater:
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.connection = None
        self.cursor = None
        self.apta_league_id = None
        self.series_13_id = None
        self.tennaqua_club_id = None
        
    def connect_to_database(self):
        """Connect to production database"""
        try:
            self.connection = psycopg2.connect(PRODUCTION_DB_URL)
            self.cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            logger.info("✅ Connected to production database")
            
            # Get APTA Chicago league ID
            self.cursor.execute("SELECT id FROM leagues WHERE league_id = 'APTA_CHICAGO'")
            result = self.cursor.fetchone()
            if not result:
                raise Exception("APTA_CHICAGO league not found in database")
            self.apta_league_id = result['id']
            logger.info(f"📊 APTA Chicago League ID: {self.apta_league_id}")
            
            # Get Series 13 ID
            self.cursor.execute("SELECT id FROM series WHERE name = 'Series 13'")
            result = self.cursor.fetchone()
            if not result:
                raise Exception("Series 13 not found in database")
            self.series_13_id = result['id']
            logger.info(f"📊 Series 13 ID: {self.series_13_id}")
            
            # Get Tennaqua club ID
            self.cursor.execute("SELECT id FROM clubs WHERE name = 'Tennaqua'")
            result = self.cursor.fetchone()
            if not result:
                raise Exception("Tennaqua club not found in database")
            self.tennaqua_club_id = result['id']
            logger.info(f"📊 Tennaqua Club ID: {self.tennaqua_club_id}")
            
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise
    
    def load_csv_data(self) -> Dict[str, float]:
        """Load PTI data from CSV file"""
        pti_data = {}
        
        if not os.path.exists(CSV_FILE_PATH):
            raise FileNotFoundError(f"CSV file not found: {CSV_FILE_PATH}")
        
        try:
            with open(CSV_FILE_PATH, 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    name = row['Name'].strip()
                    pti_str = row['PTI'].strip()
                    
                    try:
                        pti_value = float(pti_str)
                        pti_data[name] = pti_value
                        logger.info(f"📋 Loaded: {name} -> PTI {pti_value}")
                    except ValueError:
                        logger.warning(f"⚠️  Invalid PTI value for {name}: {pti_str}")
                        
        except Exception as e:
            logger.error(f"❌ Error reading CSV file: {e}")
            raise
            
        logger.info(f"📊 Loaded {len(pti_data)} players from CSV")
        return pti_data
    
    def find_matching_players(self, pti_data: Dict[str, float]) -> List[Dict]:
        """Find matching players in database for APTA Chicago Series 13 Tennaqua players only"""
        matches = []
        
        for name, new_pti in pti_data.items():
            # Parse name (handle cases like "Jamie Silverman (CC)")
            clean_name = name.split('(')[0].strip()
            name_parts = clean_name.split()
            
            if len(name_parts) < 2:
                logger.warning(f"⚠️  Invalid name format: {name}")
                continue
                
            first_name = name_parts[0]
            last_name = ' '.join(name_parts[1:])
            
            # Search for player in APTA Chicago Series 13 TENNAQUA ONLY
            query = """
                SELECT p.id, p.first_name, p.last_name, p.tenniscores_player_id, 
                       p.pti as current_pti, t.team_name, c.name as club_name
                FROM players p
                JOIN teams t ON p.team_id = t.id
                JOIN clubs c ON p.club_id = c.id
                WHERE p.league_id = %s 
                AND p.series_id = %s
                AND p.club_id = %s
                AND p.first_name ILIKE %s 
                AND p.last_name ILIKE %s
                AND p.is_active = true
            """
            
            self.cursor.execute(query, [
                self.apta_league_id,
                self.series_13_id,
                self.tennaqua_club_id,
                f"%{first_name}%",
                f"%{last_name}%"
            ])
            
            results = self.cursor.fetchall()
            
            if len(results) == 1:
                player = results[0]
                player['new_pti'] = new_pti
                player['original_name'] = name
                matches.append(player)
                logger.info(f"✅ Found match: {name} -> {player['first_name']} {player['last_name']} (ID: {player['id']})")
                
            elif len(results) > 1:
                logger.warning(f"⚠️  Multiple matches for {name}:")
                for result in results:
                    logger.warning(f"    - {result['first_name']} {result['last_name']} (ID: {result['id']})")
                    
            else:
                logger.warning(f"❌ No match found for {name}")
                
        return matches
    
    def create_backup(self, matches: List[Dict]):
        """Create backup of current PTI values"""
        if not matches:
            return
            
        backup_data = []
        for match in matches:
            backup_data.append({
                'player_id': match['id'],
                'first_name': match['first_name'],
                'last_name': match['last_name'],
                'current_pti': match['current_pti'],
                'new_pti': match['new_pti'],
                'timestamp': datetime.now().isoformat()
            })
        
        # Save backup to file
        backup_filename = f"backups/apta_pti_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        os.makedirs('backups', exist_ok=True)
        
        with open(backup_filename, 'w', newline='') as file:
            if backup_data:
                writer = csv.DictWriter(file, fieldnames=backup_data[0].keys())
                writer.writeheader()
                writer.writerows(backup_data)
                
        logger.info(f"💾 Backup created: {backup_filename}")
    
    def update_pti_values(self, matches: List[Dict]):
        """Update PTI values in database"""
        if not matches:
            logger.info("📊 No players to update")
            return
            
        updated_count = 0
        
        for match in matches:
            player_id = match['id']
            new_pti = match['new_pti']
            current_pti = match['current_pti']
            
            logger.info(f"🔄 Updating {match['first_name']} {match['last_name']}: {current_pti} -> {new_pti}")
            
            if not self.dry_run:
                try:
                    update_query = """
                        UPDATE players 
                        SET pti = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """
                    self.cursor.execute(update_query, [new_pti, player_id])
                    updated_count += 1
                    
                except Exception as e:
                    logger.error(f"❌ Failed to update {match['first_name']} {match['last_name']}: {e}")
            else:
                updated_count += 1
                
        if not self.dry_run:
            self.connection.commit()
            logger.info(f"✅ Successfully updated {updated_count} players")
        else:
            logger.info(f"🔍 DRY RUN: Would update {updated_count} players")
    
    def verify_updates(self, matches: List[Dict]):
        """Verify that updates were applied correctly"""
        if self.dry_run:
            logger.info("🔍 DRY RUN: Skipping verification")
            return
            
        logger.info("🔍 Verifying updates...")
        
        for match in matches:
            player_id = match['id']
            expected_pti = match['new_pti']
            
            self.cursor.execute("SELECT pti FROM players WHERE id = %s", [player_id])
            result = self.cursor.fetchone()
            
            if result and result['pti'] == expected_pti:
                logger.info(f"✅ Verified: {match['first_name']} {match['last_name']} PTI = {result['pti']}")
            else:
                logger.error(f"❌ Verification failed: {match['first_name']} {match['last_name']} - Expected: {expected_pti}, Got: {result['pti'] if result else 'None'}")
    
    def run(self):
        """Main execution method"""
        try:
            logger.info("🚀 Starting APTA Chicago Series 13 Tennaqua PTI Update")
            logger.info(f"🔧 Mode: {'DRY RUN' if self.dry_run else 'EXECUTE'}")
            logger.info(f"📁 CSV File: {CSV_FILE_PATH}")
            logger.info(f"🏢 Target: Tennaqua club players only")
            
            # Connect to database
            self.connect_to_database()
            
            # Load CSV data
            pti_data = self.load_csv_data()
            
            # Find matching players
            matches = self.find_matching_players(pti_data)
            
            if not matches:
                logger.warning("⚠️  No matching players found")
                return
                
            logger.info(f"📊 Found {len(matches)} matching players to update")
            
            # Create backup
            self.create_backup(matches)
            
            # Update PTI values
            self.update_pti_values(matches)
            
            # Verify updates
            self.verify_updates(matches)
            
            logger.info("🎉 PTI update process completed successfully")
            
        except Exception as e:
            logger.error(f"❌ PTI update failed: {e}")
            if self.connection:
                self.connection.rollback()
            raise
        finally:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()

def main():
    parser = argparse.ArgumentParser(description='Update APTA Chicago Series 13 Tennaqua PTI values')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying them')
    parser.add_argument('--execute', action='store_true', help='Apply changes to database')
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.execute:
        print("❌ Please specify either --dry-run or --execute")
        sys.exit(1)
        
    if args.dry_run and args.execute:
        print("❌ Please specify only one of --dry-run or --execute")
        sys.exit(1)
    
    dry_run = args.dry_run
    
    try:
        updater = PTIUpdater(dry_run=dry_run)
        updater.run()
    except Exception as e:
        logger.error(f"❌ Script failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
