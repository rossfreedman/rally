#!/usr/bin/env python3
"""
Debug script to test the missing scrapers and see what errors occur.
"""

import os
import sys

# Add the scrapers directory to the path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'etl', 'scrapers'))

try:
    from scraper_players import scrape_league_players
    from scraper_match_scores import scrape_all_matches
    print("✅ Successfully imported scraper functions")
except ImportError as e:
    print(f"❌ Error importing scrapers: {e}")
    sys.exit(1)

def test_players_scraper():
    """Test the players scraper for CNSWPL"""
    print("\n" + "="*60)
    print("🧪 TESTING PLAYERS SCRAPER")
    print("="*60)
    
    try:
        print("🚀 Calling scrape_league_players('cnswpl', get_detailed_stats=False)")
        result = scrape_league_players('cnswpl', get_detailed_stats=False)
        
        if result:
            print(f"✅ Players scraper returned {len(result)} players")
            for player in result[:3]:  # Show first 3 players
                print(f"   - {player.get('First Name', 'N/A')} {player.get('Last Name', 'N/A')} ({player.get('Series', 'N/A')})")
        else:
            print("⚠️ Players scraper returned empty result")
            
    except Exception as e:
        print(f"❌ Players scraper failed: {e}")
        import traceback
        traceback.print_exc()

def test_match_scraper():
    """Test the match scraper for CNSWPL"""
    print("\n" + "="*60) 
    print("🧪 TESTING MATCH SCRAPER")
    print("="*60)
    
    try:
        print("🚀 Calling scrape_all_matches('cnswpl')")
        scrape_all_matches('cnswpl')
        print("✅ Match scraper completed")
        
    except Exception as e:
        print(f"❌ Match scraper failed: {e}")
        import traceback
        traceback.print_exc()

def check_file_outputs():
    """Check what files exist in the CNSWPL directory"""
    print("\n" + "="*60)
    print("📁 CHECKING FILE OUTPUTS")
    print("="*60)
    
    cnswpl_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'leagues', 'CNSWPL')
    
    if os.path.exists(cnswpl_dir):
        files = os.listdir(cnswpl_dir)
        print(f"📂 Files in {cnswpl_dir}:")
        for file in files:
            file_path = os.path.join(cnswpl_dir, file)
            file_size = os.path.getsize(file_path)
            print(f"   - {file} ({file_size:,} bytes)")
    else:
        print(f"❌ Directory does not exist: {cnswpl_dir}")

if __name__ == "__main__":
    print("🔧 Debug Script for Missing Scrapers")
    print("Testing CNSWPL scrapers to identify issues...")
    
    # Check current file state
    check_file_outputs()
    
    # Test players scraper (the main missing one)
    test_players_scraper()
    
    # Check files again
    check_file_outputs()
    
    # Test match scraper 
    test_match_scraper()
    
    # Final file check
    check_file_outputs()
    
    print("\n🏁 Debug complete!") 