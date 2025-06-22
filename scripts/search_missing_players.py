#!/usr/bin/env python3

import json

with open("data/leagues/all/players.json", "r") as f:
    players = json.load(f)

print("🔍 Searching for similar names to the unmatched users...")
print()

# Search for Jeff Day
jeff_matches = [
    p
    for p in players
    if "jeff" in p["First Name"].lower() or "day" in p["Last Name"].lower()
]
print(f'🔍 Players with "Jeff" or "Day" in name ({len(jeff_matches)} found):')
for p in jeff_matches[:10]:  # Show first 10
    print(
        f'  • {p["First Name"]} {p["Last Name"]} ({p["Club"]}) - {p["Series"]} - ID: {p["Player ID"]}'
    )

print()

# Search for Scott Osterman
scott_matches = [
    p
    for p in players
    if "scott" in p["First Name"].lower() or "osterman" in p["Last Name"].lower()
]
print(f'🔍 Players with "Scott" or "Osterman" in name ({len(scott_matches)} found):')
for p in scott_matches[:10]:  # Show first 10
    print(
        f'  • {p["First Name"]} {p["Last Name"]} ({p["Club"]}) - {p["Series"]} - ID: {p["Player ID"]}'
    )

print()

# Search for Pete Wahlstrom
pete_matches = [
    p
    for p in players
    if "pete" in p["First Name"].lower()
    or "wahlstrom" in p["Last Name"].lower()
    or "peter" in p["First Name"].lower()
]
print(
    f'🔍 Players with "Pete", "Peter" or "Wahlstrom" in name ({len(pete_matches)} found):'
)
for p in pete_matches[:10]:  # Show first 10
    print(
        f'  • {p["First Name"]} {p["Last Name"]} ({p["Club"]}) - {p["Series"]} - ID: {p["Player ID"]}'
    )

print()

# Search for Tennaqua club members
tennaqua_matches = [p for p in players if "tennaqua" in p["Club"].lower()]
print(f"🔍 Tennaqua club members ({len(tennaqua_matches)} found):")
for p in tennaqua_matches[:20]:  # Show first 20
    print(
        f'  • {p["First Name"]} {p["Last Name"]} ({p["Club"]}) - {p["Series"]} - ID: {p["Player ID"]}'
    )

print()

# Search for Glenbrook RC members
glenbrook_matches = [p for p in players if "glenbrook" in p["Club"].lower()]
print(f"🔍 Glenbrook RC club members ({len(glenbrook_matches)} found):")
for p in glenbrook_matches[:20]:  # Show first 20
    print(
        f'  • {p["First Name"]} {p["Last Name"]} ({p["Club"]}) - {p["Series"]} - ID: {p["Player ID"]}'
    )
