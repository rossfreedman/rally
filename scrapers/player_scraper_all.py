import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO
from datetime import datetime
import csv
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Updated division lookup
division_lookup = {
    '19022': 'Chicago Legends',
    '19029': 'Chicago 2',
    '19030': 'Chicago 3',
    '19031': 'Chicago 4',
    '19032': 'Chicago 5',
    '19033': 'Chicago 7',
    '19034': 'Chicago 8',
    '19035': 'Chicago 9',
    '19036': 'Chicago 10',
    '19037': 'Chicago 11',
    '19038': 'Chicago 12',
    '19039': 'Chicago 13',
    '19040': 'Chicago 14',
    '19041': 'Chicago 15',
    '19042': 'Chicago 16',
    '19043': 'Chicago 17',
    '19044': 'Chicago 18',
    '19045': 'Chicago 19',
    '19046': 'Chicago 20',
    '19047': 'Chicago 21',
    '19048': 'Chicago 22',
    '19049': 'Chicago 23',
    '19050': 'Chicago 24',
    '19051': 'Chicago 25',
    '19052': 'Chicago 26',
    '19053': 'Chicago 27',
    '19054': 'Chicago 28',
    '19055': 'Chicago 29',
    '19056': 'Chicago 30',
    '19066': 'Chicago 6',
    '19068': 'Chicago 25 SW',
    '19069': 'Chicago 15 SW',
    '19070': 'Chicago 17 SW',
    '19071': 'Chicago 21 SW',
    '19072': 'Chicago 11 SW',
    '19073': 'Chicago 19 SW',
    '19076': 'Chicago 9 SW',
    '19078': 'Chicago 31',
    '19556': 'Chicago 7 SW',
    '19558': 'Chicago 23 SW',
    '19559': 'Chicago 13 SW',
    '19560': 'Chicago 32',
    '26722': 'Chicago 34',
    '26829': 'Chicago 99',
    '27694': 'Chicago 27 SW',
    '28855': 'Chicago 1',
    '28862': 'Chicago 29 SW',
    '28865': 'Chicago 33',
    '28867': 'Chicago 35',
    '28868': 'Chicago 36',
    '28869': 'Chicago 37',
    '28870': 'Chicago 38',
    '28871': 'Chicago 39'
}

# Add the location lookup dictionary
location_lookup = {
    '16161': 'Wilmette PD',
    '16162': 'Sunset Ridge',
    '16163': 'Winnetka',
    '16164': 'Exmoor',
    '16165': 'Hinsdale PC',
    '16166': 'Onwentsia',
    '16167': 'Salt Creek',
    '16168': 'Lakeshore S&amp;F',
    '16169': 'Glen View',
    '16170': 'Prairie Club',
    '16171': 'Lake Forest',
    '16172': 'Evanston ',
    '16173': 'Midt-Bannockburn',
    '16174': 'Briarwood',
    '16175': 'Birchwood',
    '16176': 'Hinsdale GC',
    '16177': 'Butterfield',
    '16178': 'Chicago Highlands',
    '16179': 'Glen Ellyn',
    '16180': 'Skokie',
    '16181': 'Winter Club',
    '16182': 'Westmoreland',
    '16183': 'Valley Lo',
    '16184': 'Tennaqua',
    '16185': 'South Barrington',
    '16186': 'Saddle &amp; Cycle',
    '16187': 'Ruth Lake',
    '16188': 'Northmoor',
    '16189': 'North Shore',
    '16190': 'Midtown - Chicago',
    '16191': 'Michigan Shores',
    '16192': 'Lake Shore CC',
    '16193': 'Knollwood',
    '16194': 'Indian Hill',
    '16195': 'Glenbrook RC',
    '16196': 'Hawthorn Woods',
    '16197': 'Lake Bluff',
    '16198': 'Barrington Hills CC',
    '16199': 'River Forest PD',
    '16200': 'Edgewood Valley',
    '16201': 'Park Ridge CC',
    '16202': 'Medinah',
    '16203': 'LaGrange CC',
    '16204': 'Dunham Woods',
    '16432': 'BYE',
    '17241': 'Lifesport-Lshore',
    '17242': 'Biltmore CC',
    '18332': 'Bryn Mawr',
    '18333': 'Glen Oak ',
    '18334': 'Inverness ',
    '18335': 'White Eagle',
    '18364': 'Legends ',
    '19205': 'River Forest CC',
    '19312': 'Oak Park CC',
    '22561': 'Royal Melbourne'
}

def get_player_stats(player_url, driver):
    try:
        base_url = "https://aptachicago.tenniscores.com"
        full_url = f"{base_url}{player_url}" if not player_url.startswith('http') else player_url
        driver.get(full_url)
        time.sleep(2)
        
        wins = 0
        losses = 0
        content = driver.find_element(By.TAG_NAME, "body").text
        matches = content.split('\n')
        
        for line in matches:
            if line.strip() == 'W':
                wins += 1
            elif line.strip() == 'L':
                losses += 1
        
        return {
            'Wins': wins,
            'Losses': losses,
            'Win %': f"{(wins/(wins+losses)*100):.1f}%" if wins + losses > 0 else "0.0%"
        }
        
    except Exception as e:
        return {'Wins': 0, 'Losses': 0, 'Win %': '0.0%'}

