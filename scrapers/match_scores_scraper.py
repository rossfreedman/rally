from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import csv
import re
import time
import os
from datetime import datetime

# Set up Chrome options
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in headless mode
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920x1080")

# Initialize the Chrome driver
service = Service()
driver = webdriver.Chrome(service=service, options=chrome_options)

# URL to scrape
url = 'https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yalNnT1VzYk5Ndz09&did=nndz-WnkrNXhiWT0%3D'

try:
    # Navigate to the URL
    driver.get(url)
    
    # Wait for the page to load
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, "match_results_container"))
    )
    
    # Create a CSV file to store the data
    current_date = datetime.now().strftime("%Y%m%d")
    
    # Set the path to the data folder (one level up from the scrapers folder)
    data_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    
    # Create the data folder if it doesn't exist
    if not os.path.exists(data_folder):
        os.makedirs(data_folder)
    
    # Create the full path to the CSV file
    csv_filename = os.path.join(data_folder, f"tennis_matches_{current_date}.csv")
    
    with open(csv_filename, 'w', newline='') as csvfile:
        # Create CSV writer
        csvwriter = csv.writer(csvfile)
        # Write header
        csvwriter.writerow(['Date', 'Home Team', 'Away Team', 'Home Player 1', 'Home Player 2', 'Away Player 1', 'Away Player 2', 'Scores', 'Winner'])
        
        # Find all match result tables
        match_tables = driver.find_elements(By.CLASS_NAME, "match_results_table")
        
        for table in match_tables:
            try:
                # Find the match header (contains date and club names)
                header_row = table.find_element(By.CSS_SELECTOR, "div[style*='background-color: #dcdcdc;']")
                
                # Extract date from the header
                date_element = header_row.find_element(By.CLASS_NAME, "match_rest")
                date_text = date_element.text
                match_date = re.search(r'(\w+ \d+, \d{4})', date_text)
                if match_date:
                    date_str = match_date.group(1)
                    date_obj = datetime.strptime(date_str, '%B %d, %Y')
                    date = date_obj.strftime('%d-%b-%y')
                else:
                    date = "Unknown"
                
                # Extract club names from the header
                home_club_element = header_row.find_element(By.CLASS_NAME, "team_name")
                away_club_element = header_row.find_element(By.CLASS_NAME, "team_name2")
                
                # Get the full team names including the "- 22" suffix
                home_club_full = home_club_element.text.strip()
                away_club_full = away_club_element.text.strip()
                
                # Find all player rows in this table
                player_divs = table.find_elements(By.XPATH, ".//div[not(contains(@style, 'background-color')) and not(contains(@class, 'clear clearfix'))]")
                
                i = 0
                while i < len(player_divs) - 4:  # Need at least 5 elements for a complete match row
                    try:
                        # Check if this is a player match row (has points, team_name, match_rest, team_name2, points2)
                        if ("points" in player_divs[i].get_attribute("class") and 
                            "team_name" in player_divs[i+1].get_attribute("class") and 
                            "match_rest" in player_divs[i+2].get_attribute("class") and 
                            "team_name2" in player_divs[i+3].get_attribute("class")):
                            
                            # Extract data
                            home_text = player_divs[i+1].text.strip()
                            score = player_divs[i+2].text.strip()
                            away_text = player_divs[i+3].text.strip()
                            
                            # Skip if this is not a match (e.g., it's a header or contains date)
                            if not score or re.search(r'\d{1,2}:\d{2}', score) or "Date" in score:
                                i += 5
                                continue
                            
                            # Determine winner
                            winner_img_home = player_divs[i].find_elements(By.TAG_NAME, "img")
                            winner_img_away = player_divs[i+4].find_elements(By.TAG_NAME, "img") if i+4 < len(player_divs) else []
                            
                            if winner_img_home:
                                winner = "home"
                            elif winner_img_away:
                                winner = "away"
                            else:
                                winner = "unknown"
                            
                            # Split player names
                            home_players = home_text.split("/")
                            away_players = away_text.split("/")
                            
                            home_player1 = home_players[0].strip() if len(home_players) > 0 else ""
                            home_player2 = home_players[1].strip() if len(home_players) > 1 else ""
                            away_player1 = away_players[0].strip() if len(away_players) > 0 else ""
                            away_player2 = away_players[1].strip() if len(away_players) > 1 else ""
                            
                            # Write to CSV
                            csvwriter.writerow([
                                date, 
                                home_club_full,  # Use full team name including "- 22" 
                                away_club_full,  # Use full team name including "- 22"
                                home_player1, 
                                home_player2, 
                                away_player1, 
                                away_player2, 
                                score, 
                                winner
                            ])
                            
                            i += 5  # Move to the next potential match row
                        else:
                            i += 1  # Move to the next div
                    except Exception as e:
                        i += 1  # Skip this div if there's an error
            
            except Exception as e:
                print(f"Error processing match table: {str(e)}")
    
    print(f"Data has been written to {csv_filename}")

except Exception as e:
    print(f"Error occurred: {str(e)}")
    import traceback
    traceback.print_exc()

finally:
    driver.quit()
