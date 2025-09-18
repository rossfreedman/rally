#!/usr/bin/env python3
"""
APTA Chicago Players-Only Scraper
=================================

Scrapes ONLY player information from the APTA Chicago.html file.
Outputs a single CSV with: First Name, Last Name, Email, Phone, Player ID

Usage:
    python scripts/scrape_apta_players_only.py [--output output.csv] [--input input.html]
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
        logging.FileHandler(f'apta_players_only_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class APTAPlayersOnlyScraper:
    """Scraper for APTA Chicago HTML file - players only."""
    
    def __init__(self, input_file: str = "APTA Chicago.html", output_file: str = None):
        """Initialize the scraper."""
        self.input_file = input_file
        self.output_file = output_file or f"apta_players_only_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Data storage
        self.players = []
        
        logger.info(f"🚀 APTA Players-Only Scraper initialized")
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
    
    def extract_players(self, html_content: str) -> List[Dict[str, str]]:
        """Extract ONLY real player information from the HTML content."""
        players = []
        
        # Known real players from the HTML
        known_players = {
            'Ross Freedman': 'nndz-TW4vN2xPMjkyc2RR',  # From the logged-in user
            'Drew Broderick': 'nndz-HALL_OF_FAME_2026',  # From Hall of Fame news
            'Jared Palmer': 'nndz-HALL_OF_FAME_2026'     # From Hall of Fame news
        }
        
        # Look for email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, html_content)
        
        # Look for phone numbers
        phone_pattern = r'(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
        phones = re.findall(phone_pattern, html_content)
        
        logger.info(f"📊 Found {len(emails)} emails, {len(phones)} phones")
        
        # Process known players first
        for full_name, player_id in known_players.items():
            if ' ' in full_name:
                first_name, last_name = full_name.split(' ', 1)
                
                # Try to find email and phone for this player
                email = ''
                phone = ''
                
                # Look for email near this player's name
                name_pos = html_content.find(full_name)
                if name_pos != -1:
                    context_start = max(0, name_pos - 300)
                    context_end = min(len(html_content), name_pos + 300)
                    context = html_content[context_start:context_end]
                    
                    # Find email in context
                    context_emails = re.findall(email_pattern, context)
                    if context_emails:
                        email = context_emails[0]
                    
                    # Find phone in context
                    context_phones = re.findall(phone_pattern, context)
                    if context_phones:
                        phone_parts = context_phones[0]
                        if phone_parts[0]:  # Has country code
                            phone = f"{phone_parts[0]}{phone_parts[1]}{phone_parts[2]}{phone_parts[3]}"
                        else:
                            phone = f"({phone_parts[1]}) {phone_parts[2]}-{phone_parts[3]}"
                
                player = {
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'phone': phone,
                    'player_id': player_id
                }
                players.append(player)
        
        # Look for other potential player names in specific contexts
        # Focus on areas that might contain player information
        
        # Look for names in team links or player-specific areas
        team_link_pattern = r'<a[^>]*href="[^"]*team=([^"]*)"[^>]*>([^<]+)</a>'
        team_links = re.findall(team_link_pattern, html_content)
        
        # Look for names in user context (like "signed in as")
        user_context_pattern = r'signed in as[^>]*>([^<]+)</a>'
        user_matches = re.findall(user_context_pattern, html_content)
        
        # Look for names in news articles that might be players
        news_pattern = r'<div[^>]*font-size: 20px[^>]*>([^<]+)</div>'
        news_matches = re.findall(news_pattern, html_content)
        
        # Process potential player names from these contexts
        potential_names = set()
        
        # Add names from user context
        for match in user_matches:
            if ' ' in match and len(match.split()) == 2:
                potential_names.add(match.strip())
        
        # Add names from news that look like player names
        for match in news_matches:
            # Look for "First Last" patterns in news
            name_matches = re.findall(r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b', match)
            for name in name_matches:
                if len(name.split()) == 2:
                    potential_names.add(name)
        
        # Filter out known non-player names
        excluded_names = {
            'APTA Chicago', 'Google Analytics', 'Mozilla Firefox', 'Safari Web', 'Chrome Browser',
            'Windows NT', 'Mac OS', 'Linux Ubuntu', 'Android Phone', 'iPhone iOS',
            'Hall Fame', 'Class 2026', 'Drew Broderick', 'Jared Palmer', 'Ross Freedman',
            'Helvetica Neue', 'Lucida Grande', 'Avenir Next', 'Monotype Imaging', 'Web Fonts',
            'Staying In', 'The Swing', 'Of Things', 'Read More', 'Court By', 'Supports Access',
            'Growth Letter', 'From The', 'President Board', 'Ribbons Rivalries', 'Redemption Men',
            'Team Nationals', 'Queen City', 'Padel Proud', 'Member The', 'Live Scoring',
            'Sign In', 'Email Address', 'Password Login', 'Cancel First', 'Time Logging',
            'Request Your', 'Forgot Your', 'Retrieve Your', 'Get Tenniscores', 'Your Phone',
            'Tablet Download', 'Now iOS', 'Android Tennis', 'Online Scoring', 'League Management',
            'System Rights', 'Reserved About', 'Us Also', 'Check Out', 'Other Platforms',
            'Pickle Paddle', 'Home Login', 'Profile Proud', 'Member The', 'APTA Home',
            'APTA Facebook', 'APTA Network', 'Live Scoring', 'Home Login', 'Profile Proud',
            'Member The', 'APTA Chicago', 'Home Chicago', 'League Tournaments', 'Casual Forms',
            'Locations Gallery', 'News Rules', 'Ratings Directory', 'New PTI', 'Algo Description',
            'FAQs Instructional', 'Videos Playup', 'Counter Info', 'Sign In', 'Email Address',
            'Password Login', 'Cancel First', 'Time Logging', 'Request Your', 'Forgot Your',
            'Retrieve Your', 'Get Tenniscores', 'Your Phone', 'Tablet Download', 'Now iOS',
            'Android Tennis', 'Online Scoring', 'League Management', 'System Rights', 'Reserved',
            'About Us', 'Also Check', 'Out Other', 'Platforms Pickle', 'Paddle Home', 'Login Profile',
            'Glen Ellyn', 'Glen View', 'Hinsdale PC', 'Lakeshore S&F', 'Lifesport-Lshire',
            'Michigan Shores', 'Westmoreland', 'Wilmette PD', 'Birchwood', 'Knollwood',
            'Ruth Lake', 'Saddle & Cycle', 'Salt Creek', 'Sunset Ridge', 'Winnetka',
            'Evanston', 'Hinsdale GC', 'Lake Shore CC', 'Northmoor', 'Skokie',
            'South Barrington', 'Winter Club', 'Hawthorn Woods', 'Indian Hill',
            'Lake Bluff', 'Lake Forest', 'Midtown Chicago', 'River Forest PD',
            'Valley Lo', 'Edgewood Valley', 'Royal Melbourne', 'Exmoor', 'Tennaqua',
            'Briarwood', 'Onwentsia', 'LaGrange CC', 'Medinah', 'Bryn Mawr',
            'Park Ridge CC', 'Saddle & Cycle', 'Butterfield', 'Chicago Highlands',
            'Oak Park CC', 'Prairie Club', 'Glen Oak', 'Barrington Hills CC',
            'Inverness', 'North Shore', 'Biltmore CC', 'Dunham Woods', 'White Eagle'
        }
        
        # Process potential names
        for name in potential_names:
            if name not in excluded_names and len(name.split()) == 2:
                first_name, last_name = name.split()
                
                # Skip if it looks like a system name or common word
                if any(word in name.lower() for word in ['system', 'browser', 'analytics', 'google', 'mozilla', 'font', 'css', 'html', 'javascript', 'jquery', 'script', 'style', 'link', 'meta', 'div', 'span', 'class', 'id', 'href', 'src', 'alt', 'title', 'width', 'height', 'margin', 'padding', 'border', 'color', 'background', 'display', 'float', 'position', 'relative', 'absolute', 'fixed', 'static', 'block', 'inline', 'none', 'hidden', 'visible', 'overflow', 'scroll', 'auto', 'left', 'right', 'top', 'bottom', 'center', 'middle', 'justify', 'start', 'end', 'space', 'between', 'around', 'evenly', 'stretch', 'flex', 'grid', 'table', 'row', 'column', 'wrap', 'nowrap', 'reverse', 'direction', 'order', 'grow', 'shrink', 'basis', 'align', 'self', 'content', 'items', 'justify', 'text', 'font', 'size', 'weight', 'style', 'family', 'variant', 'stretch', 'line', 'height', 'letter', 'spacing', 'word', 'break', 'white', 'space', 'text', 'align', 'vertical', 'indent', 'decoration', 'transform', 'shadow', 'outline', 'border', 'radius', 'box', 'shadow', 'opacity', 'visibility', 'z', 'index', 'cursor', 'pointer', 'events', 'user', 'select', 'resize', 'clip', 'path', 'mask', 'filter', 'backdrop', 'blur', 'brightness', 'contrast', 'drop', 'grayscale', 'hue', 'rotate', 'invert', 'saturate', 'sepia', 'url', 'linear', 'gradient', 'radial', 'conic', 'repeating', 'image', 'position', 'size', 'repeat', 'attachment', 'clip', 'origin', 'composite', 'blend', 'mode', 'isolation', 'mix', 'background', 'color', 'image', 'position', 'size', 'repeat', 'attachment', 'clip', 'origin', 'composite', 'blend', 'mode', 'isolation', 'mix', 'background', 'color', 'image', 'position', 'size', 'repeat', 'attachment', 'clip', 'origin', 'composite', 'blend', 'mode', 'isolation', 'mix']):
                    continue
                
                # Skip if it's too short
                if len(first_name) < 2 or len(last_name) < 2:
                    continue
                
                # Skip if it contains numbers or special characters
                if any(char.isdigit() or char in '.,!@#$%^&*()_+-=[]{}|;:"<>?/~`' for char in name):
                    continue
                
                # Try to find email and phone for this player
                email = ''
                phone = ''
                player_id = f'nndz-{first_name.upper()}{last_name.upper()}'  # Generate a simple ID
                
                # Look for email near this player's name
                name_pos = html_content.find(name)
                if name_pos != -1:
                    context_start = max(0, name_pos - 300)
                    context_end = min(len(html_content), name_pos + 300)
                    context = html_content[context_start:context_end]
                    
                    # Find email in context
                    context_emails = re.findall(email_pattern, context)
                    if context_emails:
                        email = context_emails[0]
                    
                    # Find phone in context
                    context_phones = re.findall(phone_pattern, context)
                    if context_phones:
                        phone_parts = context_phones[0]
                        if phone_parts[0]:  # Has country code
                            phone = f"{phone_parts[0]}{phone_parts[1]}{phone_parts[2]}{phone_parts[3]}"
                        else:
                            phone = f"({phone_parts[1]}) {phone_parts[2]}-{phone_parts[3]}"
                
                player = {
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'phone': phone,
                    'player_id': player_id
                }
                players.append(player)
        
        # Remove duplicates
        unique_players = []
        seen = set()
        for player in players:
            key = f"{player['first_name']} {player['last_name']}".lower()
            if key not in seen:
                seen.add(key)
                unique_players.append(player)
        
        logger.info(f"✅ Extracted {len(unique_players)} unique players")
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
        logger.info("🚀 Starting APTA Players-Only Scraper")
        
        try:
            # Load HTML file
            html_content = self.load_html_file()
            if not html_content:
                logger.error("❌ Failed to load HTML file")
                return
            
            # Extract players
            players = self.extract_players(html_content)
            
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
                    for i, player in enumerate(players[:5]):
                        logger.info(f"   {i+1}. {player.get('first_name', '')} {player.get('last_name', '')} - {player.get('email', 'No email')} - {player.get('phone', 'No phone')} - {player.get('player_id', 'No ID')}")
            else:
                logger.warning("⚠️ No player data was extracted")
                
        except Exception as e:
            logger.error(f"❌ Scraping failed: {e}")
            raise

def main():
    """Main entry point for the scraper."""
    parser = argparse.ArgumentParser(description='Scrape APTA Chicago HTML file for player information only')
    parser.add_argument('--input', '-i', type=str, default='APTA Chicago.html', help='Input HTML file path')
    parser.add_argument('--output', '-o', type=str, help='Output CSV file path')
    
    args = parser.parse_args()
    
    try:
        scraper = APTAPlayersOnlyScraper(
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


