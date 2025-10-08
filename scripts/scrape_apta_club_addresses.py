#!/usr/bin/env python3

"""
Script to scrape club addresses from APTA Chicago website
This script will visit individual club pages to extract addresses
"""

import os
import random
import re
import sys
import time
import csv
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_utils import execute_query


class APTAClubAddressScraper:
    def __init__(self):
        self.base_url = "https://aptachicago.tenniscores.com"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        self.club_addresses = {}

    def get_all_clubs_from_database(self):
        """Get all clubs from the database that need addresses"""
        clubs = execute_query("""
            SELECT id, name 
            FROM clubs 
            WHERE club_address IS NULL OR club_address = ''
            ORDER BY name
        """)
        return clubs

    def search_club_on_website(self, club_name):
        """Search for a club on the APTA website"""
        try:
            # Try different search variations
            search_terms = [
                club_name,
                club_name.replace(" CC", "").replace(" Country Club", ""),
                club_name.replace(" RC", "").replace(" Racquet Club", ""),
                club_name.replace(" GC", "").replace(" Golf Club", ""),
                club_name.replace(" PC", "").replace(" Paddle Club", ""),
            ]
            
            for search_term in search_terms:
                if not search_term or len(search_term) < 3:
                    continue
                    
                print(f"  🔍 Searching for: {search_term}")
                
                # Search on the main page
                response = self.session.get(self.base_url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, "html.parser")
                
                # Look for club mentions in the page
                club_links = self.find_club_links(soup, search_term)
                
                if club_links:
                    print(f"    ✅ Found {len(club_links)} potential matches")
                    return club_links
                
                time.sleep(random.uniform(1, 2))
            
            return []
            
        except Exception as e:
            print(f"    ❌ Error searching for {club_name}: {str(e)}")
            return []

    def find_club_links(self, soup, search_term):
        """Find links that might be related to the club"""
        links = []
        
        # Look for text containing the club name
        text_matches = soup.find_all(text=re.compile(search_term, re.IGNORECASE))
        
        for match in text_matches:
            parent = match.parent
            if parent and parent.name == 'a' and parent.get('href'):
                links.append({
                    'text': match.strip(),
                    'href': parent.get('href'),
                    'parent_text': parent.get_text(strip=True)
                })
        
        return links

    def extract_address_from_page(self, url):
        """Extract address from a specific page"""
        try:
            print(f"    📄 Checking page: {url}")
            
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Look for address patterns
            address = self.find_address_in_soup(soup)
            
            if address:
                print(f"    ✅ Found address: {address}")
                return address
            else:
                print(f"    ⚠️  No address found on page")
                return None
                
        except Exception as e:
            print(f"    ❌ Error extracting address from {url}: {str(e)}")
            return None

    def find_address_in_soup(self, soup):
        """Find address using multiple strategies"""
        
        # Strategy 1: Look for Google Maps links
        maps_links = soup.find_all('a', href=re.compile(r'google\.com/maps|maps\.google\.com'))
        for link in maps_links:
            address = self.extract_address_from_maps_url(link.get('href'))
            if address:
                return address
        
        # Strategy 2: Look for address patterns in text
        address_patterns = [
            r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Way|Court|Ct|Place|Pl)\s*,?\s*[A-Za-z\s]+,?\s*[A-Z]{2}\s+\d{5}',
            r'\d+\s+[A-Za-z\s\.]+(?:St|Ave|Rd|Dr|Ln|Blvd|Way|Ct|Pl)\s*,?\s*[A-Za-z\s]+,?\s*(?:IL|Illinois)',
        ]
        
        page_text = soup.get_text()
        
        for pattern in address_patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            if matches:
                for match in matches:
                    if 15 <= len(match) <= 100:
                        return match.strip()
        
        return None

    def extract_address_from_maps_url(self, maps_url):
        """Extract address from Google Maps URL"""
        try:
            parsed = urlparse(maps_url)
            query_params = parse_qs(parsed.query)
            
            # Check 'q' parameter
            if "q" in query_params:
                address = query_params["q"][0]
                if self.is_valid_address(address):
                    return address
            
            # Check 'daddr' parameter
            if "daddr" in query_params:
                address = query_params["daddr"][0]
                if self.is_valid_address(address):
                    return address
            
            return None
            
        except Exception as e:
            print(f"    ❌ Error parsing maps URL: {str(e)}")
            return None

    def is_valid_address(self, address):
        """Check if the text looks like a valid address"""
        if not address or len(address) < 10:
            return False
        
        # Should contain at least a number and a word that looks like a street
        if not re.search(r'\d+\s+[A-Za-z]', address):
            return False
        
        # Should not be too long
        if len(address) > 150:
            return False
        
        return True

    def scrape_all_clubs(self):
        """Scrape addresses for all clubs that need them"""
        print("🏓 APTA CHICAGO CLUB ADDRESS SCRAPER")
        print("=" * 60)
        
        # Get clubs from database
        clubs = self.get_all_clubs_from_database()
        
        if not clubs:
            print("✅ All clubs already have addresses!")
            return
        
        print(f"📊 Found {len(clubs)} clubs without addresses")
        print()
        
        updated_count = 0
        not_found_count = 0
        
        for i, club in enumerate(clubs, 1):
            club_id = club['id']
            club_name = club['name']
            
            print(f"[{i}/{len(clubs)}] Processing: {club_name}")
            
            # Skip certain clubs that are not real clubs
            if club_name in ['BYE', 'Placeholder Club']:
                print(f"  ⚠️  Skipping {club_name} (not a real club)")
                not_found_count += 1
                continue
            
            # Search for the club
            club_links = self.search_club_on_website(club_name)
            
            if club_links:
                # Try to extract address from the first few links
                address = None
                for link in club_links[:3]:  # Try first 3 links
                    full_url = urljoin(self.base_url, link['href'])
                    address = self.extract_address_from_page(full_url)
                    if address:
                        break
                
                if address:
                    self.club_addresses[club_name] = address
                    updated_count += 1
                else:
                    not_found_count += 1
            else:
                not_found_count += 1
            
            print()
            
            # Add delay to be respectful
            if i < len(clubs):
                time.sleep(random.uniform(2, 4))
        
        print("=" * 60)
        print(f"📊 SCRAPING SUMMARY:")
        print(f"  ✅ Successfully found addresses: {updated_count}")
        print(f"  ⚠️  No address found: {not_found_count}")
        print(f"  📝 Total processed: {len(clubs)}")
        
        return self.club_addresses

    def save_to_csv(self, filename="data/apta_club_addresses.csv"):
        """Save scraped addresses to CSV file"""
        if not self.club_addresses:
            print("❌ No addresses to save")
            return
        
        try:
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['Club Name', 'Address']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for club_name, address in self.club_addresses.items():
                    writer.writerow({
                        'Club Name': club_name,
                        'Address': address
                    })
            
            print(f"💾 Saved {len(self.club_addresses)} addresses to {filename}")
            
        except Exception as e:
            print(f"❌ Error saving to CSV: {str(e)}")


def main():
    """Main function"""
    try:
        scraper = APTAClubAddressScraper()
        
        # Scrape addresses
        addresses = scraper.scrape_all_clubs()
        
        if addresses:
            # Save to CSV
            scraper.save_to_csv()
            
            print(f"\n✅ Scraping completed! Found {len(addresses)} addresses.")
            print("💡 You can now use the load_club_addresses_from_csv.py script to load these addresses into the database.")
        else:
            print("\n⚠️  No addresses were found.")
    
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
