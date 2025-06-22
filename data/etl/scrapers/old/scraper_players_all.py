import csv
import json
import os
import platform
import time
from contextlib import contextmanager
from datetime import datetime
from io import StringIO

import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# Updated division lookup
division_lookup = {
    "19022": "Chicago Legends",
    "19029": "Chicago 2",
    "19030": "Chicago 3",
    "19031": "Chicago 4",
    "19032": "Chicago 5",
    "19033": "Chicago 7",
    "19034": "Chicago 8",
    "19035": "Chicago 9",
    "19036": "Chicago 10",
    "19037": "Chicago 11",
    "19038": "Chicago 12",
    "19039": "Chicago 13",
    "19040": "Chicago 14",
    "19041": "Chicago 15",
    "19042": "Chicago 16",
    "19043": "Chicago 17",
    "19044": "Chicago 18",
    "19045": "Chicago 19",
    "19046": "Chicago 20",
    "19047": "Chicago 21",
    "19048": "Chicago 22",
    "19049": "Chicago 23",
    "19050": "Chicago 24",
    "19051": "Chicago 25",
    "19052": "Chicago 26",
    "19053": "Chicago 27",
    "19054": "Chicago 28",
    "19055": "Chicago 29",
    "19056": "Chicago 30",
    "19066": "Chicago 6",
    "19068": "Chicago 25 SW",
    "19069": "Chicago 15 SW",
    "19070": "Chicago 17 SW",
    "19071": "Chicago 21 SW",
    "19072": "Chicago 11 SW",
    "19073": "Chicago 19 SW",
    "19076": "Chicago 9 SW",
    "19078": "Chicago 31",
    "19556": "Chicago 7 SW",
    "19558": "Chicago 23 SW",
    "19559": "Chicago 13 SW",
    "19560": "Chicago 32",
    "26722": "Chicago 34",
    "26829": "Chicago 99",
    "27694": "Chicago 27 SW",
    "28855": "Chicago 1",
    "28862": "Chicago 29 SW",
    "28865": "Chicago 33",
    "28867": "Chicago 35",
    "28868": "Chicago 36",
    "28869": "Chicago 37",
    "28870": "Chicago 38",
    "28871": "Chicago 39",
}

# Add the location lookup dictionary
location_lookup = {
    "16161": "Wilmette PD",
    "16162": "Sunset Ridge",
    "16163": "Winnetka",
    "16164": "Exmoor",
    "16165": "Hinsdale PC",
    "16166": "Onwentsia",
    "16167": "Salt Creek",
    "16168": "Lakeshore S&amp;F",
    "16169": "Glen View",
    "16170": "Prairie Club",
    "16171": "Lake Forest",
    "16172": "Evanston ",
    "16173": "Midt-Bannockburn",
    "16174": "Briarwood",
    "16175": "Birchwood",
    "16176": "Hinsdale GC",
    "16177": "Butterfield",
    "16178": "Chicago Highlands",
    "16179": "Glen Ellyn",
    "16180": "Skokie",
    "16181": "Winter Club",
    "16182": "Westmoreland",
    "16183": "Valley Lo",
    "16184": "Tennaqua",
    "16185": "South Barrington",
    "16186": "Saddle &amp; Cycle",
    "16187": "Ruth Lake",
    "16188": "Northmoor",
    "16189": "North Shore",
    "16190": "Midtown - Chicago",
    "16191": "Michigan Shores",
    "16192": "Lake Shore CC",
    "16193": "Knollwood",
    "16194": "Indian Hill",
    "16195": "Glenbrook RC",
    "16196": "Hawthorn Woods",
    "16197": "Lake Bluff",
    "16198": "Barrington Hills CC",
    "16199": "River Forest PD",
    "16200": "Edgewood Valley",
    "16201": "Park Ridge CC",
    "16202": "Medinah",
    "16203": "LaGrange CC",
    "16204": "Dunham Woods",
    "16432": "BYE",
    "17241": "Lifesport-Lshore",
    "17242": "Biltmore CC",
    "18332": "Bryn Mawr",
    "18333": "Glen Oak ",
    "18334": "Inverness ",
    "18335": "White Eagle",
    "18364": "Legends ",
    "19205": "River Forest CC",
    "19312": "Oak Park CC",
    "22561": "Royal Melbourne",
}


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
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920x1080")
        options.add_argument("--disable-features=NetworkService")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--disable-web-security")
        options.add_argument("--disable-features=IsolateOrigins,site-per-process")
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
                print(
                    f"Error creating Chrome driver (attempt {attempt + 1}/{self.max_retries}): {str(e)}"
                )
                if attempt < self.max_retries - 1:
                    print("Retrying...")
                    time.sleep(5)
                else:
                    raise Exception(
                        "Failed to create Chrome driver after maximum retries"
                    )

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


