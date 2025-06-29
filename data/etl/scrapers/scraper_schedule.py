import json
import os
import re
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup


# Dynamic League Configuration - User Input Based
def get_league_config(league_subdomain=None):
    """Get dynamic league configuration based on user input"""
    if not league_subdomain:
        raise ValueError("League subdomain must be provided")

    base_url = build_base_url(league_subdomain)

    return {
        "league_id": league_subdomain.upper(),
        "subdomain": league_subdomain,
        "base_url": base_url,
        "main_page": base_url,
        "player_page_mod": "nndz-SkhmOW1PQ3V4Zz09",
        "team_page_mod": "nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D",
    }


def build_base_url(subdomain):
    """
    Build the base URL for the league using the subdomain.

    Args:
        subdomain (str): The subdomain for the league (e.g., 'aptachicago', 'nstf')

    Returns:
        str: The complete base URL (e.g., 'https://aptachicago.tenniscores.com')
    """
    return f"https://{subdomain}.tenniscores.com"


def extract_series_name_from_team(team_name):
    """
    Extract series name from team name, auto-detecting APTA vs NSTF vs CNSWPL format.

    Args:
        team_name (str): Team name in various formats

    Returns:
        str: Standardized series name or None if not detected

    Examples:
        APTA: "Birchwood - 6" -> "Chicago 6"
        NSTF: "Birchwood S1" -> "Series 1"
        NSTF: "Wilmette Sunday A" -> "Series A"
        CNSWPL: "Birchwood 1" -> "Series 1"
        CNSWPL: "Hinsdale PC 1a" -> "Series 1a"
    """
    if not team_name:
        return None

    team_name = team_name.strip()

    # APTA Chicago format: "Club - Number"
    if " - " in team_name:
        parts = team_name.split(" - ")
        if len(parts) > 1:
            series_num = parts[1].strip()
            return f"Chicago {series_num}"

    # NSTF format: "Club SNumber" or "Club SNumberLetter" (e.g., S1, S2A, S2B)
    elif re.search(r"S(\d+[A-Z]*)", team_name):
        match = re.search(r"S(\d+[A-Z]*)", team_name)
        if match:
            series_identifier = match.group(1)
            return f"Series {series_identifier}"

    # NSTF Sunday formats
    elif "Sunday A" in team_name:
        return "Series A"
    elif "Sunday B" in team_name:
        return "Series B"

    # CNSWPL format: "Club Number" or "Club NumberLetter" (e.g., "Birchwood 1", "Hinsdale PC 1a")
    elif re.search(r"\s(\d+[a-zA-Z]?)$", team_name):
        match = re.search(r"\s(\d+[a-zA-Z]?)$", team_name)
        if match:
            series_identifier = match.group(1)
            return f"Series {series_identifier}"

    # Direct series name (already formatted)
    elif team_name.startswith("Series ") or team_name.startswith("Chicago "):
        return team_name

    return None


