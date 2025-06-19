#!/usr/bin/env python3

"""
Script to automatically populate club addresses by searching Google
"""

import os
import sys
import time
import re
import requests
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
import random

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_update, execute_query

class GoogleAddressSearcher:
    def __init__(self):
        self.session = requests.Session()
        # Use a realistic user agent
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def search_club_address(self, club_name):
        """Search Google for a club's address"""
        try:
            # Create search query
            search_query = f"{club_name} Club Address"
            encoded_query = quote_plus(search_query)
            
            # Google search URL
            url = f"https://www.google.com/search?q={encoded_query}"
            
            print(f"  Searching: {search_query}")
            
            # Add random delay to avoid being blocked
            time.sleep(random.uniform(1, 3))
            
            # Make request
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try multiple strategies to find address
            address = self._extract_address_from_soup(soup, club_name)
            
            if address:
                print(f"  ✓ Found address: {address}")
                return address
            else:
                print(f"  ✗ No address found")
                return None
                
        except Exception as e:
            print(f"  ❌ Error searching for {club_name}: {str(e)}")
            return None
    
    def _extract_address_from_soup(self, soup, club_name):
        """Extract address from Google search results using multiple strategies"""
        
        # Strategy 1: Look for Google My Business info box
        address = self._find_gmb_address(soup)
        if address:
            return address
            
        # Strategy 2: Look for structured data/rich snippets
        address = self._find_structured_address(soup)
        if address:
            return address
            
        # Strategy 3: Look for address patterns in search results
        address = self._find_pattern_address(soup)
        if address:
            return address
            
        return None
    
    def _find_gmb_address(self, soup):
        """Find address in Google My Business info box"""
        try:
            # Look for address in knowledge panel
            knowledge_panel = soup.find('div', {'class': re.compile(r'knowledge|panel|kp-')})
            if knowledge_panel:
                # Look for address text
                address_elements = knowledge_panel.find_all(text=re.compile(r'\d+.*(?:St|Ave|Rd|Dr|Ln|Blvd|Way|Ct|Pl).*\d{5}'))
                if address_elements:
                    return address_elements[0].strip()
                    
            # Alternative selector for address
            address_spans = soup.find_all('span', string=re.compile(r'\d+.*(?:St|Ave|Rd|Dr|Ln|Blvd|Way|Ct|Pl).*\d{5}'))
            if address_spans:
                return address_spans[0].get_text().strip()
                
        except Exception:
            pass
        return None
    
    def _find_structured_address(self, soup):
        """Find address in structured data"""
        try:
            # Look for JSON-LD structured data
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    import json
                    data = json.loads(script.string)
                    if isinstance(data, list):
                        data = data[0]
                    
                    # Look for address in different formats
                    if 'address' in data:
                        addr = data['address']
                        if isinstance(addr, str):
                            return addr
                        elif isinstance(addr, dict):
                            # Structured address
                            street = addr.get('streetAddress', '')
                            city = addr.get('addressLocality', '')
                            state = addr.get('addressRegion', '')
                            zip_code = addr.get('postalCode', '')
                            
                            if street and city:
                                full_address = f"{street}, {city}"
                                if state:
                                    full_address += f", {state}"
                                if zip_code:
                                    full_address += f" {zip_code}"
                                return full_address
                except:
                    continue
        except Exception:
            pass
        return None
    
    def _find_pattern_address(self, soup):
        """Find address using regex patterns in search results"""
        try:
            # Get all text from the page
            text = soup.get_text()
            
            # Common address patterns
            patterns = [
                r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Way|Court|Ct|Place|Pl)\s*,?\s*[A-Za-z\s]+,?\s*[A-Z]{2}\s+\d{5}',
                r'\d+\s+[A-Za-z\s\.]+(?:St|Ave|Rd|Dr|Ln|Blvd|Way|Ct|Pl)\s*,?\s*[A-Za-z\s]+,?\s*[A-Z]{2}\s+\d{5}'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    # Return the first match that looks reasonable
                    for match in matches:
                        if len(match) > 20 and len(match) < 100:  # Reasonable length
                            return match.strip()
        except Exception:
            pass
        return None

