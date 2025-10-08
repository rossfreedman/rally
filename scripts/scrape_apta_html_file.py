#!/usr/bin/env python3
"""
APTA Chicago HTML File Scraper
==============================

Scrapes the local APTA Chicago.html file to extract team information and player data.
This is designed to work with the saved HTML file instead of live scraping.

Usage:
    python scripts/scrape_apta_html_file.py [--output output.csv] [--input input.html]

Features:
- Extracts team listings from the HTML file
- Finds player names and contact information
- Exports to CSV with First Name, Last Name, Email, Phone columns
- Handles the specific structure of the APTA Chicago directory page
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
        logging.FileHandler(f'apta_html_scraper_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class APTAHTMLScraper:
    """Scraper for APTA Chicago HTML file."""
    
    def __init__(self, input_file: str = "APTA Chicago.html", output_file: str = None):
        """Initialize the scraper."""
        self.input_file = input_file
        self.output_file = output_file or f"apta_teams_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Data storage
        self.teams = []
        self.players = []
        
        logger.info(f"🚀 APTA HTML Scraper initialized")
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
    
    def extract_teams(self, html_content: str) -> List[Dict[str, str]]:
        """Extract team information from the HTML content."""
        teams = []
        
        # Pattern to match team links
        team_pattern = r'<a href="[^"]*team=([^"]*)"[^>]*>([^<]+)</a>'
        team_matches = re.findall(team_pattern, html_content)
        
        logger.info(f"🔍 Found {len(team_matches)} team links")
        
        for team_id, team_name in team_matches:
            # Clean up team name
            team_name = team_name.strip()
            
            # Extract series number from team name
            series_match = re.search(r' - (\d+)(?: SW)?$', team_name)
            series = series_match.group(1) if series_match else ""
            
            # Extract club name
            club_name = re.sub(r' - \d+(?: SW)?$', '', team_name)
            
            team = {
                'team_id': team_id,
                'club_name': club_name,
                'series': series,
                'full_name': team_name,
                'email': '',
                'phone': ''
            }
            
            teams.append(team)
        
        # Remove duplicates
        unique_teams = []
        seen = set()
        for team in teams:
            key = team['full_name']
            if key not in seen:
                seen.add(key)
                unique_teams.append(team)
        
        logger.info(f"✅ Extracted {len(unique_teams)} unique teams")
        return unique_teams
    
    def extract_players(self, html_content: str) -> List[Dict[str, str]]:
        """Extract player information from the HTML content."""
        players = []
        
        # Look for player names in various contexts
        # Pattern 1: Look for names in news articles and content
        name_pattern = r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b'
        potential_names = re.findall(name_pattern, html_content)
        
        # Pattern 2: Look for email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, html_content)
        
        # Pattern 3: Look for phone numbers
        phone_pattern = r'(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
        phones = re.findall(phone_pattern, html_content)
        
        logger.info(f"📊 Found {len(potential_names)} potential names, {len(emails)} emails, {len(phones)} phones")
        
        # Filter out common false positives for names
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
            'About Us', 'Also Check', 'Out Other', 'Platforms Pickle', 'Paddle Home', 'Login Profile'
        }
        
        # Process potential names
        for name in potential_names:
            if name not in excluded_names and len(name.split()) == 2:
                first_name, last_name = name.split()
                
                # Skip if it looks like a system name or common words
                if any(word in name.lower() for word in ['system', 'browser', 'analytics', 'google', 'mozilla', 'font', 'css', 'html', 'javascript', 'jquery', 'script', 'style', 'link', 'meta', 'div', 'span', 'class', 'id', 'href', 'src', 'alt', 'title', 'width', 'height', 'margin', 'padding', 'border', 'color', 'background', 'display', 'float', 'position', 'relative', 'absolute', 'fixed', 'static', 'block', 'inline', 'none', 'hidden', 'visible', 'overflow', 'scroll', 'auto', 'left', 'right', 'top', 'bottom', 'center', 'middle', 'justify', 'start', 'end', 'space', 'between', 'around', 'evenly', 'stretch', 'flex', 'grid', 'table', 'row', 'column', 'wrap', 'nowrap', 'reverse', 'direction', 'order', 'grow', 'shrink', 'basis', 'align', 'self', 'content', 'items', 'justify', 'text', 'font', 'size', 'weight', 'style', 'family', 'variant', 'stretch', 'line', 'height', 'letter', 'spacing', 'word', 'break', 'white', 'space', 'text', 'align', 'vertical', 'indent', 'decoration', 'transform', 'shadow', 'outline', 'border', 'radius', 'box', 'shadow', 'opacity', 'visibility', 'z', 'index', 'cursor', 'pointer', 'events', 'user', 'select', 'resize', 'clip', 'path', 'mask', 'filter', 'backdrop', 'blur', 'brightness', 'contrast', 'drop', 'grayscale', 'hue', 'rotate', 'invert', 'saturate', 'sepia', 'url', 'linear', 'gradient', 'radial', 'conic', 'repeating', 'image', 'position', 'size', 'repeat', 'attachment', 'clip', 'origin', 'composite', 'blend', 'mode', 'isolation', 'mix', 'background', 'color', 'image', 'position', 'size', 'repeat', 'attachment', 'clip', 'origin', 'composite', 'blend', 'mode', 'isolation', 'mix', 'background', 'color', 'image', 'position', 'size', 'repeat', 'attachment', 'clip', 'origin', 'composite', 'blend', 'mode', 'isolation', 'mix']):
                    continue
                
                # Skip if it's too short or looks like a common word
                if len(first_name) < 2 or len(last_name) < 2:
                    continue
                
                # Skip if it contains numbers or special characters
                if any(char.isdigit() or char in '.,!@#$%^&*()_+-=[]{}|;:"<>?/~`' for char in name):
                    continue
                
                player = {
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': '',
                    'phone': ''
                }
                players.append(player)
        
        # Try to match emails with names
        for email in emails:
            # Look for names near this email
            email_pos = html_content.find(email)
            if email_pos != -1:
                context_start = max(0, email_pos - 200)
                context_end = min(len(html_content), email_pos + 200)
                context = html_content[context_start:context_end]
                
                # Find names in this context
                context_names = re.findall(name_pattern, context)
                if context_names:
                    name = context_names[-1]
                    if name not in excluded_names and len(name.split()) == 2:
                        first_name, last_name = name.split()
                        
                        player = {
                            'first_name': first_name,
                            'last_name': last_name,
                            'email': email,
                            'phone': ''
                        }
                        players.append(player)
        
        # Try to match phones with names
        for phone_parts in phones:
            phone = f"({phone_parts[1]}) {phone_parts[2]}-{phone_parts[3]}" if not phone_parts[0] else f"{phone_parts[0]}{phone_parts[1]}{phone_parts[2]}{phone_parts[3]}"
            
            # Look for names near this phone
            phone_pos = html_content.find(phone)
            if phone_pos != -1:
                context_start = max(0, phone_pos - 200)
                context_end = min(len(html_content), phone_pos + 200)
                context = html_content[context_start:context_end]
                
                # Find names in this context
                context_names = re.findall(name_pattern, context)
                if context_names:
                    name = context_names[-1]
                    if name not in excluded_names and len(name.split()) == 2:
                        first_name, last_name = name.split()
                        
                        # Check if we already have this player
                        existing_player = None
                        for p in players:
                            if p['first_name'] == first_name and p['last_name'] == last_name:
                                existing_player = p
                                break
                        
                        if existing_player:
                            existing_player['phone'] = phone
                        else:
                            player = {
                                'first_name': first_name,
                                'last_name': last_name,
                                'email': '',
                                'phone': phone
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
    
    def save_teams_to_csv(self, teams: List[Dict[str, str]]) -> None:
        """Save team data to CSV file."""
        if not teams:
            logger.warning("⚠️ No team data to save")
            return
        
        try:
            with open(f"teams_{self.output_file}", 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['Team ID', 'Club Name', 'Series', 'Full Name', 'Email', 'Phone']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for team in teams:
                    writer.writerow({
                        'Team ID': team.get('team_id', ''),
                        'Club Name': team.get('club_name', ''),
                        'Series': team.get('series', ''),
                        'Full Name': team.get('full_name', ''),
                        'Email': team.get('email', ''),
                        'Phone': team.get('phone', '')
                    })
            
            logger.info(f"💾 Saved {len(teams)} teams to teams_{self.output_file}")
            
        except Exception as e:
            logger.error(f"❌ Error saving teams to CSV: {e}")
    
    def save_players_to_csv(self, players: List[Dict[str, str]]) -> None:
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
            logger.error(f"❌ Error saving players to CSV: {e}")
    
    def run(self) -> None:
        """Run the complete scraping process."""
        logger.info("🚀 Starting APTA HTML File Scraper")
        
        try:
            # Load HTML file
            html_content = self.load_html_file()
            if not html_content:
                logger.error("❌ Failed to load HTML file")
                return
            
            # Extract teams
            teams = self.extract_teams(html_content)
            
            # Extract players
            players = self.extract_players(html_content)
            
            # Save to CSV files
            if teams:
                self.save_teams_to_csv(teams)
                
                # Print team summary
                logger.info("📊 Team Summary:")
                logger.info(f"   Total teams found: {len(teams)}")
                
                # Show sample teams
                if teams:
                    logger.info("📋 Sample teams:")
                    for i, team in enumerate(teams[:5]):
                        logger.info(f"   {i+1}. {team['full_name']} (ID: {team['team_id']})")
            
            if players:
                self.save_players_to_csv(players)
                
                # Print player summary
                logger.info("📊 Player Summary:")
                logger.info(f"   Total players found: {len(players)}")
                logger.info(f"   Players with emails: {len([p for p in players if p.get('email')])}")
                logger.info(f"   Players with phones: {len([p for p in players if p.get('phone')])}")
                
                # Show sample players
                if players:
                    logger.info("📋 Sample players:")
                    for i, player in enumerate(players[:5]):
                        logger.info(f"   {i+1}. {player.get('first_name', '')} {player.get('last_name', '')} - {player.get('email', 'No email')} - {player.get('phone', 'No phone')}")
            
            if not teams and not players:
                logger.warning("⚠️ No data was extracted from the HTML file")
                
        except Exception as e:
            logger.error(f"❌ Scraping failed: {e}")
            raise

def main():
    """Main entry point for the scraper."""
    parser = argparse.ArgumentParser(description='Scrape APTA Chicago HTML file for team and player information')
    parser.add_argument('--input', '-i', type=str, default='APTA Chicago.html', help='Input HTML file path')
    parser.add_argument('--output', '-o', type=str, help='Output CSV file path for players')
    
    args = parser.parse_args()
    
    try:
        scraper = APTAHTMLScraper(
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
