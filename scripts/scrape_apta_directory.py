#!/usr/bin/env python3
"""
APTA Chicago Directory Scraper
==============================

Scrapes the APTA Chicago directory page to extract player information including
names, emails, and phone numbers. Uses stealth features and proxy rotation
to avoid detection.

Usage:
    python scripts/scrape_apta_directory.py [--output output.csv] [--fast]

Features:
- Stealth browser with anti-detection measures
- Proxy rotation and retry logic
- CAPTCHA/block detection and handling
- CSV export with First Name, Last Name, Email, Phone columns
- Comprehensive logging and error handling
"""

import argparse
import csv
import json
import logging
import os
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import stealth and proxy components
try:
    from data.etl.scrapers.helpers.stealth_browser import EnhancedStealthBrowser, StealthConfig
    from data.etl.scrapers.helpers.proxy_manager import fetch_with_retry, get_random_headers
    from data.etl.scrapers.helpers.user_agent_manager import get_user_agent_for_site
except ImportError as e:
    print(f"❌ Error importing stealth components: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)

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
    """Scraper for APTA Chicago directory page with stealth features."""
    
    def __init__(self, fast_mode: bool = False, output_file: str = None):
        """Initialize the scraper with stealth configuration."""
        self.fast_mode = fast_mode
        self.output_file = output_file or f"apta_directory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Initialize stealth configuration
        self.config = StealthConfig(
            fast_mode=fast_mode,
            verbose=True,
            environment="production",
            headless=True
        )
        
        # Initialize stealth browser
        self.browser = EnhancedStealthBrowser(self.config)
        
        # Target URL
        self.target_url = "https://aptachicago.tenniscores.com/?mod=nndz-TW4vN2xPMjkyc2RR"
        
        # Player data storage
        self.players = []
        
        logger.info(f"🚀 APTA Directory Scraper initialized")
        logger.info(f"   Target URL: {self.target_url}")
        logger.info(f"   Output file: {self.output_file}")
        logger.info(f"   Fast mode: {fast_mode}")
    
    def extract_player_data_from_page(self, html_content: str) -> List[Dict[str, str]]:
        """
        Extract player data from the HTML content.
        
        This function looks for player information in various formats:
        - Direct name listings
        - Contact information patterns
        - Email addresses
        - Phone numbers
        """
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html_content, 'html.parser')
        players = []
        
        # Look for various patterns that might contain player data
        # The page structure shows team listings, so we need to find individual players
        
        # Pattern 1: Look for email addresses (most reliable indicator of player data)
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, html_content)
        
        # Pattern 2: Look for phone numbers
        phone_pattern = r'(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
        phones = re.findall(phone_pattern, html_content)
        
        # Pattern 3: Look for name patterns (First Last format)
        name_pattern = r'\b[A-Z][a-z]+ [A-Z][a-z]+\b'
        potential_names = re.findall(name_pattern, html_content)
        
        # Pattern 4: Look for specific HTML elements that might contain player data
        # Check for tables, lists, or divs that might contain player information
        player_containers = soup.find_all(['table', 'ul', 'ol', 'div'], 
                                        class_=re.compile(r'player|member|roster|directory', re.I))
        
        logger.info(f"📊 Found {len(emails)} emails, {len(phones)} phones, {len(potential_names)} potential names")
        logger.info(f"📊 Found {len(player_containers)} potential player containers")
        
        # Try to match names with emails and phones
        for i, email in enumerate(emails):
            player = {
                'first_name': '',
                'last_name': '',
                'email': email,
                'phone': ''
            }
            
            # Try to find a name near this email
            email_pos = html_content.find(email)
            if email_pos != -1:
                # Look for names in a 200-character window around the email
                context_start = max(0, email_pos - 100)
                context_end = min(len(html_content), email_pos + 100)
                context = html_content[context_start:context_end]
                
                # Find names in this context
                context_names = re.findall(name_pattern, context)
                if context_names:
                    # Use the closest name to the email
                    name = context_names[-1]  # Usually the last name before email
                    name_parts = name.split()
                    if len(name_parts) >= 2:
                        player['first_name'] = name_parts[0]
                        player['last_name'] = ' '.join(name_parts[1:])
            
            # Try to find a phone near this email
            if email_pos != -1:
                context_start = max(0, email_pos - 200)
                context_end = min(len(html_content), email_pos + 200)
                context = html_content[context_start:context_end]
                
                context_phones = re.findall(phone_pattern, context)
                if context_phones:
                    # Format the phone number
                    phone_parts = context_phones[0]
                    if phone_parts[0]:  # Has country code
                        player['phone'] = f"{phone_parts[0]}{phone_parts[1]}{phone_parts[2]}{phone_parts[3]}"
                    else:
                        player['phone'] = f"({phone_parts[1]}) {phone_parts[2]}-{phone_parts[3]}"
            
            players.append(player)
        
        # If we didn't find many emails, try to extract names from the team listings
        if len(players) < 10:  # Threshold for trying alternative extraction
            logger.info("🔍 Trying alternative extraction from team listings...")
            
            # Look for individual player names in team listings
            # The page shows teams like "Glen Ellyn - 1", "Hinsdale PC - 1", etc.
            # We need to find individual players within these teams
            
            # Look for links or clickable elements that might lead to player pages
            links = soup.find_all('a', href=True)
            player_links = []
            
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Look for links that might be player pages
                if any(keyword in href.lower() for keyword in ['player', 'member', 'profile', 'individual']):
                    player_links.append((href, text))
                elif re.match(name_pattern, text) and len(text.split()) >= 2:
                    # This looks like a player name
                    player_links.append((href, text))
            
            logger.info(f"🔗 Found {len(player_links)} potential player links")
            
            # For each player link, try to extract additional info
            for href, text in player_links[:50]:  # Limit to first 50 to avoid too many requests
                if re.match(name_pattern, text):
                    name_parts = text.split()
                    if len(name_parts) >= 2:
                        player = {
                            'first_name': name_parts[0],
                            'last_name': ' '.join(name_parts[1:]),
                            'email': '',
                            'phone': ''
                        }
                        players.append(player)
        
        # Remove duplicates based on email or name combination
        unique_players = []
        seen = set()
        
        for player in players:
            # Create a unique key
            if player['email']:
                key = player['email']
            else:
                key = f"{player['first_name']} {player['last_name']}".lower()
            
            if key and key not in seen:
                seen.add(key)
                unique_players.append(player)
        
        logger.info(f"✅ Extracted {len(unique_players)} unique players")
        return unique_players
    
    def scrape_directory(self) -> List[Dict[str, str]]:
        """Scrape the APTA directory page for player information."""
        logger.info(f"🌐 Starting directory scrape of {self.target_url}")
        
        try:
            # Use the stealth browser to get the page
            page_source = self.browser.get_html(self.target_url)
            
            if not page_source:
                logger.error("❌ Failed to get page content")
                return []
            
            logger.info(f"📄 Retrieved page content ({len(page_source)} characters)")
            
            # Extract player data
            players = self.extract_player_data_from_page(page_source)
            
            if not players:
                logger.warning("⚠️ No player data found on the page")
                logger.info("🔍 Page content preview:")
                logger.info(page_source[:1000] + "..." if len(page_source) > 1000 else page_source)
            else:
                logger.info(f"✅ Successfully extracted {len(players)} players")
            
            return players
                
        except Exception as e:
            logger.error(f"❌ Error during scraping: {e}")
            return []
    
    def save_to_csv(self, players: List[Dict[str, str]]) -> None:
        """Save player data to CSV file."""
        if not players:
            logger.warning("⚠️ No player data to save")
            return
        
        try:
            with open(self.output_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['First Name', 'Last Name', 'Email', 'Phone']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for player in players:
                    writer.writerow({
                        'First Name': player.get('first_name', ''),
                        'Last Name': player.get('last_name', ''),
                        'Email': player.get('email', ''),
                        'Phone': player.get('phone', '')
                    })
            
            logger.info(f"💾 Saved {len(players)} players to {self.output_file}")
            
        except Exception as e:
            logger.error(f"❌ Error saving to CSV: {e}")
    
    def run(self) -> None:
        """Run the complete scraping process."""
        logger.info("🚀 Starting APTA Directory Scraper")
        
        try:
            # Scrape the directory
            players = self.scrape_directory()
            
            if players:
                # Save to CSV
                self.save_to_csv(players)
                
                # Print summary
                logger.info("📊 Scraping Summary:")
                logger.info(f"   Total players found: {len(players)}")
                logger.info(f"   Players with emails: {len([p for p in players if p.get('email')])}")
                logger.info(f"   Players with phones: {len([p for p in players if p.get('phone')])}")
                logger.info(f"   Output file: {self.output_file}")
                
                # Show sample data
                if players:
                    logger.info("📋 Sample data:")
                    for i, player in enumerate(players[:3]):
                        logger.info(f"   {i+1}. {player.get('first_name', '')} {player.get('last_name', '')} - {player.get('email', 'No email')} - {player.get('phone', 'No phone')}")
            else:
                logger.warning("⚠️ No player data was extracted")
                
        except Exception as e:
            logger.error(f"❌ Scraping failed: {e}")
            raise
        finally:
            # Clean up
            try:
                self.browser.cleanup()
            except:
                pass

def main():
    """Main entry point for the scraper."""
    parser = argparse.ArgumentParser(description='Scrape APTA Chicago directory for player information')
    parser.add_argument('--output', '-o', type=str, help='Output CSV file path')
    parser.add_argument('--fast', action='store_true', help='Use fast mode with reduced delays')
    
    args = parser.parse_args()
    
    try:
        scraper = APTADirectoryScraper(
            fast_mode=args.fast,
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
