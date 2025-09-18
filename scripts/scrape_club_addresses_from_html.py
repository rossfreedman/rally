#!/usr/bin/env python3

"""
Script to scrape club addresses from ClubAddresses.html file
This script extracts the addresses from the specific HTML structure shown in the file
"""

import csv
import re
from bs4 import BeautifulSoup

def scrape_club_addresses_from_html(html_file, output_file):
    """Extract club names and addresses from the HTML file"""
    
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    clubs_data = []
    
    # Use regex to find all club entries in the HTML
    # Pattern: club name in <a> tag followed by address in <div class="list_location">
    pattern = r'<a[^>]*class="lightbox-auto[^"]*"[^>]*>([^<]+)</a>.*?<div class="list_cell list_location">([^<]*)</div>'
    
    matches = re.findall(pattern, content, re.DOTALL)
    
    print(f"🔍 Found {len(matches)} club-address matches")
    
    for club_name, address in matches:
        club_name = club_name.strip()
        address = address.strip()
        
        # Skip if no address or if it's empty
        if not address or address == "":
            continue
            
        clubs_data.append({
            'club_name': club_name,
            'address': address
        })
    
    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['club_name', 'address']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for club in clubs_data:
            writer.writerow(club)
    
    print(f"✅ Successfully scraped {len(clubs_data)} club addresses")
    print(f"📁 Saved to: {output_file}")
    
    return clubs_data

if __name__ == "__main__":
    html_file = "ClubAddresses.html"
    output_file = "data/club_addresses.csv"
    
    print("🏓 Scraping club addresses from HTML file...")
    clubs_data = scrape_club_addresses_from_html(html_file, output_file)
    
    print("\n📋 Sample of scraped data:")
    for i, club in enumerate(clubs_data[:10]):
        print(f"{i+1:2d}. {club['club_name']:<20} | {club['address']}")
    
    if len(clubs_data) > 10:
        print(f"    ... and {len(clubs_data) - 10} more clubs")