def build_league_data_dir(league_id):
    """
    Build the dynamic data directory path based on the league ID.

    Args:
        league_id (str): The league identifier

    Returns:
        str: The data directory path (e.g., 'data/leagues/APTACHICAGO')
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))  # data/etl/scrapers/
    etl_dir = os.path.dirname(script_dir)  # data/etl/
    project_root = os.path.dirname(
        os.path.dirname(etl_dir)
    )  # rally/ (up one more level)

    league_data_dir = os.path.join(project_root, "data", "leagues", league_id)
    os.makedirs(league_data_dir, exist_ok=True)

    return league_data_dir


# Removed file-based configuration functions - now using user input
# Removed active_series functionality - now processes all discovered series


def scrape_tennis_schedule(league_subdomain):
    """
    Main function to scrape tennis schedules using dynamic discovery.

    Args:
        league_subdomain (str): League subdomain (e.g., 'aptachicago', 'nstf')
    """
    # Record start time
    start_time = datetime.now()
    print(f"🕐 Session Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Track timing milestones
    discovery_start_time = None
    scraping_start_time = None

    try:
        # Load league configuration from user input
        config = get_league_config(league_subdomain)
        league_id = config["league_id"]
        base_url = config["base_url"]

        print(
            f"🌟 Processing ALL discovered series from {config['subdomain']} dynamically"
        )
        print("No filtering - comprehensive discovery and processing of all schedules")

        # Create dynamic data directory based on league
        data_dir = build_league_data_dir(league_id)

        print(f"🚀 Starting {config['subdomain'].upper()} Schedule Scraper")
        print(f"📊 Target: All Discovered Series")
        print("=" * 60)

        # Discovery phase
        discovery_start_time = datetime.now()
        print(f"🔍 Discovery Phase Start: {discovery_start_time.strftime('%H:%M:%S')}")
        print(f"📄 Accessing main page: {base_url}")

        # Send GET request to the base URL
        response = requests.get(base_url)
        response.raise_for_status()
        print(f"✅ Main page loaded successfully (Status: {response.status_code})")

        # Parse the HTML content
        soup = BeautifulSoup(response.text, "html.parser")

        # Find all series elements
        series_elements = soup.find_all("div", class_="div_list_option")
        print(f"🏆 Found {len(series_elements)} total series on main page")

        discovery_end_time = datetime.now()
        discovery_duration = discovery_end_time - discovery_start_time
        print(
            f"✅ Discovery Phase Complete: {discovery_duration.total_seconds():.1f} seconds"
        )

        # Scraping phase
        scraping_start_time = datetime.now()
        print(f"\n⚡ Scraping Phase Start: {scraping_start_time.strftime('%H:%M:%S')}")

        all_schedule_data = []
        processed_series_count = 0
        skipped_series_count = 0

        # Process each series
        for series_idx, element in enumerate(series_elements, 1):
            series_start_time = datetime.now()
            progress_percent = (series_idx / len(series_elements)) * 100
            elapsed = series_start_time - start_time
            print(
                f"\n=== Series {series_idx}/{len(series_elements)} ({progress_percent:.1f}%) | Elapsed: {elapsed} ==="
            )

            try:
                series_link = element.find("a")
                if series_link and series_link.text:
                    series_number = series_link.text.strip()

                    # Format the series number to auto-detect APTA vs NSTF format
                    if series_number.isdigit():
                        formatted_series = f"Chicago {series_number}"
                    elif series_number.startswith("Series "):
                        # Series name already has "Series" prefix, use as-is
                        formatted_series = series_number
                    elif "SW" in series_number:
                        # Handle SW series: "23 SW" -> "Chicago 23 SW"
                        formatted_series = f"Chicago {series_number}"
                    else:
                        # Handle non-numeric series (like "2B", "3A", etc.)
                        formatted_series = f"Series {series_number}"

                    series_url = series_link.get("href", "")
                    full_url = f"{base_url}/{series_url}" if series_url else ""

                    if not full_url:
                        print(
                            f"⚠️  Skipping series {formatted_series} - No valid URL found"
                        )
                        skipped_series_count += 1
                        continue

                    print(f"🏆 Processing: {formatted_series}")
                    print(f"   📄 Series URL: {full_url}")

                    # Get the series page
                    print("   🔍 Accessing series page...")
                    series_response = requests.get(full_url)
                    series_soup = BeautifulSoup(series_response.text, "html.parser")

                    # Find the Schedule link
                    print("   📅 Looking for schedule link...")
                    schedule_link = series_soup.find("a", text="Schedule")
                    if not schedule_link:
                        print(
                            f"   ⚠️  No schedule link found for series {formatted_series}"
                        )
                        skipped_series_count += 1
                        continue

                    schedule_url = f"{base_url}/{schedule_link['href']}"
                    print(f"   📅 Schedule URL: {schedule_url}")

                    # Get the schedule page
                    print("   📊 Accessing schedule page...")
                    schedule_response = requests.get(schedule_url)
                    schedule_soup = BeautifulSoup(schedule_response.text, "html.parser")

                    # Find all schedule entries
                    schedule_entries = schedule_soup.find_all("div", class_="row_cont")
                    print(
                        f"   📋 Found {len(schedule_entries)} potential schedule entries"
                    )

                    entries_added = 0
                    # Process each schedule entry
                    for entry in schedule_entries:
                        # Get all the fields for this entry
                        date = entry.find("div", class_="week_date")
                        time = entry.find("div", class_="week_time")
                        home = entry.find("div", class_="week_home")
                        away = entry.find("div", class_="week_away")
                        location = entry.find("div", class_="week_loc")

                        # Some sites use different class names for location field
                        if not location:
                            location = entry.find("div", class_="week_print")
                        if not location:
                            location = entry.find("div", class_="week_location")

                        if all([date, time, home, away]):  # Only require core fields
                            # Fix team name formatting - don't add series number if already present
                            raw_home = home.text.strip()
                            raw_away = away.text.strip()

                            # Skip schedule entries involving BYE teams - they are placeholders with no actual players
                            if "BYE" in raw_home.upper() or "BYE" in raw_away.upper():
                                print(
                                    f"       Skipping BYE schedule entry: {raw_home} vs {raw_away}"
                                )
                                continue

                            # Check if team name already ends with the series number
                            if raw_home.endswith(f" - {series_number}"):
                                formatted_home = raw_home
                            else:
                                formatted_home = f"{raw_home} - {series_number}"

                            if raw_away.endswith(f" - {series_number}"):
                                formatted_away = raw_away
                            else:
                                formatted_away = f"{raw_away} - {series_number}"

                            # Extract location text, handling different formats
                            location_text = ""
                            if location:
                                location_text = location.text.strip()
                                # If location contains "Details" or similar, it's not a real location
                                if location_text.lower() in ["details", "print", ""]:
                                    location_text = "TBD"
                            else:
                                location_text = "TBD"

                            schedule_item = {
                                "date": date.text.strip(),
                                "time": time.text.strip(),
                                "home_team": formatted_home,
                                "away_team": formatted_away,
                                "location": location_text,
                                "series": formatted_series,
                                "League": league_id,
                            }
                            all_schedule_data.append(schedule_item)
                            entries_added += 1

                    series_end_time = datetime.now()
                    series_duration = series_end_time - series_start_time

                    print(
                        f"   ✅ Added {entries_added} schedule entries for {formatted_series}"
                    )
                    processed_series_count += 1

                    # Progress update with timing
                    remaining_series = len(series_elements) - series_idx
                    avg_time_per_series = (
                        (series_start_time - scraping_start_time).total_seconds()
                        / series_idx
                        if scraping_start_time and series_idx > 0
                        else 0
                    )
                    estimated_remaining = (
                        remaining_series * avg_time_per_series
                        if avg_time_per_series > 0
                        else 0
                    )
                    eta = (
                        series_end_time + timedelta(seconds=estimated_remaining)
                        if estimated_remaining > 0
                        else None
                    )

                    print(
                        f"✅ Series completed in {series_duration.total_seconds():.1f}s | Progress: {series_idx}/{len(series_elements)} series"
                    )
                    if eta:
                        print(
                            f"   ⏰ ETA: {eta.strftime('%H:%M:%S')} (est. {estimated_remaining/60:.1f} min remaining)"
                        )

            except Exception as e:
                print(f"   ❌ Error processing series: {str(e)}")
                skipped_series_count += 1
                continue

        # Save schedule data
        output_filename = os.path.join(data_dir, "schedules.json")
        with open(output_filename, "w", encoding="utf-8") as f:
            json.dump(all_schedule_data, f, indent=4, ensure_ascii=False)

        # Calculate end time and duration
        end_time = datetime.now()
        total_duration = end_time - start_time
        scraping_end_time = end_time
        scraping_duration = (
            scraping_end_time - scraping_start_time
            if scraping_start_time
            else total_duration
        )

        print(f"\n🎉 SCRAPING COMPLETE!")
        print("=" * 70)

        # Detailed timing summary
        print(f"📅 SESSION SUMMARY - {end_time.strftime('%Y-%m-%d')}")
        print(f"🕐 Session Start:     {start_time.strftime('%H:%M:%S')}")
        if discovery_start_time:
            print(
                f"🔍 Discovery Start:   {discovery_start_time.strftime('%H:%M:%S')} (Duration: {discovery_duration.total_seconds():.1f}s)"
            )
        if scraping_start_time:
            print(
                f"⚡ Scraping Start:    {scraping_start_time.strftime('%H:%M:%S')} (Duration: {scraping_duration.total_seconds():.1f}s)"
            )
        print(f"🏁 Session End:       {end_time.strftime('%H:%M:%S')}")
        print(f"⏱️  TOTAL DURATION:    {total_duration}")
        print()

        # Performance metrics
        total_seconds = total_duration.total_seconds()
        series_per_minute = (
            (processed_series_count / total_seconds * 60) if total_seconds > 0 else 0
        )
        entries_per_minute = (
            (len(all_schedule_data) / total_seconds * 60) if total_seconds > 0 else 0
        )

        print(f"📊 PERFORMANCE METRICS")
        print(f"📈 Total series found: {len(series_elements)}")
        print(f"🏆 Series processed successfully: {processed_series_count}")
        print(f"⚠️  Series skipped/failed: {skipped_series_count}")
        print(f"📅 Total schedule entries: {len(all_schedule_data)}")
        print(f"📈 Series per minute: {series_per_minute:.1f}")
        print(f"📅 Entries per minute: {entries_per_minute:.1f}")
        print(
            f"⚡ Average time per series: {total_seconds/processed_series_count:.1f}s"
            if processed_series_count > 0
            else "⚡ Average time per series: N/A"
        )
        print()

        print(f"💾 Data saved to: {output_filename}")

        # Print summary by series
        print(f"\n📈 SERIES BREAKDOWN:")
        series_counts = {}
        for entry in all_schedule_data:
            series = entry["series"]
            series_counts[series] = series_counts.get(series, 0) + 1

        for series, count in sorted(series_counts.items()):
            percentage = (
                (count / len(all_schedule_data) * 100)
                if len(all_schedule_data) > 0
                else 0
            )
            print(f"  {series}: {count} entries ({percentage:.1f}%)")

        print("=" * 70)

    except requests.RequestException as e:
        error_time = datetime.now()
        elapsed_time = error_time - start_time
        print(f"\n❌ NETWORK ERROR OCCURRED!")
        print("=" * 50)
        print(f"🕐 Session Start: {start_time.strftime('%H:%M:%S')}")
        print(f"❌ Error Time:    {error_time.strftime('%H:%M:%S')}")
        print(f"⏱️  Elapsed Time:  {elapsed_time}")
        print(f"🚨 Error Details: {str(e)}")
        print("=" * 50)
    except Exception as e:
        error_time = datetime.now()
        elapsed_time = error_time - start_time
        print(f"\n❌ ERROR OCCURRED!")
        print("=" * 50)
        print(f"🕐 Session Start: {start_time.strftime('%H:%M:%S')}")
        print(f"❌ Error Time:    {error_time.strftime('%H:%M:%S')}")
        print(f"⏱️  Elapsed Time:  {elapsed_time}")
        print(f"🚨 Error Details: {str(e)}")
        print("=" * 50)


if __name__ == "__main__":
    print("🎾 TennisScores Schedule Scraper - Dynamic Discovery Mode")
    print("=" * 60)
    print("🔍 Dynamically discovering ALL schedules from any TennisScores website")
    print("📊 No more hardcoded values - everything is discovered automatically!")
    print()

    # Get league input from user
    league_subdomain = (
        input("Enter league subdomain (e.g., 'aptachicago', 'nstf'): ").strip().lower()
    )

    if not league_subdomain:
        print("❌ No league subdomain provided. Exiting.")
        exit(1)

    target_url = f"https://{league_subdomain}.tenniscores.com"
    print(f"🌐 Target URL: {target_url}")
    print()

    print("📅 Comprehensive schedule scraping mode")
    print("   Will collect all schedule data from all discovered series")
    print()

    scrape_tennis_schedule(league_subdomain)
    print(f"\n✅ Schedule scraping complete for {league_subdomain.upper()}!")