def get_player_stats(player_url, driver, max_retries=3, retry_delay=5):
    """
    Get player statistics using the provided driver instance.

    Args:
        player_url (str): URL to the player's stats page
        driver (webdriver): Chrome WebDriver instance
        max_retries (int): Maximum number of retry attempts
        retry_delay (int): Delay in seconds between retries

    Returns:
        dict: Player statistics including wins, losses, and win percentage
    """
    for attempt in range(max_retries):
        try:
            base_url = "https://aptachicago.tenniscores.com"
            full_url = (
                f"{base_url}{player_url}"
                if not player_url.startswith("http")
                else player_url
            )

            # Verify driver health before making request
            try:
                driver.current_url
            except Exception:
                raise Exception("Driver session is invalid")

            driver.get(full_url)
            time.sleep(retry_delay)  # Increased delay between requests

            wins = 0
            losses = 0
            content = driver.find_element(By.TAG_NAME, "body").text
            matches = content.split("\n")

            for line in matches:
                if line.strip() == "W":
                    wins += 1
                elif line.strip() == "L":
                    losses += 1

            return {
                "Wins": wins,
                "Losses": losses,
                "Win %": (
                    f"{(wins/(wins+losses)*100):.1f}%" if wins + losses > 0 else "0.0%"
                ),
            }

        except Exception as e:
            print(
                f"Error getting player stats (attempt {attempt + 1}/{max_retries}): {str(e)}"
            )
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                # If session is invalid, try to recreate the driver
                if "invalid session id" in str(e).lower():
                    try:
                        driver.quit()
                    except:
                        pass
                    driver = ChromeManager().__enter__()
            else:
                print("Max retries reached, returning default stats")
                return {"Wins": 0, "Losses": 0, "Win %": "0.0%"}


