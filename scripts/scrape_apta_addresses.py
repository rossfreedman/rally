#!/usr/bin/env python3

"""
Script to scrape club addresses from APTA Chicago website
Uses the official league site to get accurate club addresses
"""

import os
import random
import re
import sys
import time
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_utils import execute_query, execute_update


class APTAAddressScraper:
    def __init__(self):
        self.base_url = "https://aptachicago.tenniscores.com"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )

    def get_club_teams_from_homepage(self):
        """Scrape the homepage to get all club team links"""

        print("🔍 Scraping APTA Chicago homepage for club teams...")

        try:
            response = self.session.get(self.base_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Look for team links in the content
            team_links = []

            # Find links that contain team information
            # The page shows teams like "Glen Ellyn - 1", "Winnetka - 1", etc.
            links = soup.find_all("a", href=True)

            for link in links:
                href = link.get("href", "")
                text = link.get_text(strip=True)

                # Look for team links that have club names
                if "team=" in href and text:
                    # Extract club name from text (remove series numbers)
                    club_name = re.sub(r"\s*-\s*\d+.*$", "", text).strip()
                    if club_name and len(club_name) > 2:
                        full_url = urljoin(self.base_url, href)
                        team_links.append(
                            {"club_name": club_name, "team_text": text, "url": full_url}
                        )

            # Remove duplicates based on club name
            unique_clubs = {}
            for team in team_links:
                club = team["club_name"]
                if club not in unique_clubs:
                    unique_clubs[club] = team

            print(f"✅ Found {len(unique_clubs)} unique clubs with team pages")
            return list(unique_clubs.values())

        except Exception as e:
            print(f"❌ Error scraping homepage: {str(e)}")
            return []

    def extract_address_from_team_page(self, team_info):
        """Extract address from a team page"""

        club_name = team_info["club_name"]
        url = team_info["url"]

        print(f"🔍 Checking {club_name} team page...")

        try:
            response = self.session.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Look for "Get Directions" links
            directions_links = soup.find_all(
                "a", href=True, string=re.compile(r"get\s+directions", re.I)
            )

            for link in directions_links:
                href = link.get("href", "")

                # Check if it's a Google Maps link
                if "google.com/maps" in href or "maps.google.com" in href:
                    # Extract address from Google Maps URL
                    address = self.extract_address_from_maps_url(href)
                    if address:
                        print(f"  ✅ Found address via Get Directions: {address}")
                        return address

            # Look for any text that looks like an address
            address_patterns = [
                # Street address pattern
                r"\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Way|Court|Ct|Place|Pl)\s*,?\s*[A-Za-z\s]+,?\s*[A-Z]{2}\s+\d{5}",
                # Address with IL/Chicago pattern
                r"\d+\s+[A-Za-z\s\.]+(?:St|Ave|Rd|Dr|Ln|Blvd|Way|Ct|Pl)\s*,?\s*[A-Za-z\s]+,?\s*(?:IL|Chicago)",
            ]

            page_text = soup.get_text()

            for pattern in address_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    # Return the first reasonable match
                    for match in matches:
                        if 15 <= len(match) <= 100:
                            clean_address = match.strip()
                            print(f"  ✅ Found address in page text: {clean_address}")
                            return clean_address

            print(f"  ⚠️ No address found for {club_name}")
            return None

        except Exception as e:
            print(f"  ❌ Error scraping {club_name}: {str(e)}")
            return None

    def extract_address_from_maps_url(self, maps_url):
        """Extract address from Google Maps URL"""

        try:
            # Parse the URL
            parsed = urlparse(maps_url)

            # Look for address in query parameters
            query_params = parse_qs(parsed.query)

            # Check 'q' parameter (query)
            if "q" in query_params:
                address = query_params["q"][0]
                if self.is_valid_address(address):
                    return address

            # Check 'daddr' parameter (destination address)
            if "daddr" in query_params:
                address = query_params["daddr"][0]
                if self.is_valid_address(address):
                    return address

            return None

        except Exception as e:
            print(f"    ❌ Error parsing maps URL: {str(e)}")
            return None

    def is_valid_address(self, address):
        """Check if the extracted text looks like a valid address"""

        if not address or len(address) < 10:
            return False

        # Should contain at least a number and a word that looks like a street
        if not re.search(r"\d+\s+[A-Za-z]", address):
            return False

        # Should not be too long (likely extracted too much text)
        if len(address) > 150:
            return False

        return True


def get_current_clubs_needing_addresses():
    """Get clubs that don't have addresses or need updates"""

    return execute_query(
        """
        SELECT DISTINCT name 
        FROM clubs 
        ORDER BY name
    """
    )


def update_club_address(club_name, address):
    """Update club address in database"""

    try:
        success = execute_update(
            "UPDATE clubs SET club_address = %s WHERE name = %s", (address, club_name)
        )

        if success:
            print(f"  ✅ Updated database for {club_name}")
            return True
        else:
            print(f"  ❌ Failed to update database for {club_name}")
            return False

    except Exception as e:
        print(f"  ❌ Database error for {club_name}: {str(e)}")
        return False


def main():
    """Main scraping function"""

    print("🏓 APTA CHICAGO ADDRESS SCRAPER")
    print("=" * 60)

    scraper = APTAAddressScraper()

    # Get list of clubs from database
    db_clubs = get_current_clubs_needing_addresses()
    db_club_names = {club["name"].lower() for club in db_clubs}

    print(f"📊 Found {len(db_clubs)} clubs in database")

    # Scrape APTA homepage for team links
    team_links = scraper.get_club_teams_from_homepage()

    if not team_links:
        print("❌ No team links found on APTA homepage")
        return

    print(f"🔗 Found {len(team_links)} team pages to check")
    print()

    updated_count = 0
    not_found_count = 0

    # Process each team page
    for i, team_info in enumerate(team_links, 1):
        club_name = team_info["club_name"]

        print(f"[{i}/{len(team_links)}] Processing: {club_name}")

        # Check if this club is in our database
        club_name_lower = club_name.lower()
        matching_db_clubs = [
            c["name"] for c in db_clubs if c["name"].lower() == club_name_lower
        ]

        if not matching_db_clubs:
            print(f"  ⚠️ Club '{club_name}' not found in database")
            not_found_count += 1
        else:
            # Extract address from team page
            address = scraper.extract_address_from_team_page(team_info)

            if address:
                # Update all matching club names in database
                for db_club_name in matching_db_clubs:
                    if update_club_address(db_club_name, address):
                        updated_count += 1
            else:
                not_found_count += 1

        print()

        # Add delay to be respectful
        if i < len(team_links):
            time.sleep(random.uniform(1, 3))

    print("=" * 60)
    print(f"📊 SCRAPING SUMMARY:")
    print(f"  ✅ Successfully updated: {updated_count}")
    print(f"  ⚠️ No address found: {not_found_count}")
    print(f"  📝 Total processed: {len(team_links)}")

    # Show verification
    print("\n🔍 Verifying results...")
    clubs_with_addresses = execute_query(
        """
        SELECT COUNT(*) as count 
        FROM clubs 
        WHERE club_address IS NOT NULL AND club_address != ''
    """
    )[0]["count"]

    clubs_without_addresses = execute_query(
        """
        SELECT name 
        FROM clubs 
        WHERE club_address IS NULL OR club_address = ''
        ORDER BY name
    """
    )

    print(f"✅ Clubs with addresses: {clubs_with_addresses}")
    print(f"❌ Clubs without addresses: {len(clubs_without_addresses)}")

    if clubs_without_addresses:
        print("Clubs still missing addresses:")
        for club in clubs_without_addresses[:10]:  # Show first 10
            print(f"  • {club['name']}")
        if len(clubs_without_addresses) > 10:
            print(f"  ... and {len(clubs_without_addresses) - 10} more")


if __name__ == "__main__":
    main()
