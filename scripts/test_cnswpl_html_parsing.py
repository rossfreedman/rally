#!/usr/bin/env python3
"""
Test CNSWPL HTML Parsing
========================

This script tests the CNSWPL HTML parsing logic with sample HTML.
"""

import re
from datetime import datetime

from bs4 import BeautifulSoup


def test_cnswpl_parsing():
    """Test CNSWPL parsing with sample HTML structure"""

    # Sample HTML structure based on what the user showed us
    sample_html = """
    <div class="match_results_table">
        <div class="points"></div>
        <div class="team_name">Hinsdale PC</div>
        <div class="match_rest">January 9, 2025 - 6:30 PM</div>
        <div class="team_name2">Birchwood</div>
        <div class="points2"></div>
        
        <div class="points"><img src="/images/icons/check_mark.gif"></div>
        <div class="team_name">Sue Cooper / Linda Polakowski</div>
        <div class="match_rest">6-3, 6-1</div>
        <div class="team_name2">Alison Morgan / Sari Hirsch</div>
        <div class="points2"></div>
        
        <div class="points"></div>
        <div class="team_name">Jane Smith / Mary Johnson</div>
        <div class="match_rest">4-6, 6-2, 6-4</div>
        <div class="team_name2">Lisa Brown / Sarah Wilson</div>
        <div class="points2"><img src="/images/icons/check_mark.gif"></div>
    </div>
    """

    soup = BeautifulSoup(sample_html, "html.parser")

    # Test the parsing logic
    print("🔍 Testing CNSWPL parsing logic...")

    table_element = soup.find("div", class_="match_results_table")
    if not table_element:
        print("❌ No match_results_table found")
        return

    # Get all divs within the table
    all_divs = table_element.find_all("div")

    # Organize divs by their CSS classes
    divs_by_class = {
        "points": [],
        "team_name": [],
        "match_rest": [],
        "team_name2": [],
        "points2": [],
    }

    for div in all_divs:
        div_classes = div.get("class", [])
        div_text = div.get_text(strip=True)

        print(f"Div: classes={div_classes}, text='{div_text}'")

        # Categorize divs by their CSS classes
        for class_name in divs_by_class.keys():
            if class_name in div_classes:
                divs_by_class[class_name].append(div_text)
                break

    print("\n📊 Organized divs by class:")
    for class_name, texts in divs_by_class.items():
        print(f"  {class_name}: {texts}")

    # Test parsing logic
    print("\n🔍 Testing row-by-row parsing:")

    # Parse rows - each row consists of 5 divs (points, team_name, match_rest, team_name2, points2)
    num_rows = min(
        len(divs_by_class["team_name"]),
        len(divs_by_class["team_name2"]),
        len(divs_by_class["match_rest"]),
    )
    print(f"Found {num_rows} potential rows to parse")

    for i in range(num_rows):
        try:
            points1 = (
                divs_by_class["points"][i] if i < len(divs_by_class["points"]) else ""
            )
            team1 = (
                divs_by_class["team_name"][i]
                if i < len(divs_by_class["team_name"])
                else ""
            )
            match_rest = (
                divs_by_class["match_rest"][i]
                if i < len(divs_by_class["match_rest"])
                else ""
            )
            team2 = (
                divs_by_class["team_name2"][i]
                if i < len(divs_by_class["team_name2"])
                else ""
            )
            points2 = (
                divs_by_class["points2"][i] if i < len(divs_by_class["points2"]) else ""
            )

            print(f"\nRow {i}:")
            print(f"  Points1: '{points1}'")
            print(f"  Team1: '{team1}'")
            print(f"  Match Rest: '{match_rest}'")
            print(f"  Team2: '{team2}'")
            print(f"  Points2: '{points2}'")

            # Determine if this is a header row or match row
            if "/" in team1 and "/" in team2:
                print(f"  → This looks like a MATCH ROW")

                # Parse player names
                home_players = [p.strip() for p in team1.split("/")]
                away_players = [p.strip() for p in team2.split("/")]

                print(f"    Home players: {home_players}")
                print(f"    Away players: {away_players}")
                print(f"    Score: {match_rest}")

                # Determine winner
                winner = "unknown"
                if "check" in points1.lower() or len(points1) > 0:
                    winner = "home"
                elif "check" in points2.lower() or len(points2) > 0:
                    winner = "away"

                print(f"    Winner: {winner}")

            elif re.match(
                r"^(January|February|March|April|May|June|July|August|September|October|November|December)",
                match_rest,
            ):
                print(f"  → This looks like a HEADER ROW (date/teams)")
                print(f"    Date: {match_rest}")
                print(f"    Home Team: {team1}")
                print(f"    Away Team: {team2}")
            else:
                print(f"  → Unknown row type")

        except Exception as e:
            print(f"  ❌ Error parsing row {i}: {e}")


if __name__ == "__main__":
    test_cnswpl_parsing()
