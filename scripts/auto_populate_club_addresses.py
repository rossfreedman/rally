#!/usr/bin/env python3

"""
Automated script to populate club addresses by searching Google (non-interactive)
"""

import os
import random
import re
import sys
import time
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_update


def search_club_address(club_name, session):
    """Search Google for a club's address using the specified URL format"""

    # Use the exact format requested: club_name + country club address
    search_query = f"{club_name} country club address"

    try:
        encoded_query = quote_plus(search_query)
        url = f"https://www.google.com/search?q={encoded_query}"

        print(f"  Searching: {search_query}")
        print(f"  URL: {url}")

        # Add random delay to avoid being blocked
        time.sleep(random.uniform(2, 4))

        # Make request
        response = session.get(url, timeout=10)
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.content, "html.parser")

        # Try to find address using regex patterns in the page text
        text = soup.get_text()

        # Debug: Show first part of the response to see if we're getting blocked
        print(f"  Response preview: {text[:100]}...")

        # Address patterns to look for
        patterns = [
            # Full address with zip
            r"\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Way|Court|Ct|Place|Pl)\s*,?\s*[A-Za-z\s]+,?\s*[A-Z]{2}\s+\d{5}",
            # Address without full state/zip but with IL/PA
            r"\d+\s+[A-Za-z\s\.]+(?:St|Ave|Rd|Dr|Ln|Blvd|Way|Ct|Pl)\s*,?\s*[A-Za-z\s]+,?\s*(?:IL|PA|Chicago|Philadelphia)",
            # Street number and name followed by city (more flexible)
            r"\d+\s+[A-Za-z\s\.]+(?:St|Ave|Rd|Dr|Ln|Blvd|Way|Ct|Pl)\s*,?\s*[A-Za-z\s]+",
            # Alternative pattern for addresses that might not follow standard format
            r"\d+\s+[A-Za-z]+\s+[A-Za-z]+\s*,?\s*[A-Za-z\s]+,?\s*[A-Z]{2}",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Return the first reasonable match
                for match in matches:
                    if 15 <= len(match) <= 100:  # Reasonable length (lowered min)
                        clean_match = match.strip()
                        print(f"  ✓ Found address: {clean_match}")
                        return clean_match

        print(f"  ✗ No address found in search results")
        return None

    except Exception as e:
        print(f"  ❌ Error searching for {club_name}: {str(e)}")
        return None


def main():
    """Main function to populate missing club addresses"""

    print("🔍 Auto-populating missing club addresses from Google search...")
    print("=" * 60)

    # Check if required packages are available
    try:
        import bs4
        import requests
    except ImportError as e:
        print("❌ Required packages not installed.")
        print("Please install them with: pip install requests beautifulsoup4")
        sys.exit(1)

    # Get clubs without addresses
    clubs_without_addresses = execute_query(
        """
        SELECT id, name 
        FROM clubs 
        WHERE club_address IS NULL OR club_address = ''
        ORDER BY name
    """
    )

    if not clubs_without_addresses:
        print("✅ All clubs already have addresses!")
        return

    print(f"Found {len(clubs_without_addresses)} clubs without addresses")
    print()

    # Create session with realistic headers
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
    )

    updated_count = 0
    failed_count = 0

    for i, club in enumerate(clubs_without_addresses, 1):
        club_id = club["id"]
        club_name = club["name"]

        print(f"[{i}/{len(clubs_without_addresses)}] Processing: {club_name}")

        # Search for address
        address = search_club_address(club_name, session)

        if address:
            # Update database
            try:
                success = execute_update(
                    "UPDATE clubs SET club_address = %s WHERE id = %s",
                    (address, club_id),
                )

                if success:
                    print(f"  ✅ Updated database with address")
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
            time.sleep(random.uniform(3, 6))

    print("=" * 60)
    print(f"📊 SUMMARY:")
    print(f"  ✅ Successfully updated: {updated_count}")
    print(f"  ❌ Failed/Not found: {failed_count}")
    print(f"  📝 Total processed: {len(clubs_without_addresses)}")

    # Show remaining clubs without addresses
    remaining_clubs = execute_query(
        """
        SELECT name 
        FROM clubs 
        WHERE club_address IS NULL OR club_address = ''
        ORDER BY name
    """
    )

    print(f"\n📋 Remaining clubs without addresses: {len(remaining_clubs)}")
    if remaining_clubs:
        for club in remaining_clubs[:10]:  # Show first 10
            print(f"  • {club['name']}")
        if len(remaining_clubs) > 10:
            print(f"  ... and {len(remaining_clubs) - 10} more")


if __name__ == "__main__":
    try:
        main()
        print("\n✅ Club address population completed!")
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)
