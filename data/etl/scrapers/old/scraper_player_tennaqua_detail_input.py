print("[DEBUG] player_scrape_tennaqua_deep.py script started")
import csv
import os
import tempfile
import time
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


def get_player_stats(player_url, driver):
    try:
        base_url = "https://aptachicago.tenniscores.com"
        full_url = (
            f"{base_url}{player_url}"
            if not player_url.startswith("http")
            else player_url
        )
        print(f"[DEBUG] Loading player page: {full_url}")
        driver.get(full_url)
        time.sleep(2)

        wins = 0
        losses = 0
        wl_dates = []  # List of tuples: (W/L, date)
        match_details = []  # List of dicts: {date, end_pti, series}

        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Extract match info from rbox_top divs
        for rbox in soup.find_all("div", class_="rbox_top"):
            # Date
            date_div = rbox.find("div", class_="rbox_inner")
            match_date = None
            if date_div:
                date_text = date_div.get_text(strip=True)
                # Only take the date part (before space/time)
                match_date = date_text.split()[0] if date_text else None
            # Series
            series_div = rbox.find_all("div", class_="rbox_inner")
            match_series = None
            if len(series_div) > 1:
                # The second rbox_inner contains the series info
                match_series = series_div[1].get_text(strip=True)
                # Optionally, just take the part before ' - ' if needed
                if " - " in match_series:
                    match_series = match_series.split(" - ")[0]
            # End PTI
            end_pti = None
            for pti_div in rbox.find_all("div", class_="rbox3top"):
                if "End" in pti_div.get_text():
                    span = pti_div.find("span", class_="demi")
                    if span:
                        end_pti = span.get_text(strip=True)
            if match_date and end_pti and match_series:
                match_details.append(
                    {"date": match_date, "end_pti": end_pti, "series": match_series}
                )

        # Existing W/L logic
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if not cells or len(cells) < 2:
                continue
            wl = None
            date = None
            for cell in cells:
                text = cell.get_text(strip=True)
                if text in ("W", "L"):
                    wl = text
                if any(char.isdigit() for char in text) and (
                    "/" in text or "-" in text
                ):
                    date = text
            if wl and date:
                wl_dates.append((wl, date))
                if wl == "W":
                    wins += 1
                elif wl == "L":
                    losses += 1

        if not wl_dates:
            content = driver.find_element(By.TAG_NAME, "body").text
            matches = content.split("\n")
            for line in matches:
                if line.strip() == "W":
                    wins += 1
                elif line.strip() == "L":
                    losses += 1

        print(f"[DEBUG] Finished scraping player page: {full_url}")
        return {
            "Wins": wins,
            "Losses": losses,
            "Win %": (
                f"{(wins/(wins+losses)*100):.1f}%" if wins + losses > 0 else "0.0%"
            ),
            "wl_dates": wl_dates,
            "match_details": match_details,
        }

    except Exception as e:
        print(f"Error in get_player_stats: {e}")
        return {
            "Wins": 0,
            "Losses": 0,
            "Win %": "0.0%",
            "wl_dates": [],
            "match_details": [],
        }


