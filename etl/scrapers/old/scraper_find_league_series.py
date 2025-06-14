print("[DEBUG] league_names_scraper.py script started")
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import csv
import os
from datetime import datetime
import time
import json

class ChromeManager:
    """Context manager for handling Chrome WebDriver sessions."""
    
    def __init__(self, max_retries=3):
        """Initialize the Chrome WebDriver manager.
        
        Args:
            max_retries (int): Maximum number of retries for creating a new driver
        """
        self.driver = None
        self.max_retries = max_retries
        
    def create_driver(self):
        """Create and configure a new Chrome WebDriver instance."""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920x1080')
        options.add_argument('--disable-features=NetworkService')
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=IsolateOrigins,site-per-process')
        return webdriver.Chrome(options=options)

    def __enter__(self):
        """Create and return a Chrome WebDriver instance with retries."""
        for attempt in range(self.max_retries):
            try:
                if self.driver is not None:
                    try:
                        self.driver.quit()
                    except:
                        pass
                self.driver = self.create_driver()
                return self.driver
            except Exception as e:
                print(f"Error creating Chrome driver (attempt {attempt + 1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    print("Retrying...")
                    time.sleep(5)
                else:
                    raise Exception("Failed to create Chrome driver after maximum retries")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up the Chrome WebDriver instance."""
        self.quit()

    def quit(self):
        """Safely quit the Chrome WebDriver instance."""
        if self.driver is not None:
            try:
                self.driver.quit()
            except Exception as e:
                print(f"Error closing Chrome driver: {str(e)}")
            finally:
                self.driver = None

def scrape_league_names(max_retries=3, retry_delay=2):
    """Main function to scrape and save league names data."""
    try:
        # Use context manager to ensure Chrome driver is properly closed
        with ChromeManager() as driver:
            url = 'https://aptachicago.tenniscores.com/'
            
            # Create directory structure if it doesn't exist
            data_dir = os.path.join('data', 'leagues')
            os.makedirs(data_dir, exist_ok=True)
            
            print(f"Navigating to URL: {url}")
            driver.get(url)
            time.sleep(retry_delay)
            
            # Parse the page with BeautifulSoup
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Find all div_list_option elements
            series_elements = soup.find_all('div', class_='div_list_option')
            
            # Extract and store series data
            series_data = []
            for element in series_elements:
                try:
                    # Get the data-id attribute
                    series_id = element.get('data-id', '')
                    
                    # Get the series number from the link text
                    series_link = element.find('a')
                    if series_link and series_link.text:
                        series_number = series_link.text.strip()
                        series_url = series_link.get('href', '')
                        
                        series_info = {
                            'series_number': series_number,
                            'series_id': series_id,
                            'url': f"https://aptachicago.tenniscores.com{series_url}" if series_url else ''
                        }
                        series_data.append(series_info)
                        print(f"Found series: Chicago {series_number} (ID: {series_id})")
                        print(f"         URL: {series_info['url']}")
                        print("-" * 80)  # Add a separator line for better readability
                except Exception as e:
                    print(f"Error extracting series data: {str(e)}")
            
            if not series_data:
                print("No series found!")
                return
            
            # Sort series data by series number
            def sort_key(item):
                # Extract numeric part and 'SW' suffix if present
                num = item['series_number'].split()[0]
                try:
                    return (float(num), 'SW' not in item['series_number'])
                except ValueError:
                    return (float('inf'), True)
            
            series_data.sort(key=sort_key)
            
            # Save data in both JSON and CSV formats
            current_date = datetime.now().strftime("%Y%m%d")
            
            # Save as JSON
            json_filename = os.path.join(data_dir, f"league_series_{current_date}.json")
            with open(json_filename, 'w', encoding='utf-8') as jsonfile:
                json.dump(series_data, jsonfile, indent=2)
            
            # Save as CSV
            csv_filename = os.path.join(data_dir, f"league_series_{current_date}.csv")
            with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow(['Series Number', 'Series ID', 'URL'])  # Header
                for series in series_data:
                    csvwriter.writerow([
                        series['series_number'],
                        series['series_id'],
                        series['url']
                    ])
            
            print(f"\nScraping completed successfully!")
            print(f"Found {len(series_data)} series")
            print(f"Data has been saved to:")
            print(f"- JSON: {json_filename}")
            print(f"- CSV: {csv_filename}")

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    scrape_league_names() 