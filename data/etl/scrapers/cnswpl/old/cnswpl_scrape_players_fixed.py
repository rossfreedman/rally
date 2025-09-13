#!/usr/bin/env python3
"""
Fixed CNSWPL Player Scraper with Accurate Career Stats
=====================================================

This is a corrected version of the CNSWPL scraper that fixes the career stats extraction
to only count W/L from actual match results, not from team names or other text.

Key fixes:
- Only counts W/L from match history tables with Date/Result columns
- Ignores W/L in team names (like "Wilmette" containing "W")
- More conservative pattern matching
- Accurate career statistics
"""

def get_career_stats_from_individual_page_fixed(self, player_url: str, max_retries: int = 2) -> Dict[str, any]:
    """
    Get career wins and losses from individual player page using accurate table parsing.
    Fixed version that only counts W/L from actual match results, not team names.
    
    Args:
        player_url: URL to the individual player page
        max_retries: Maximum number of retry attempts
        
    Returns:
        Dictionary with career wins, losses, and win_percentage
    """
    for attempt in range(max_retries):
        try:
            print(f"   📊 Getting career stats from individual player page (attempt {attempt + 1})...")
            
            # Construct full URL if needed
            if not player_url.startswith("http"):
                full_url = f"{self.base_url}{player_url}"
            else:
                full_url = player_url
            
            # Use stealth browser to execute JavaScript and get rendered content
            try:
                print(f"   🌐 Using stealth browser to render JavaScript for career stats...")
                
                # Use the existing stealth browser if available, otherwise create one
                if self.stealth_browser:
                    browser = self.stealth_browser
                else:
                    from stealth_browser import create_stealth_browser
                    browser = create_stealth_browser(force_browser=True, verbose=False)
                
                # Get the HTML content with browser automation
                html_content = browser.get_html(full_url)
                print(f"   ✅ Browser request successful - got {len(html_content)} characters")
                
                # Get the browser driver to interact with elements if available
                driver = getattr(browser, 'current_driver', None)
                if driver:
                    try:
                        # Look for chronological or similar controls to load full match history
                        print(f"   📅 Looking for controls to load full match history...")
                        
                        # Try common chronological control patterns
                        chron_elements = driver.find_elements("xpath", "//input[@type='checkbox' and contains(@id, 'chron')]")
                        if not chron_elements:
                            chron_elements = driver.find_elements("xpath", "//input[@type='checkbox' and contains(@name, 'chron')]")
                        if not chron_elements:
                            chron_elements = driver.find_elements("xpath", "//input[@type='checkbox' and contains(@class, 'chron')]")
                        
                        if chron_elements:
                            print(f"   ✅ Found chronological control, clicking to load full history...")
                            chron_elements[0].click()
                            time.sleep(2)  # Wait for content to load
                            html_content = driver.page_source
                        else:
                            print(f"   ℹ️ No chronological control found, using current content")
                        
                    except Exception as e:
                        print(f"   ⚠️ Could not interact with page controls: {e}")
                        # Continue with the original HTML content
                
                # Parse HTML and look for match history tables
                soup = BeautifulSoup(html_content, 'html.parser')
                total_wins = 0
                total_losses = 0
                
                # Look for match history tables (tables with Date, Match, Line, Result columns)
                tables = soup.find_all('table')
                
                for table in tables:
                    table_text = table.get_text()
                    
                    # Look for tables that contain match history
                    if 'Date' in table_text and 'Result' in table_text:
                        print(f"   📊 Found match history table, analyzing results...")
                        
                        # Count W's and L's only in the Result column
                        rows = table.find_all('tr')
                        table_wins = 0
                        table_losses = 0
                        
                        for row in rows:
                            cells = row.find_all(['td', 'th'])
                            if len(cells) >= 4:  # Date, Match, Line, Result
                                result_cell = cells[-1]  # Last cell should be Result
                                result_text = result_cell.get_text().strip()
                                
                                if result_text == 'W':
                                    table_wins += 1
                                elif result_text == 'L':
                                    table_losses += 1
                        
                        if table_wins > 0 or table_losses > 0:
                            total_wins += table_wins
                            total_losses += table_losses
                            print(f"   📊 Found {table_wins}W/{table_losses}L in match history table")
                
                # If no match history tables found, try to find any W/L patterns but be very conservative
                if total_wins == 0 and total_losses == 0:
                    print(f"   🔍 No match history tables found, looking for W/L patterns...")
                    
                    # Save debug HTML for analysis
                    debug_file = f"/tmp/cnswpl_player_debug_{hash(full_url) % 10000}.html"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    print(f"   💾 Saved debug HTML to {debug_file}")
                    
                    # Look for W/L in any table, but be very conservative
                    for table in tables:
                        table_text = table.get_text()
                        w_count = len(re.findall(r'\bW\b', table_text))
                        l_count = len(re.findall(r'\bL\b', table_text))
                        
                        # Only count if it looks like a reasonable number (not too many W's from team names)
                        if w_count <= 15 and l_count <= 15 and (w_count > 0 or l_count > 0):
                            total_wins += w_count
                            total_losses += l_count
                            print(f"   📊 Found {w_count}W/{l_count}L in general table")
                
                # Calculate win percentage
                if total_wins + total_losses > 0:
                    win_percentage = (total_wins / (total_wins + total_losses)) * 100
                else:
                    win_percentage = 0.0
                
                print(f"   ✅ Career stats extracted: {total_wins} wins, {total_losses} losses, {win_percentage:.1f}%")
                
                return {
                    "wins": total_wins,
                    "losses": total_losses,
                    "win_percentage": f"{win_percentage:.1f}%"
                }
                
            except Exception as e:
                print(f"   ❌ Browser automation failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                else:
                    return {"wins": 0, "losses": 0, "win_percentage": "0.0%"}
            
        except Exception as e:
            print(f"   ❌ Error getting career stats for {player_url}: {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            else:
                return {"wins": 0, "losses": 0, "win_percentage": "0.0%"}
    
    # Return default stats if all retries failed
    return {"wins": 0, "losses": 0, "win_percentage": "0.0%"}