def populate_missing_club_addresses():
    """Populate club addresses for clubs that don't have addresses yet"""
    
    print("🔍 Populating missing club addresses from Google search...")
    print("=" * 60)
    
    # Get clubs without addresses
    clubs_without_addresses = execute_query("""
        SELECT id, name 
        FROM clubs 
        WHERE club_address IS NULL OR club_address = ''
        ORDER BY name
    """)
    
    if not clubs_without_addresses:
        print("✅ All clubs already have addresses!")
        return
    
    print(f"Found {len(clubs_without_addresses)} clubs without addresses")
    print()
    
    searcher = GoogleAddressSearcher()
    
    updated_count = 0
    failed_count = 0
    
    for i, club in enumerate(clubs_without_addresses, 1):
        club_id = club['id']
        club_name = club['name']
        
        print(f"[{i}/{len(clubs_without_addresses)}] Processing: {club_name}")
        
        # Search for address
        address = searcher.search_club_address(club_name)
        
        if address:
            # Update database
            try:
                success = execute_update(
                    "UPDATE clubs SET club_address = %s WHERE id = %s",
                    (address, club_id)
                )
                
                if success:
                    print(f"  ✅ Updated database with address: {address}")
                    updated_count += 1
                else:
                    print(f"  ❌ Failed to update database")
                    failed_count += 1
                    
            except Exception as e:
                print(f"  ❌ Database error: {str(e)}")
                failed_count += 1
        else:
            print(f"  ⚠️ No address found for {club_name}")
            failed_count += 1
        
        print()
        
        # Add delay between requests to be respectful
        if i < len(clubs_without_addresses):
            time.sleep(random.uniform(2, 5))
    
    print("=" * 60)
    print(f"📊 SUMMARY:")
    print(f"  ✅ Successfully updated: {updated_count}")
    print(f"  ❌ Failed/Not found: {failed_count}")
    print(f"  📝 Total processed: {len(clubs_without_addresses)}")

def verify_populated_addresses():
    """Verify the addresses that were populated"""
    
    print("\n🔍 Verifying populated addresses...")
    print("=" * 60)
    
    clubs_with_addresses = execute_query("""
        SELECT name, club_address 
        FROM clubs 
        WHERE club_address IS NOT NULL AND club_address != ''
        ORDER BY name
    """)
    
    clubs_without_addresses = execute_query("""
        SELECT name 
        FROM clubs 
        WHERE club_address IS NULL OR club_address = ''
        ORDER BY name
    """)
    
    print(f"✅ Clubs WITH addresses: {len(clubs_with_addresses)}")
    for club in clubs_with_addresses[:10]:  # Show first 10
        print(f"  • {club['name']}: {club['club_address']}")
    if len(clubs_with_addresses) > 10:
        print(f"  ... and {len(clubs_with_addresses) - 10} more")
    
    print(f"\n❌ Clubs WITHOUT addresses: {len(clubs_without_addresses)}")
    for club in clubs_without_addresses:
        print(f"  • {club['name']}")

if __name__ == '__main__':
    try:
        # Check if required packages are available
        try:
            import requests
            import bs4
        except ImportError as e:
            print("❌ Required packages not installed.")
            print("Please install them with: pip install requests beautifulsoup4")
            sys.exit(1)
        
        print("🏓 Rally Club Address Populator")
        print("This script will search Google for missing club addresses")
        print("⚠️  Note: This makes requests to Google and should be used responsibly")
        print()
        
        # Ask for confirmation
        response = input("Continue? (y/N): ").strip().lower()
        if response != 'y':
            print("Cancelled.")
            sys.exit(0)
        
        # Run the population
        populate_missing_club_addresses()
        
        # Verify results
        verify_populated_addresses()
        
        print("\n✅ Club address population completed!")
        
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1) 