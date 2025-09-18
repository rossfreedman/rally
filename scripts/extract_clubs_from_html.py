#!/usr/bin/env python3

"""
Script to extract club names from ClubAddresses.html file
"""

import re
from bs4 import BeautifulSoup

def extract_club_names_from_html(html_file):
    """Extract unique club names from the HTML file"""
    
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    soup = BeautifulSoup(content, 'html.parser')
    
    # Find all team links
    team_links = soup.find_all('a', href=re.compile(r'team='))
    
    clubs = set()
    
    for link in team_links:
        text = link.get_text(strip=True)
        
        # Extract club name (remove series numbers and suffixes)
        # Pattern: "Club Name - Series" or "Club Name - Series SW"
        club_name = re.sub(r'\s*-\s*\d+.*$', '', text).strip()
        
        if club_name and len(club_name) > 2:
            clubs.add(club_name)
    
    return sorted(list(clubs))

def main():
    """Main function"""
    html_file = "ClubAddresses.html"
    
    print("🏓 EXTRACTING CLUB NAMES FROM HTML")
    print("=" * 50)
    
    try:
        clubs = extract_club_names_from_html(html_file)
        
        print(f"📊 Found {len(clubs)} unique clubs:")
        print()
        
        for i, club in enumerate(clubs, 1):
            print(f"{i:2d}. {club}")
        
        print()
        print("✅ Club extraction completed!")
        print("💡 These are the clubs that need addresses.")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()
