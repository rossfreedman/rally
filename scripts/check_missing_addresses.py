#!/usr/bin/env python3

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query

print("🔍 Clubs WITHOUT addresses:")
print("=" * 40)

clubs_without = execute_query(
    """
    SELECT name FROM clubs 
    WHERE club_address IS NULL OR club_address = '' 
    ORDER BY name
"""
)

for i, club in enumerate(clubs_without, 1):
    print(f'{i:2d}. {club["name"]}')

print(f"\n📊 Total: {len(clubs_without)} clubs need addresses")

print("\n✅ Clubs WITH addresses:")
print("=" * 40)

clubs_with = execute_query(
    """
    SELECT name, club_address FROM clubs 
    WHERE club_address IS NOT NULL AND club_address != '' 
    ORDER BY name
    LIMIT 5
"""
)

for club in clubs_with:
    print(f'✓ {club["name"]}: {club["club_address"][:50]}...')

clubs_with_count = execute_query(
    "SELECT COUNT(*) as count FROM clubs WHERE club_address IS NOT NULL AND club_address != ''"
)[0]["count"]
print(f"\n📊 Total: {clubs_with_count} clubs have addresses")