def load_active_series():
    """
    Load the list of active series from active_series.txt.
    The file should be located in the same directory as this script.
    If the file doesn't exist, return an empty set.

    Returns:
        set: Set of active series names
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    active_series_path = os.path.join(script_dir, "active_series.txt")

    try:
        with open(active_series_path, "r") as f:
            return {line.strip() for line in f if line.strip()}
    except FileNotFoundError:
        print(
            f"active_series.txt not found at {active_series_path}. Processing all series."
        )
        return set()


def print_all_players():
    """Main function to scrape and save player data."""
    try:
        # Load active series
        active_series = load_active_series()
        if active_series:
            print(
                f"Found {len(active_series)} active series to process: {', '.join(sorted(active_series))}"
            )
        else:
            print("No active series file found - will process all series")

        # Use context manager to ensure Chrome driver is properly closed
        with ChromeManager() as driver:
            url = "https://aptachicago.tenniscores.com/?mod=nndz-SkhmOW1PQ3V4Zz09"

            # Create directory structure if it doesn't exist
            data_dir = os.path.join("data", "players")
            os.makedirs(data_dir, exist_ok=True)

            # Load the page
            driver.get(url)
            time.sleep(3)

            # Get the page source after JavaScript has run
            soup = BeautifulSoup(driver.page_source, "html.parser")

            # Initialize tracking variables
            all_players = []
            total_players = 0

            # First pass: Collect all rows and sort by division
            all_rows = []
            current_series = None
            current_series_players = []

            # Calculate total players that match series criteria
            total_players_to_process = 0
            for table in soup.find_all("table"):
                for row in table.find_all("tr")[1:]:  # Skip header row
                    cells = row.find_all("td")
                    if len(cells) >= 2:
                        classes = row.get("class", [])
                        division_id = None
                        for cls in classes:
                            if cls.startswith("diver_"):
                                division_id = cls.replace("diver_", "")
                                break
                        if division_id:
                            division_name = division_lookup.get(division_id, "Unknown")
                            if not active_series or division_name in active_series:
                                total_players_to_process += 1

            # Now collect rows for processing
            for table in soup.find_all("table"):
                for row in table.find_all("tr")[1:]:  # Skip header row
                    cells = row.find_all("td")
                    if len(cells) >= 2:
                        classes = row.get("class", [])
                        division_id = None
                        for cls in classes:
                            if cls.startswith("diver_"):
                                division_id = cls.replace("diver_", "")
                                break
                        if division_id:
                            try:
                                # Extract base number for sorting
                                division_name = division_lookup.get(
                                    division_id, "Unknown"
                                )

                                # Skip if not in active series
                                if active_series and division_name not in active_series:
                                    continue

                                number_part = division_name.split()[-1]
                                if number_part.endswith("SW"):
                                    sort_num = float(number_part[:-2]) + 0.5
                                else:
                                    sort_num = float(number_part)
                            except (ValueError, IndexError):
                                sort_num = -1
                            all_rows.append((sort_num, row, division_name, division_id))

            # Sort rows by division number (highest to lowest)
            all_rows.sort(key=lambda x: x[0], reverse=True)

            # Process rows in sorted order
            processed_series = set()
            total_players = 0

            for _, row, division_name, division_id in all_rows:
                cells = row.find_all("td")

                # Get club information
                club_id = None
                club_name = "Unknown"
                for cls in row.get("class", []):
                    if cls.startswith("loc_"):
                        club_id = cls.replace("loc_", "")
                        club_name = location_lookup.get(club_id, "Unknown")

                # Get player information
                last_name = cells[1].text.strip()
                first_name = cells[0].text.strip()
                rating = cells[2].text.strip() if len(cells) > 2 else "N/A"

                # Get link for wins/losses
                link = row.find("a")
                if link:
                    href = link.get("href", "")
                    stats = get_player_stats(href, driver)
                else:
                    stats = {"Wins": 0, "Losses": 0, "Win %": "0.0%"}

                # Create player info
                player_info = {
                    "Series": division_name,
                    "Division ID": division_id,
                    "Club": club_name,
                    "Location ID": club_id,
                    "First Name": first_name,
                    "Last Name": last_name,
                    "PTI": rating,
                    "Wins": str(stats["Wins"]),
                    "Losses": str(stats["Losses"]),
                    "Win %": stats["Win %"],
                }

                # Add to all players list
                all_players.append(player_info)
                processed_series.add(division_name)

                # Calculate progress
                total_in_series = len([r for r in all_rows if r[2] == division_name])
                total_players += 1
                series_players = len(
                    [p for p in all_players if p["Series"] == division_name]
                )

                # Print progress in the requested format
                print(
                    f"{series_players} of {total_in_series} in series and {total_players} of {total_players_to_process} players - {first_name} {last_name} | {club_name} | {division_name} | {rating} | {stats['Win %']} |"
                )

            # Save all players to JSON
            filename = os.path.join(data_dir, "players.json")
            with open(filename, "w", encoding="utf-8") as jsonfile:
                json.dump(all_players, jsonfile, indent=2)

            print(f"\nSaved {len(all_players)} players to {filename}")
            print(f"Processed series: {', '.join(sorted(processed_series))}")

    except Exception as e:
        print(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    print_all_players()
