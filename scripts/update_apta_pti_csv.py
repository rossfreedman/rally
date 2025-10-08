#!/usr/bin/env python3
"""
Script to update the APTA Players CSV file with new PTI data from players.json
"""

import os
import sys
import json
import csv
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Add project root to path
sys.path.append(os.getcwd())

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'update_pti_csv_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)

class APTAPTIUpdater:
    """Updates APTA Players CSV with PTI data from JSON file."""
    
    def __init__(self, csv_file: str = "data/APTA Players - 2025 Season Starting PTI.csv", 
                 json_file: str = "data/leagues/APTA_CHICAGO/players.json"):
        """Initialize the updater."""
        self.csv_file = csv_file
        self.json_file = json_file
        self.csv_players = []
        self.json_players = []
        self.updated_players = []
        self.matched_count = 0
        self.unmatched_csv = []
        self.unmatched_json = []
        
        logger.info(f"🚀 APTA PTI CSV Updater initialized")
        logger.info(f"   CSV file: {self.csv_file}")
        logger.info(f"   JSON file: {self.json_file}")
    
    def load_csv_data(self) -> List[Dict[str, str]]:
        """Load player data from CSV file."""
        try:
            with open(self.csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                players = list(reader)
            
            logger.info(f"📄 Loaded {len(players)} players from CSV")
            return players
            
        except FileNotFoundError:
            logger.error(f"❌ CSV file not found: {self.csv_file}")
            return []
        except Exception as e:
            logger.error(f"❌ Error loading CSV file: {e}")
            return []
    
    def load_json_data(self) -> List[Dict]:
        """Load player data from JSON file."""
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            # Flatten the data structure if needed
            players = []
            for item in raw_data:
                if isinstance(item, list):
                    players.extend(item)
                elif isinstance(item, dict):
                    players.append(item)
            
            logger.info(f"📄 Loaded {len(players)} players from JSON")
            return players
            
        except FileNotFoundError:
            logger.error(f"❌ JSON file not found: {self.json_file}")
            return []
        except Exception as e:
            logger.error(f"❌ Error loading JSON file: {e}")
            return []
    
    def normalize_name(self, name: str) -> str:
        """Normalize name for matching (lowercase, strip whitespace)."""
        return name.lower().strip() if name else ""
    
    def normalize_club(self, club: str) -> str:
        """Normalize club name for matching."""
        if not club:
            return ""
        # Remove common suffixes and normalize
        club = club.lower().strip()
        club = club.replace(" club", "").replace(" country club", "").replace(" tennis club", "")
        return club
    
    def normalize_series(self, series: str) -> str:
        """Normalize series name for matching."""
        if not series:
            return ""
        return series.lower().strip()
    
    def find_json_match(self, csv_player: Dict[str, str]) -> Optional[Dict]:
        """Find matching player in JSON data."""
        csv_first = self.normalize_name(csv_player.get('First Name', ''))
        csv_last = self.normalize_name(csv_player.get('Last Name', ''))
        csv_club = self.normalize_club(csv_player.get('Club', ''))
        csv_series = self.normalize_series(csv_player.get('Series', ''))
        
        for json_player in self.json_players:
            json_first = self.normalize_name(json_player.get('First Name', ''))
            json_last = self.normalize_name(json_player.get('Last Name', ''))
            json_club = self.normalize_club(json_player.get('Club', ''))
            json_series = self.normalize_series(json_player.get('Series', ''))
            
            # Exact match on name and club
            if (csv_first == json_first and csv_last == json_last and 
                csv_club == json_club and csv_series == json_series):
                return json_player
            
            # Close match on name and club (ignoring series differences)
            if (csv_first == json_first and csv_last == json_last and 
                csv_club == json_club):
                logger.warning(f"⚠️ Series mismatch for {csv_first} {csv_last} ({csv_club}): CSV='{csv_series}' vs JSON='{json_series}'")
                return json_player
        
        return None
    
    def update_players(self) -> None:
        """Update CSV players with PTI data from JSON."""
        logger.info("🔄 Starting player matching and PTI update process...")
        
        for csv_player in self.csv_players:
            json_match = self.find_json_match(csv_player)
            
            if json_match:
                # Update PTI value
                updated_player = csv_player.copy()
                updated_player['PTI'] = json_match.get('PTI', '')
                self.updated_players.append(updated_player)
                self.matched_count += 1
                
                if csv_player.get('PTI', '').strip() != json_match.get('PTI', ''):
                    logger.info(f"✅ Updated PTI for {csv_player.get('First Name')} {csv_player.get('Last Name')}: '{csv_player.get('PTI', '')}' → '{json_match.get('PTI', '')}'")
            else:
                # No match found
                self.unmatched_csv.append(csv_player)
                logger.warning(f"⚠️ No JSON match found for: {csv_player.get('First Name')} {csv_player.get('Last Name')} ({csv_player.get('Club')}, {csv_player.get('Series')})")
        
        logger.info(f"📊 Matching complete: {self.matched_count} matched, {len(self.unmatched_csv)} unmatched from CSV")
    
    def find_csv_match(self, json_player: Dict) -> Optional[Dict]:
        """Find matching player in CSV data."""
        json_first = self.normalize_name(json_player.get('First Name', ''))
        json_last = self.normalize_name(json_player.get('Last Name', ''))
        json_club = self.normalize_club(json_player.get('Club', ''))
        json_series = self.normalize_series(json_player.get('Series', ''))
        
        for csv_player in self.csv_players:
            csv_first = self.normalize_name(csv_player.get('First Name', ''))
            csv_last = self.normalize_name(csv_player.get('Last Name', ''))
            csv_club = self.normalize_club(csv_player.get('Club', ''))
            csv_series = self.normalize_series(csv_player.get('Series', ''))
            
            # Exact match
            if (json_first == csv_first and json_last == csv_last and 
                json_club == csv_club and json_series == csv_series):
                return csv_player
        
        return None
    
    def find_new_players(self) -> None:
        """Find players in JSON that aren't in CSV."""
        logger.info("🔍 Looking for new players in JSON data...")
        
        for json_player in self.json_players:
            csv_match = self.find_csv_match(json_player)
            if not csv_match:
                self.unmatched_json.append(json_player)
        
        logger.info(f"📊 Found {len(self.unmatched_json)} new players in JSON not in CSV")
    
    def save_updated_csv(self, output_file: str = None) -> None:
        """Save the updated CSV file."""
        if output_file is None:
            # Create backup of original file
            backup_file = f"{self.csv_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.rename(self.csv_file, backup_file)
            logger.info(f"💾 Created backup: {backup_file}")
            output_file = self.csv_file
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                if self.updated_players:
                    fieldnames = self.updated_players[0].keys()
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(self.updated_players)
                    
                    logger.info(f"💾 Saved {len(self.updated_players)} updated players to {output_file}")
                else:
                    logger.warning("⚠️ No updated players to save")
                    
        except Exception as e:
            logger.error(f"❌ Error saving updated CSV: {e}")
    
    def generate_report(self) -> None:
        """Generate a summary report."""
        logger.info("📋 GENERATION SUMMARY REPORT")
        logger.info("=" * 50)
        logger.info(f"Total CSV players: {len(self.csv_players)}")
        logger.info(f"Total JSON players: {len(self.json_players)}")
        logger.info(f"Successfully matched: {self.matched_count}")
        logger.info(f"Unmatched from CSV: {len(self.unmatched_csv)}")
        logger.info(f"New players in JSON: {len(self.unmatched_json)}")
        
        if self.unmatched_csv:
            logger.info("\n⚠️ Unmatched CSV players (first 10):")
            for i, player in enumerate(self.unmatched_csv[:10]):
                logger.info(f"  {i+1}. {player.get('First Name')} {player.get('Last Name')} ({player.get('Club')}, {player.get('Series')})")
        
        if self.unmatched_json:
            logger.info("\n🆕 New players in JSON (first 10):")
            for i, player in enumerate(self.unmatched_json[:10]):
                logger.info(f"  {i+1}. {player.get('First Name')} {player.get('Last Name')} ({player.get('Club')}, {player.get('Series')}) - PTI: {player.get('PTI', 'N/A')}")
    
    def run(self) -> None:
        """Run the complete update process."""
        logger.info("🚀 Starting APTA PTI CSV Update Process")
        logger.info("=" * 50)
        
        # Load data
        self.csv_players = self.load_csv_data()
        self.json_players = self.load_json_data()
        
        if not self.csv_players or not self.json_players:
            logger.error("❌ Failed to load required data files")
            return
        
        # Update players
        self.update_players()
        
        # Find new players
        self.find_new_players()
        
        # Save updated CSV
        self.save_updated_csv()
        
        # Generate report
        self.generate_report()
        
        logger.info("✅ APTA PTI CSV Update Process Complete")

def main():
    """Main function."""
    updater = APTAPTIUpdater()
    updater.run()

if __name__ == "__main__":
    main()
