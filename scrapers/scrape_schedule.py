import requests
from bs4 import BeautifulSoup
import json
import datetime
import os

def scrape_tennis_schedule():
    # URL of the tennis schedule website
    url = "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4ya2l3SlJNTGNNdz09&print&did=nndz-WnkrNXhiWT0%3D"
    
    try:
        print("1. Sending request to URL...")
        # Send GET request to the URL
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        print(f"2. Response status code: {response.status_code}")
        
        # Parse the HTML content
        print("3. Parsing HTML content...")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all schedule entries
        print("4. Looking for schedule entries...")
        schedule_entries = soup.find_all('div', class_='row_cont')
        print(f"5. Found {len(schedule_entries)} potential entries")
        
        schedule_data = []
        
        # Process each schedule entry
        print("\n6. Processing entries...")
        for i, entry in enumerate(schedule_entries, 1):
            # Get all the fields for this entry
            date = entry.find('div', class_='week_date')
            time = entry.find('div', class_='week_time')
            home = entry.find('div', class_='week_home')
            away = entry.find('div', class_='week_away')
            location = entry.find('div', class_='week_loc')
            
            if all([date, time, home, away, location]):  # Only process complete entries
                schedule_item = {
                    'date': date.text.strip(),
                    'time': time.text.strip(),
                    'home_team': home.text.strip(),
                    'away_team': away.text.strip(),
                    'location': location.text.strip()
                }
                print(f"   Entry {i} data: {schedule_item}")
                schedule_data.append(schedule_item)
        
        print(f"\n7. Total valid entries found: {len(schedule_data)}")
        
        # Create data directory if it doesn't exist
        if not os.path.exists('data'):
            os.makedirs('data')
            print("8. Created data directory")
        
        # Create output filename with current date
        current_date = datetime.datetime.now().strftime("%Y%m%d")
        output_filename = f"data/tennis_schedule_{current_date}.json"
        
        # Save to JSON file
        print(f"\n9. Saving data to {output_filename}")
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(schedule_data, f, indent=4, ensure_ascii=False)
            
        print(f"10. Schedule successfully scraped and saved to {output_filename}")
        
    except requests.RequestException as e:
        print(f"Error fetching the website: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error details: {str(e)}")

if __name__ == "__main__":
    scrape_tennis_schedule()