def print_all_players():
    driver = None
    try:
        # Set up Chrome options
        chrome_options = Options()
        user_data_dir = tempfile.mkdtemp()
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")

        # Initialize Chrome driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        url = "https://aptachicago.tenniscores.com/?mod=nndz-SkhmOW1PQ3V4Zz09"

        # Create Data directory if it doesn't exist
        data_dir = "Data"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        # Load the page
        driver.get(url)
        time.sleep(3)

        # Get the page source after JavaScript has run
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Initialize tracking variables
        series_players = {}

        # First pass: identify all Tennaqua players and their series
        for table in soup.find_all("table"):
            for row in table.find_all("tr")[1:]:  # Skip header row
                cells = row.find_all("td")
                if len(cells) >= 2:
                    classes = row.get("class", [])

                    # Check if player is from Tennaqua
                    is_tennaqua = False
                    club_id = None
                    division_id = None

                    for cls in classes:
                        if cls.startswith("loc_"):
                            club_id = cls.replace("loc_", "")
                            if location_lookup.get(club_id, "") == "Tennaqua":
                                is_tennaqua = True

                    if is_tennaqua:
                        # Get the series
                        for cls in classes:
                            if cls.startswith("diver_"):
                                division_id = cls.replace("diver_", "")
                                series = division_lookup.get(division_id, "Unknown")
                                if series not in series_players:
                                    series_players[series] = []
                                series_players[series].append(row)

        # Display total number of series and list them
        print(f"\nFound Tennaqua players in {len(series_players)} series:")
        for series in sorted(series_players.keys()):
            print(f"- {series} ({len(series_players[series])} players)")

        # Get total number of Tennaqua players
        total_players = sum(len(players) for players in series_players.values())
        overall_processed = 0

        # Process all series
        processed_count = 0
        for series, players in series_players.items():
            current_series_players = []
            series_count = len(players)
            series_processed = 0
            for row in players:
                if processed_count >= 3:
                    print("Ended Test")
                    return
                cells = row.find_all("td")
                if len(cells) >= 2:
                    last_name = cells[
                        1
                    ].text.strip()  # This cell contains the last name
                    first_name = cells[
                        0
                    ].text.strip()  # This cell contains the first name
                    rating = cells[2].text.strip() if len(cells) > 2 else "N/A"
                    series_processed += 1
                    overall_processed += 1
                    link = row.find("a")
                    if link:
                        href = link.get("href", "")
                        stats = get_player_stats(href, driver)
                    else:
                        stats = {
                            "Wins": 0,
                            "Losses": 0,
                            "Win %": "0.0%",
                            "wl_dates": [],
                            "match_details": [],
                        }
                    # Print player info block once, then each match detail
                    print(
                        f"{first_name} {last_name}\n{series}\nRating: {rating}\nWins: {stats['Wins']}, Losses: {stats['Losses']}\n{series_processed} of {series_count} in Series | {overall_processed} of {total_players} overall"
                    )
                    if stats.get("match_details"):
                        for m in stats["match_details"]:
                            print(
                                f"{m['date']}\nEnd PTI: {m['end_pti']}\nSeries: {m['series']}\n"
                            )
                    print()  # Extra newline after each player
                    player_info = {
                        "Series": series,
                        "Division ID": division_id,
                        "Club": "Tennaqua",
                        "Location ID": club_id,
                        "First Name": first_name,
                        "Last Name": last_name,
                        "PTI": rating,
                        "Wins": stats["Wins"],
                        "Losses": stats["Losses"],
                        "Win %": stats["Win %"],
                    }
                    try:
                        if isinstance(player_info["Win %"], str) and player_info[
                            "Win %"
                        ].endswith("%"):
                            win_percentage = float(player_info["Win %"].rstrip("%"))
                            player_info["Win %"] = f"{win_percentage:.1f}%"
                    except (ValueError, AttributeError):
                        player_info["Win %"] = "0.0%"
                    current_series_players.append(player_info)
                    processed_count += 1

            # Save series data
            if current_series_players:
                sorted_players = sorted(
                    current_series_players, key=lambda x: x["Last Name"]
                )
                filename = os.path.join(data_dir, f"tennaqua_players_{series}.csv")

                fieldnames = [
                    "Series",
                    "Division ID",
                    "Club",
                    "Location ID",
                    "First Name",
                    "Last Name",
                    "PTI",
                    "Wins",
                    "Losses",
                    "Win %",
                ]
                with open(filename, "w", newline="") as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    for player in sorted_players:
                        writer.writerow(
                            {
                                "Series": player["Series"],
                                "Division ID": player["Division ID"],
                                "Club": player["Club"],
                                "Location ID": player["Location ID"],
                                "First Name": player["First Name"],
                                "Last Name": player["Last Name"],
                                "PTI": player["PTI"],
                                "Wins": player["Wins"],
                                "Losses": player["Losses"],
                                "Win %": player["Win %"],
                            }
                        )

                print(f"Created: {filename}")

    except Exception as e:
        print(f"Error: {str(e)}")
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
    soup = BeautifulSoup(page_source, "html.parser")
    # Parse player details

    driver.quit()
    return player_details


if __name__ == "__main__":
    os.system("pkill -f 'chromedriver'")

    # 1. Prompt for player name
    player_name = input("Enter player name (e.g., Phil Davis): ").strip().lower()

    chrome_options = Options()
    user_data_dir = tempfile.mkdtemp()
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")

    print("Before Service/Driver init")
    service = Service(ChromeDriverManager().install())
    print("Service created")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    print("Driver created")

    # 2. Load the main page
    driver.get("https://aptachicago.tenniscores.com/?mod=nndz-SkhmOW1PQ3V4Zz09")
    soup = BeautifulSoup(driver.page_source, "html.parser")

    # 3. Search for the player in the table
    found = False
    for table in soup.find_all("table"):
        for row in table.find_all("tr")[1:]:  # Skip header
            cells = row.find_all("td")
            if len(cells) >= 2:
                first_name = cells[0].text.strip()
                last_name = cells[1].text.strip()
                full_name = f"{first_name} {last_name}".lower()
                if player_name == full_name:
                    # Found the player, get the link
                    link = row.find("a")
                    if link:
                        href = link.get("href", "")
                        # 4. Go to the player's page and scrape
                        driver.get("https://aptachicago.tenniscores.com" + href)
                        player_soup = BeautifulSoup(driver.page_source, "html.parser")
                        # Example: print the page title or scrape as needed
                        print(f"\nFound player: {first_name} {last_name}")
                        # --- Insert your scraping/printing logic here ---
                        # For demo, just print the page title:
                        print(driver.title)
                        # --- End custom logic ---
                        found = True
                    break
    if not found:
        print("Player not found.")

    driver.quit()
