#!/usr/bin/env python3

"""
Debug script to diagnose SW series discovery issue
"""

import requests
from bs4 import BeautifulSoup

def debug_series_discovery():
    """Debug what series are found on APTA Chicago main page"""
    
    print("🔍 Debugging SW Series Discovery Issue")
    print("=" * 50)
    
    base_url = "https://aptachicago.tenniscores.com"
    
    try:
        print(f"📄 Accessing main page: {base_url}")
        response = requests.get(base_url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find all series elements using the same method as schedule scraper
        series_elements = soup.find_all("div", class_="div_list_option")
        print(f"🏆 Found {len(series_elements)} series elements")
        print()
        
        sw_series_found = []
        regular_series_found = []
        
        for i, element in enumerate(series_elements, 1):
            try:
                series_link = element.find("a")
                if series_link and series_link.text:
                    series_number = series_link.text.strip()
                    series_url = series_link.get("href", "")
                    
                    print(f"{i:2d}. '{series_number}' -> {series_url}")
                    
                    # Check if this is an SW series
                    if "SW" in series_number:
                        sw_series_found.append(series_number)
                    else:
                        regular_series_found.append(series_number)
                        
            except Exception as e:
                print(f"    ❌ Error processing element {i}: {e}")
        
        print()
        print("📊 DISCOVERY SUMMARY:")
        print(f"   Regular series found: {len(regular_series_found)}")
        print(f"   SW series found: {len(sw_series_found)}")
        print()
        
        if sw_series_found:
            print("✅ SW SERIES FOUND:")
            for series in sorted(sw_series_found):
                print(f"   - {series}")
        else:
            print("❌ NO SW SERIES FOUND - This is the problem!")
            
        print()
        if regular_series_found[:10]:  # Show first 10
            print("📋 REGULAR SERIES SAMPLE:")
            for series in sorted(regular_series_found)[:10]:
                print(f"   - {series}")
            if len(regular_series_found) > 10:
                print(f"   ... and {len(regular_series_found) - 10} more")
        
        # Also check for alternative discovery methods
        print()
        print("🔍 ALTERNATIVE DISCOVERY METHODS:")
        
        # Method 1: Look for any links with SW in text
        all_links = soup.find_all("a", href=True)
        sw_links = []
        for link in all_links:
            text = link.text.strip()
            if "SW" in text and text not in [x for x in sw_series_found]:
                sw_links.append((text, link.get("href", "")))
        
        if sw_links:
            print(f"   Found {len(sw_links)} additional SW links:")
            for text, href in sw_links[:5]:  # Show first 5
                print(f"   - '{text}' -> {href}")
        else:
            print("   No additional SW links found")
            
        # Method 2: Look at page structure
        print()
        print("🔍 PAGE STRUCTURE ANALYSIS:")
        div_classes = set()
        for div in soup.find_all("div", class_=True):
            if isinstance(div.get("class"), list):
                div_classes.update(div.get("class"))
        
        relevant_classes = [cls for cls in div_classes if any(keyword in cls.lower() for keyword in ['list', 'option', 'series', 'div'])]
        print(f"   Relevant div classes found: {sorted(relevant_classes)}")
        
        return sw_series_found, regular_series_found
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return [], []

if __name__ == "__main__":
    debug_series_discovery() 