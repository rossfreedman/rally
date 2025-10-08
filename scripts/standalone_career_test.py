#!/usr/bin/env python3
"""
Standalone career stats extraction test - NO stealth browser, NO proxies.
Clean approach to test different methods for getting career stats.
"""

import time
import re
import requests
from bs4 import BeautifulSoup

def test_requests_approach():
    """Test using simple requests library."""
    print("🌐 Testing Simple Requests Approach")
    print("=" * 40)
    
    # Test with Sonja Baichwal (we know she has 9W/3L career stats)
    test_url = "https://cnswpl.tenniscores.com/player.php?p=nndz-WkM2eHhyNzhoQT09"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        print(f"🔗 URL: {test_url}")
        response = requests.get(test_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            html_content = response.text
            print(f"✅ Requests successful: {len(html_content)} characters")
            
            # Analyze content
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for career indicators
            indicators = {
                'chronological': 'chronological' in html_content.lower(),
                'expand all': 'expand all' in html_content.lower(),
                'night league': 'night league' in html_content.lower(),
                'series e': 'series e' in html_content.lower(),
                'apta women': 'apta women' in html_content.lower(),
                'vs tennaqua': 'vs tennaqua' in html_content.lower(),
                'match dates': len(re.findall(r'\d{2}/\d{2}/\d{2}', html_content)) > 0,
                'tables': len(soup.find_all('table')) > 0,
            }
            
            print(f"📊 Content analysis:")
            for key, found in indicators.items():
                status = "✅" if found else "❌"
                print(f"   {status} {key}: {found}")
            
            # Try different extraction methods
            methods = [
                ("Simple W/L", len(re.findall(r'\bW\b', html_content)), len(re.findall(r'\bL\b', html_content))),
                ("Table cells", len(soup.find_all('td', string=re.compile(r'^W$'))), len(soup.find_all('td', string=re.compile(r'^L$')))),
                ("Result context", len(re.findall(r'Result.*?W', html_content, re.IGNORECASE)), len(re.findall(r'Result.*?L', html_content, re.IGNORECASE))),
            ]
            
            print(f"📊 Extraction methods:")
            for method_name, w_count, l_count in methods:
                print(f"   {method_name}: {w_count}W/{l_count}L")
            
            return html_content
        else:
            print(f"❌ Requests failed: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Requests error: {e}")
        return None

def test_selenium_basic():
    """Test using basic Selenium without stealth."""
    print("\n🤖 Testing Basic Selenium Approach")
    print("=" * 40)
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        
        # Basic Chrome options
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        # Don't use headless so we can see what's happening
        # options.add_argument("--headless")
        
        driver = webdriver.Chrome(options=options)
        
        test_url = "https://cnswpl.tenniscores.com/player.php?p=nndz-WkM2eHhyNzhoQT09"
        
        print(f"🔗 URL: {test_url}")
        driver.get(test_url)
        time.sleep(5)
        
        # Take screenshot to see what loaded
        driver.save_screenshot("selenium_basic_initial.png")
        print("📸 Screenshot saved: selenium_basic_initial.png")
        
        # Get initial content
        initial_html = driver.page_source
        print(f"📄 Initial HTML: {len(initial_html)} characters")
        
        # Look for and click chronological checkbox
        try:
            checkbox = driver.find_element(By.XPATH, "//input[@type='checkbox']")
            is_checked = checkbox.is_selected()
            print(f"✅ Found checkbox, checked: {is_checked}")
            
            if not is_checked:
                print("🔄 Clicking chronological checkbox...")
                checkbox.click()
                time.sleep(8)  # Wait for AJAX
                
                # Take screenshot after clicking
                driver.save_screenshot("selenium_basic_after_click.png")
                print("📸 Screenshot saved: selenium_basic_after_click.png")
        
        except Exception as e:
            print(f"⚠️ Checkbox interaction failed: {e}")
        
        # Get final content
        final_html = driver.page_source
        print(f"📄 Final HTML: {len(final_html)} characters")
        
        # Analyze content change
        if len(final_html) > len(initial_html):
            print(f"✅ Content grew by {len(final_html) - len(initial_html)} characters")
        else:
            print(f"⚠️ Content didn't grow - AJAX may not be working")
        
        # Save HTML for inspection
        with open('selenium_basic_final.html', 'w', encoding='utf-8') as f:
            f.write(final_html)
        print("💾 Saved selenium_basic_final.html")
        
        # Analyze for career content
        soup = BeautifulSoup(final_html, 'html.parser')
        tables = soup.find_all('table')
        
        print(f"📊 Analysis:")
        print(f"   Tables found: {len(tables)}")
        
        # Look for specific career content
        career_indicators = [
            'NIGHT LEAGUE',
            'SERIES E', 
            'APTA WOMEN',
            'vs Tennaqua',
            'vs Valley Lo',
            'Evanston E (H)',
        ]
        
        found_indicators = [indicator for indicator in career_indicators if indicator in final_html]
        print(f"   Career indicators: {found_indicators}")
        
        # Count W/L
        w_count = len(re.findall(r'\bW\b', final_html))
        l_count = len(re.findall(r'\bL\b', final_html))
        print(f"   W/L count: {w_count}W/{l_count}L")
        
        # Keep browser open for manual inspection
        print("\n🔍 Browser window left open for manual inspection")
        input("Press Enter to close browser...")
        
        driver.quit()
        return final_html
        
    except Exception as e:
        print(f"❌ Selenium error: {e}")
        return None

def test_requests_session():
    """Test using requests session to maintain cookies."""
    print("\n🍪 Testing Requests Session with Cookies")
    print("=" * 45)
    
    session = requests.Session()
    
    # Set headers
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    })
    
    try:
        # First, visit the main site to get cookies
        print("🏠 Visiting main site to get cookies...")
        main_response = session.get("https://cnswpl.tenniscores.com/", timeout=30)
        print(f"   Main site: {main_response.status_code}")
        
        # Then visit the player page
        test_url = "https://cnswpl.tenniscores.com/player.php?p=nndz-WkM2eHhyNzhoQT09"
        print(f"🔗 Player page: {test_url}")
        
        player_response = session.get(test_url, timeout=30)
        
        if player_response.status_code == 200:
            html_content = player_response.text
            print(f"✅ Session request successful: {len(html_content)} characters")
            
            # Look for career content
            career_found = [
                ('NIGHT LEAGUE', 'NIGHT LEAGUE' in html_content),
                ('SERIES E', 'SERIES E' in html_content),
                ('Match dates', len(re.findall(r'\d{2}/\d{2}/\d{2}', html_content)) > 0),
                ('vs patterns', 'vs ' in html_content),
            ]
            
            print(f"📊 Career content search:")
            for name, found in career_found:
                status = "✅" if found else "❌"
                print(f"   {status} {name}")
            
            # Save for inspection
            with open('requests_session_content.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
            print("💾 Saved requests_session_content.html")
            
            return html_content
        else:
            print(f"❌ Session request failed: {player_response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Session error: {e}")
        return None

def main():
    """Run all standalone tests."""
    print("🎾 Standalone Career Stats Testing")
    print("=" * 50)
    print("Testing different approaches without stealth/proxy infrastructure")
    
    # Test 1: Simple requests
    requests_html = test_requests_approach()
    
    # Test 2: Basic Selenium (if requests shows promise)
    if requests_html and len(requests_html) > 20000:
        selenium_html = test_selenium_basic()
    else:
        print("\n⚠️ Skipping Selenium test - requests didn't get good content")
        selenium_html = None
    
    # Test 3: Requests with session
    session_html = test_requests_session()
    
    # Summary
    print(f"\n📊 SUMMARY:")
    print(f"   Requests: {'✅' if requests_html and len(requests_html) > 20000 else '❌'}")
    print(f"   Selenium: {'✅' if selenium_html and len(selenium_html) > 20000 else '❌'}")
    print(f"   Session:  {'✅' if session_html and len(session_html) > 20000 else '❌'}")
    
    # Check if any approach found career content
    career_content_found = False
    for html in [requests_html, selenium_html, session_html]:
        if html and any(indicator in html for indicator in ['NIGHT LEAGUE', 'SERIES E', 'vs Tennaqua']):
            career_content_found = True
            break
    
    if career_content_found:
        print(f"🎉 SUCCESS: At least one approach found career content!")
    else:
        print(f"⚠️ NO CAREER CONTENT: All approaches failed to get career data")
        print(f"💡 The website may be blocking ALL automated access to career stats")

if __name__ == "__main__":
    main()
