#!/usr/bin/env python3
"""
Debug CNSWPL Match Parsing
==========================

This script helps debug why the CNSWPL match scraper isn't finding any matches.
It will show the actual HTML content being parsed.
"""

import os
import sys

sys.path.append(
    os.path.join(os.path.dirname(__file__), "..", "data", "etl", "scrapers")
)

import json
import re
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def create_driver():
    """Create a Chrome WebDriver instance."""
    print("🚀 Creating Chrome driver...")
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920x1080")

    # Add user agent to avoid bot detection
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    return webdriver.Chrome(options=options)


def debug_cnswpl_parsing():
    """Debug CNSWPL parsing to see what content is actually extracted."""
    print("🧪 CNSWPL Parsing Debug Tool")
    print("=" * 60)

    # Use one of the CNSWPL division URLs from the logs
    test_url = "https://cnswpl.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NqN1FMcGpx&did=nndz-WkNld3hyci8%3D"

    driver = None
    try:
        driver = create_driver()

        print(f"🌐 Navigating to: {test_url}")
        driver.get(test_url)

        # Wait for page to load
        time.sleep(3)

        print("📊 Initial page title:", driver.title)
        print("📊 Initial page URL:", driver.current_url)

        print("\n🔍 Looking for Matches link...")
        try:
            matches_link = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.LINK_TEXT, "Matches"))
            )
            print("✅ Found Matches link, clicking...")
            matches_link.click()
            time.sleep(3)

            print("📊 After clicking Matches - URL:", driver.current_url)
            print("📊 After clicking Matches - Title:", driver.title)

        except Exception as e:
            print(f"❌ Could not find Matches link: {e}")
            print("🔍 Available links on page:")
            links = driver.find_elements(By.TAG_NAME, "a")
            for i, link in enumerate(links[:10]):  # Show first 10 links
                text = link.text.strip()
                href = link.get_attribute("href")
                if text:
                    print(f"  {i+1}. '{text}' -> {href}")
            return

        print("\n🔍 Looking for match results container...")
        try:
            match_container = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "match_results_container"))
            )
            print("✅ Found match results container")
        except Exception as e:
            print(f"❌ Could not find match results container: {e}")

            # Try alternative selectors
            print("🔍 Looking for alternative containers...")
            alternatives = [
                ("div", "match_results"),
                ("div", "results"),
                ("div", "matches"),
                ("table", "match"),
                ("div", "match-results"),
            ]

            for tag, class_name in alternatives:
                try:
                    elements = driver.find_elements(
                        By.CSS_SELECTOR, f"{tag}[class*='{class_name}']"
                    )
                    if elements:
                        print(
                            f"✅ Found {len(elements)} elements with {tag}.{class_name}"
                        )
                        match_container = elements[0]
                        break
                except:
                    continue
            else:
                print("❌ No alternative containers found")
                return

        print("\n🔍 Extracting HTML content from container...")
        html_content = match_container.get_attribute("innerHTML")
        print(f"📊 HTML content length: {len(html_content)} characters")

        # Parse with BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")

        print("\n🔍 Analyzing HTML structure...")
        print(f"📊 Total elements in container: {len(soup.find_all())}")

        # Show element breakdown
        element_counts = {}
        for element in soup.find_all():
            tag = element.name
            element_counts[tag] = element_counts.get(tag, 0) + 1

        print("📊 Element breakdown:")
        for tag, count in sorted(element_counts.items()):
            print(f"  {tag}: {count}")

        print("\n🔍 Extracting all text content...")
        all_text = soup.get_text()
        lines = [line.strip() for line in all_text.split("\n") if line.strip()]

        print(f"📊 Total text lines: {len(lines)}")
        print("\n📋 First 20 lines of text content:")
        for i, line in enumerate(lines[:20], 1):
            print(f"  {i:2d}: {line}")

        if len(lines) > 20:
            print(f"     ... and {len(lines) - 20} more lines")

        print("\n🔍 Looking for date patterns...")
        date_patterns = [
            r"(\w+\s+\d{1,2},\s+\d{4})\s+\d{1,2}:\d{2}\s+(am|pm)",
            r"(\w+\s+\d{1,2},\s+\d{4})",
            r"(\d{1,2}/\d{1,2}/\d{4})",
            r"(\d{1,2}-\d{1,2}-\d{4})",
        ]

        dates_found = []
        for line in lines:
            for pattern in date_patterns:
                matches = re.findall(pattern, line, re.IGNORECASE)
                if matches:
                    dates_found.extend(matches)
                    print(f"  📅 Found date pattern in: {line}")

        if dates_found:
            print(f"📊 Total dates found: {len(dates_found)}")
        else:
            print("❌ No date patterns found")

        print("\n🔍 Looking for team/score patterns...")
        team_patterns = [
            r"^(.+?)\s+(\d+(?:\.\d+)?)\s*$",
            r"(.+?)\s+vs\s+(.+?)",
            r"(.+?)\s+(\d+)\s+(.+?)\s+(\d+)",
        ]

        teams_found = []
        for line in lines:
            for pattern in team_patterns:
                matches = re.findall(pattern, line)
                if matches:
                    teams_found.extend(matches)
                    print(f"  🏆 Found team pattern in: {line}")

        if teams_found:
            print(f"📊 Total team patterns found: {len(teams_found)}")
        else:
            print("❌ No team patterns found")

        print("\n🔍 Looking for player patterns...")
        player_patterns = [
            r"(.+?)\s*/\s*(.+?)\s+(\d+[-]\d+)",
            r"(.+?)\s*/\s*(.+?)\s+(By Forfeit|Forfeit)",
            r"(.+?)\s*/\s*(.+?)",
        ]

        players_found = []
        for line in lines:
            for pattern in player_patterns:
                matches = re.findall(pattern, line, re.IGNORECASE)
                if matches:
                    players_found.extend(matches)
                    print(f"  👥 Found player pattern in: {line}")

        if players_found:
            print(f"📊 Total player patterns found: {len(players_found)}")
        else:
            print("❌ No player patterns found")

        print("\n🔍 Raw HTML sample (first 1000 chars):")
        print("-" * 50)
        print(html_content[:1000])
        if len(html_content) > 1000:
            print(f"\n... and {len(html_content) - 1000} more characters")
        print("-" * 50)

        print("\n🔍 Checking for JavaScript-rendered content...")
        # Wait a bit more and check if content changes
        time.sleep(5)

        updated_html = match_container.get_attribute("innerHTML")
        if len(updated_html) != len(html_content):
            print(f"📊 Content changed! New length: {len(updated_html)} characters")
            print("🔍 This suggests JavaScript is loading content dynamically")
        else:
            print("📊 Content unchanged - likely static HTML")

        print("\n🔍 Looking for specific CNSWPL elements...")
        cnswpl_selectors = [
            "div.match_results_table",
            "div[class*='match']",
            "div[class*='result']",
            "table[class*='match']",
            "div[style*='background-color']",
            ".team_name",
            ".match_rest",
        ]

        for selector in cnswpl_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(
                        f"✅ Found {len(elements)} elements with selector: {selector}"
                    )
                    # Show content of first element
                    first_element = elements[0]
                    content = first_element.text.strip()
                    print(f"     First element content: {content[:100]}...")
                else:
                    print(f"❌ No elements found with selector: {selector}")
            except Exception as e:
                print(f"❌ Error with selector {selector}: {e}")

        print("\n🎯 Final Analysis:")
        print("=" * 50)
        if len(lines) <= 1:
            print(
                "❌ PROBLEM: Only 1 line of text found - suggests empty or minimal content"
            )
            print("💡 This explains why the scraper finds 0 matches")
            print("💡 Possible causes:")
            print("   - JavaScript-rendered content not fully loaded")
            print("   - Different HTML structure than expected")
            print("   - Authentication/access issues")
            print("   - Wrong URL or navigation path")
        else:
            print(f"✅ Found {len(lines)} lines of text - content seems present")
            if not dates_found and not teams_found and not players_found:
                print("❌ PROBLEM: No match data patterns found")
                print("💡 Content is present but parsing patterns don't match")
                print("💡 Parsing logic may need adjustment")
            else:
                print("✅ Found some match data patterns - parsing might work")

    except Exception as e:
        print(f"❌ Error during debugging: {e}")
        import traceback

        traceback.print_exc()

    finally:
        if driver:
            driver.quit()
            print("\n✅ Cleaned up browser")


if __name__ == "__main__":
    debug_cnswpl_parsing()
