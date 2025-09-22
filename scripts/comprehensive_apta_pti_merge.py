#!/usr/bin/env python3
"""
Comprehensive script to merge APTA Players CSV with JSON data.
This script:
1. Preserves all original CSV players
2. Updates PTI values for existing players from JSON
3. Adds all new players from JSON data
4. Creates a comprehensive CSV with all players
"""

import os
import sys
import json
import csv
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

# Add project root to path
sys.path.append(os.getcwd())

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'comprehensive_pti_merge_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)

class ComprehensiveAPTAMerger:
    """Comprehensive merger for APTA Players CSV and JSON data."""
    
    def __init__(self, csv_file: str = "data/APTA Players - 2025 Season Starting PTI.csv", 
                 json_file: str = "data/leagues/APTA_CHICAGO/players.json"):
        """Initialize the merger."""
        self.csv_file = csv_file
        self.json_file = json_file
        self.csv_players = []
        self.json_players = []
        self.final_players = []
        self.updated_count = 0
        self.new_players_count = 0
        self.total_players = 0
        
        logger.info(f"🚀 Comprehensive APTA PTI Merger initialized")
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
    
    def create_player_key(self, player: Dict) -> str:
        """Create a unique key for player matching."""
        first = self.normalize_name(player.get('First Name', ''))
        last = self.normalize_name(player.get('Last Name', ''))
        club = self.normalize_club(player.get('Club', ''))
        series = self.normalize_series(player.get('Series', ''))
        return f"{first}|{last}|{club}|{series}"
    
    def find_json_match(self, csv_player: Dict[str, str]) -> Optional[Dict]:
        """Find matching player in JSON data."""
        csv_key = self.create_player_key(csv_player)
        
        for json_player in self.json_players:
            json_key = self.create_player_key(json_player)
            if csv_key == json_key:
                return json_player
        
        # Try fuzzy matching for close matches (same name and club, different series)
        csv_first = self.normalize_name(csv_player.get('First Name', ''))
        csv_last = self.normalize_name(csv_player.get('Last Name', ''))
        csv_club = self.normalize_club(csv_player.get('Club', ''))
        
        for json_player in self.json_players:
            json_first = self.normalize_name(json_player.get('First Name', ''))
            json_last = self.normalize_name(json_player.get('Last Name', ''))
            json_club = self.normalize_club(json_player.get('Club', ''))
            
            if (csv_first == json_first and csv_last == json_last and csv_club == json_club):
                logger.warning(f"⚠️ Series mismatch for {csv_first} {csv_last} ({csv_club}): CSV='{csv_player.get('Series', '')}' vs JSON='{json_player.get('Series', '')}'")
                return json_player
        
        return None
    
    def convert_json_to_csv_format(self, json_player: Dict) -> Dict[str, str]:
        """Convert JSON player data to CSV format."""
        return {
            'First Name': json_player.get('First Name', ''),
            'Last Name': json_player.get('Last Name', ''),
            'Club': json_player.get('Club', ''),
            'Series': json_player.get('Series', ''),
            'Team': json_player.get('Team', ''),
            'PTI': json_player.get('PTI', '')
        }
    
    def merge_data(self) -> None:
        """Merge CSV and JSON data comprehensively."""
        logger.info("🔄 Starting comprehensive data merge...")
        
        # Create a set to track which JSON players we've used
        used_json_keys = set()
        
        # Process all CSV players first (preserve all original data)
        for csv_player in self.csv_players:
            json_match = self.find_json_match(csv_player)
            
            if json_match:
                # Update PTI value from JSON
                updated_player = csv_player.copy()
                updated_player['PTI'] = json_match.get('PTI', csv_player.get('PTI', ''))
                self.final_players.append(updated_player)
                self.updated_count += 1
                
                # Mark this JSON player as used
                json_key = self.create_player_key(json_match)
                used_json_keys.add(json_key)
                
                if csv_player.get('PTI', '').strip() != json_match.get('PTI', ''):
                    logger.info(f"✅ Updated PTI for {csv_player.get('First Name')} {csv_player.get('Last Name')}: '{csv_player.get('PTI', '')}' → '{json_match.get('PTI', '')}'")
            else:
                # Keep original CSV player as-is
                self.final_players.append(csv_player)
        
        # Add all new players from JSON that weren't in CSV
        for json_player in self.json_players:
            json_key = self.create_player_key(json_player)
            if json_key not in used_json_keys:
                # This is a new player not in the CSV
                new_player = self.convert_json_to_csv_format(json_player)
                self.final_players.append(new_player)
                self.new_players_count += 1
        
        self.total_players = len(self.final_players)
        logger.info(f"📊 Merge complete: {self.total_players} total players ({len(self.csv_players)} original + {self.new_players_count} new)")
        logger.info(f"   Updated PTI values: {self.updated_count}")
        logger.info(f"   New players added: {self.new_players_count}")
    
    def save_comprehensive_csv(self, output_file: str = None) -> None:
        """Save the comprehensive CSV file."""
        if output_file is None:
            # Create backup of current file
            backup_file = f"{self.csv_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.rename(self.csv_file, backup_file)
            logger.info(f"💾 Created backup: {backup_file}")
            output_file = self.csv_file
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                if self.final_players:
                    fieldnames = self.final_players[0].keys()
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(self.final_players)
                    
                    logger.info(f"💾 Saved {len(self.final_players)} players to {output_file}")
                else:
                    logger.warning("⚠️ No players to save")
                    
        except Exception as e:
            logger.error(f"❌ Error saving comprehensive CSV: {e}")
    
    def generate_report(self) -> None:
        """Generate a comprehensive summary report."""
        logger.info("📋 COMPREHENSIVE MERGE SUMMARY REPORT")
        logger.info("=" * 60)
        logger.info(f"Original CSV players: {len(self.csv_players)}")
        logger.info(f"JSON players: {len(self.json_players)}")
        logger.info(f"Final comprehensive CSV players: {self.total_players}")
        logger.info(f"PTI values updated: {self.updated_count}")
        logger.info(f"New players added from JSON: {self.new_players_count}")
        logger.info(f"Original players preserved: {len(self.csv_players)}")
        
        # Show some examples of new players
        if self.new_players_count > 0:
            logger.info(f"\n🆕 Sample new players added (first 10):")
            new_players = [p for p in self.final_players if p not in self.csv_players][:10]
            for i, player in enumerate(new_players):
                logger.info(f"  {i+1}. {player.get('First Name')} {player.get('Last Name')} ({player.get('Club')}, {player.get('Series')}) - PTI: {player.get('PTI', 'N/A')}")
    
    def run(self) -> None:
        """Run the comprehensive merge process."""
        logger.info("🚀 Starting Comprehensive APTA PTI Merge Process")
        logger.info("=" * 60)
        
        # Load data
        self.csv_players = self.load_csv_data()
        self.json_players = self.load_json_data()
        
        if not self.csv_players or not self.json_players:
            logger.error("❌ Failed to load required data files")
            return
        
        # Merge data comprehensively
        self.merge_data()
        
        # Save comprehensive CSV
        self.save_comprehensive_csv()
        
        # Generate report
        self.generate_report()
        
        logger.info("✅ Comprehensive APTA PTI Merge Process Complete")

def main():
    """Main function."""
    merger = ComprehensiveAPTAMerger()
    merger.run()

if __name__ == "__main__":
    main()