def print_all_players():
    driver = None
    try:
        # Set up Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-infobars')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--ignore-ssl-errors')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')

        # Initialize Chrome driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        url = 'https://aptachicago.tenniscores.com/?mod=nndz-SkhmOW1PQ3V4Zz09'
        
        # Create directory structure if it doesn't exist
        data_dir = os.path.join('data', 'player', 'all_players_csvs')
        os.makedirs(data_dir, exist_ok=True)
        
        # Load the page
        driver.get(url)
        time.sleep(3)
        
        # Get the page source after JavaScript has run
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Initialize tracking variables
        series_players = {}  # Dictionary to store players by series
        total_players = 0
        
        # First pass: Collect all rows and sort by division
        all_rows = []
        current_series = None
        current_series_players = []
        
        # Calculate total players in the entire table
        total_players_overall = len([row for row in soup.find_all('tr')[1:] if row.find_all('td')])
        
        for table in soup.find_all('table'):
            for row in table.find_all('tr')[1:]:  # Skip header row
                cells = row.find_all('td')
                if len(cells) >= 2:
                    classes = row.get('class', [])
                    division_id = None
                    for cls in classes:
                        if cls.startswith('diver_'):
                            division_id = cls.replace('diver_', '')
                            break
                    if division_id:
                        try:
                            # Extract base number for sorting
                            division_name = division_lookup.get(division_id, "Unknown")
                            number_part = division_name.split()[-1]
                            if number_part.endswith('SW'):
                                sort_num = float(number_part[:-2]) + 0.5
                            else:
                                sort_num = float(number_part)
                        except (ValueError, IndexError):
                            sort_num = -1
                        all_rows.append((sort_num, row, division_name, division_id))
        
        # Sort rows by division number (highest to lowest)
        all_rows.sort(key=lambda x: x[0], reverse=True)
        
        # Process rows in sorted order
        for _, row, division_name, division_id in all_rows:
            cells = row.find_all('td')
            classes = row.get('class', [])
            
            # If we've moved to a new series, save the previous series data
            if current_series and current_series != division_name and current_series_players:
                # Save current series to CSV
                series_number = current_series.split()[-1] if current_series != "Unknown" else ""
                safe_series_name = f"Series {series_number}" if series_number else "Unknown Series"
                filename = os.path.join(data_dir, f'{safe_series_name}.csv')
                
                # Sort players by club and last name
                sorted_players = sorted(current_series_players, key=lambda x: (x['Club'], x['Last Name']))
                
                # Save to CSV
                fieldnames = ['Series', 'Division ID', 'Club', 'Location ID', 
                            'First Name', 'Last Name', 'PTI', 'Wins', 'Losses', 'Win %']
                
                with open(filename, 'w', newline='') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    for player in sorted_players:
                        writer.writerow(player)
                
                print(f"\nSaved {len(current_series_players)} players from {current_series} to {filename}")
                current_series_players = []
            
            # Get club information
            club_id = None
            club_name = "Unknown"
            for cls in classes:
                if cls.startswith('loc_'):
                    club_id = cls.replace('loc_', '')
                    club_name = location_lookup.get(club_id, "Unknown")
            
            # Get player information
            last_name = cells[1].text.strip()
            first_name = cells[0].text.strip()
            rating = cells[2].text.strip() if len(cells) > 2 else "N/A"
            
            # Get link for wins/losses
            link = row.find('a')
            if link:
                href = link.get('href', '')
                stats = get_player_stats(href, driver)
            else:
                stats = {'Wins': 0, 'Losses': 0, 'Win %': '0.0%'}
            
            # Create player info
            player_info = {
                'Series': division_name,
                'Division ID': division_id,
                'Club': club_name,
                'Location ID': club_id,
                'First Name': first_name,
                'Last Name': last_name,
                'PTI': rating,
                'Wins': stats['Wins'],
                'Losses': stats['Losses'],
                'Win %': stats['Win %']
            }
            
            # Format the win percentage
            try:
                if isinstance(player_info['Win %'], str) and player_info['Win %'].endswith('%'):
                    win_percentage = float(player_info['Win %'].rstrip('%'))
                    player_info['Win %'] = f"{win_percentage:.1f}%"
            except (ValueError, AttributeError):
                player_info['Win %'] = "0.0%"
            
            # Add to current series players
            current_series_players.append(player_info)
            current_series = division_name
            
            total_players += 1
            
            # Calculate total players in this series
            total_in_series = len([r for r in all_rows if r[2] == division_name])
            
            print(f"{len(current_series_players)} of {total_in_series} in series and {total_players} of {total_players_overall} overall - {first_name} {last_name} | {club_name} | {division_name} | {rating} | {stats['Win %']} |")
        
        # Save the last series
        if current_series and current_series_players:
            series_number = current_series.split()[-1] if current_series != "Unknown" else ""
            safe_series_name = f"Series {series_number}" if series_number else "Unknown Series"
            filename = os.path.join(data_dir, f'{safe_series_name}.csv')
            
            # Sort players by club and last name
            sorted_players = sorted(current_series_players, key=lambda x: (x['Club'], x['Last Name']))
            
            # Save to CSV
            fieldnames = ['Series', 'Division ID', 'Club', 'Location ID', 
                        'First Name', 'Last Name', 'PTI', 'Wins', 'Losses', 'Win %']
            
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for player in sorted_players:
                    writer.writerow(player)
            
            print(f"\nSaved {len(current_series_players)} players from {current_series} to {filename}")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        if driver:
            driver.quit()

def get_player_data(player_url):
    driver = webdriver.Chrome()  # Or other browser driver
    driver.get(player_url)
    # Wait for data to load
    time.sleep(2)  # Or use WebDriverWait
    
    # Extract data from rendered page
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')
    # Parse player details
    
    driver.quit()
    return player_details

if __name__ == "__main__":
    print_all_players()
