#!/usr/bin/env python3
"""
APTA Chicago Directory Scraper
==============================

Scrapes the APTA Chicago directory from the provided HTML content.
Extracts all players with their contact information.

Usage:
    python scripts/scrape_apta_directory_proper.py [--output output.csv] [--input input.html]
"""

import argparse
import csv
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'apta_directory_scraper_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class APTADirectoryScraper:
    """Scraper for APTA Chicago directory from HTML content."""
    
    def __init__(self, input_file: str = "APTA Chicago.html", output_file: str = None):
        """Initialize the scraper."""
        self.input_file = input_file
        self.output_file = output_file or f"apta_directory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Data storage
        self.players = []
        
        logger.info(f"🚀 APTA Directory Scraper initialized")
        logger.info(f"   Input file: {self.input_file}")
        logger.info(f"   Output file: {self.output_file}")
    
    def load_html_file(self) -> str:
        """Load the HTML file content."""
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.info(f"📄 Loaded HTML file ({len(content)} characters)")
            return content
        except FileNotFoundError:
            logger.error(f"❌ File not found: {self.input_file}")
            return ""
        except Exception as e:
            logger.error(f"❌ Error loading file: {e}")
            return ""
    
    def extract_players_from_directory(self, html_content: str) -> List[Dict[str, str]]:
        """Extract all players from the directory table structure."""
        players = []
        
        # Pattern to match each player row in the directory
        # Looking for the structure: <div class="rower"> with player data
        row_pattern = r'<div class="rower">.*?<div class="clearfix"></div></div>'
        
        # Find all player rows
        rows = re.findall(row_pattern, html_content, re.DOTALL)
        logger.info(f"📊 Found {len(rows)} player rows in directory")
        
        for i, row in enumerate(rows):
            try:
                # Extract first name
                first_name_match = re.search(r'<div class="fnamer">([^<]+)</div>', row)
                first_name = first_name_match.group(1).strip() if first_name_match else ""
                
                # Extract last name and email from the link
                last_name_match = re.search(r'<div class="lnamer"><a[^>]*href="mailto:([^"]*)"[^>]*>([^<]+)</a>', row)
                if last_name_match:
                    email = last_name_match.group(1).strip()
                    last_name = last_name_match.group(2).strip()
                else:
                    # Try without email link
                    last_name_match = re.search(r'<div class="lnamer">([^<]+)</div>', row)
                    last_name = last_name_match.group(1).strip() if last_name_match else ""
                    email = ""
                
                # Extract phone number
                phone_match = re.search(r'<div class="phone1">([^<]+)</div>', row)
                phone = phone_match.group(1).strip() if phone_match else ""
                
                # Clean up phone number (remove extra spaces and line breaks)
                if phone:
                    phone = re.sub(r'\s+', ' ', phone).strip()
                    # Remove any non-phone content
                    phone = re.sub(r'[^\d\s\(\)\-\.]', '', phone).strip()
                
                # Skip if no name data
                if not first_name and not last_name:
                    continue
                
                # Generate player ID (simple format)
                player_id = f"nndz-{first_name.upper()}{last_name.upper()}" if first_name and last_name else f"nndz-{i+1:04d}"
                
                player = {
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'phone': phone,
                    'player_id': player_id
                }
                players.append(player)
                
            except Exception as e:
                logger.warning(f"⚠️ Error processing row {i+1}: {e}")
                continue
        
        # Remove duplicates based on name
        unique_players = []
        seen = set()
        for player in players:
            key = f"{player['first_name']} {player['last_name']}".lower().strip()
            if key and key not in seen:
                seen.add(key)
                unique_players.append(player)
        
        logger.info(f"✅ Extracted {len(unique_players)} unique players from directory")
        return unique_players
    
    def save_to_csv(self, players: List[Dict[str, str]]) -> None:
        """Save player data to CSV file."""
        if not players:
            logger.warning("⚠️ No player data to save")
            return
        
        try:
            with open(self.output_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['First Name', 'Last Name', 'Email', 'Phone', 'Player ID']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for player in players:
                    writer.writerow({
                        'First Name': player.get('first_name', ''),
                        'Last Name': player.get('last_name', ''),
                        'Email': player.get('email', ''),
                        'Phone': player.get('phone', ''),
                        'Player ID': player.get('player_id', '')
                    })
            
            logger.info(f"💾 Saved {len(players)} players to {self.output_file}")
            
        except Exception as e:
            logger.error(f"❌ Error saving to CSV: {e}")
    
    def run(self) -> None:
        """Run the complete scraping process."""
        logger.info("🚀 Starting APTA Directory Scraper")
        
        try:
            # Load HTML file
            html_content = self.load_html_file()
            if not html_content:
                logger.error("❌ Failed to load HTML file")
                return
            
            # Extract players from directory
            players = self.extract_players_from_directory(html_content)
            
            # Save to CSV
            if players:
                self.save_to_csv(players)
                
                # Print summary
                logger.info("📊 Player Summary:")
                logger.info(f"   Total players found: {len(players)}")
                logger.info(f"   Players with emails: {len([p for p in players if p.get('email')])}")
                logger.info(f"   Players with phones: {len([p for p in players if p.get('phone')])}")
                
                # Show sample players
                if players:
                    logger.info("📋 Sample players:")
                    for i, player in enumerate(players[:10]):
                        logger.info(f"   {i+1}. {player.get('first_name', '')} {player.get('last_name', '')} - {player.get('email', 'No email')} - {player.get('phone', 'No phone')}")
            else:
                logger.warning("⚠️ No player data was extracted")
                
        except Exception as e:
            logger.error(f"❌ Scraping failed: {e}")
            raise

def main():
    """Main entry point for the scraper."""
    parser = argparse.ArgumentParser(description='Scrape APTA Chicago directory from HTML file')
    parser.add_argument('--input', '-i', type=str, default='APTA Chicago.html', help='Input HTML file path')
    parser.add_argument('--output', '-o', type=str, help='Output CSV file path')
    
    args = parser.parse_args()
    
    try:
        scraper = APTADirectoryScraper(
            input_file=args.input,
            output_file=args.output
        )
        scraper.run()
        
    except KeyboardInterrupt:
        logger.info("⏹️ Scraping interrupted by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()


