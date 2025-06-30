#!/usr/bin/env python3
"""
Post-Processing Script: Fix Null Player IDs with Valid Names
This script finds matches where player IDs are null but player names exist,
and resolves them using cross-league database lookups.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one, execute_update
from datetime import datetime


def find_null_player_ids_with_names():
    """Find matches with null player IDs but valid names"""
    print("🔍 Finding matches with null player IDs but valid names...")
    
    # Query to find matches with null player IDs
    query = """
        SELECT id, match_date, home_team, away_team,
               CASE 
                   WHEN home_player_1_id IS NULL AND home_player_1_name IS NOT NULL THEN 'home_player_1'
                   WHEN home_player_2_id IS NULL AND home_player_2_name IS NOT NULL THEN 'home_player_2'
                   WHEN away_player_1_id IS NULL AND away_player_1_name IS NOT NULL THEN 'away_player_1'
                   WHEN away_player_2_id IS NULL AND away_player_2_name IS NOT NULL THEN 'away_player_2'
               END as missing_field,
               CASE 
                   WHEN home_player_1_id IS NULL AND home_player_1_name IS NOT NULL THEN home_player_1_name
                   WHEN home_player_2_id IS NULL AND home_player_2_name IS NOT NULL THEN home_player_2_name
                   WHEN away_player_1_id IS NULL AND away_player_1_name IS NOT NULL THEN away_player_1_name
                   WHEN away_player_2_id IS NULL AND away_player_2_name IS NOT NULL THEN away_player_2_name
               END as player_name,
               league_id
        FROM match_scores
        WHERE (home_player_1_id IS NULL AND home_player_1_name IS NOT NULL)
           OR (home_player_2_id IS NULL AND home_player_2_name IS NOT NULL)
           OR (away_player_1_id IS NULL AND away_player_1_name IS NOT NULL)
           OR (away_player_2_id IS NULL AND away_player_2_name IS NOT NULL)
        ORDER BY match_date DESC
    """
    
    # Note: The above query assumes match_scores table has name columns
    # If not, we need to get names from the original JSON data
    # Let's check if the table has name columns first
    
    try:
        results = execute_query(query)
        return results
    except Exception as e:
        print(f"❌ Query failed (likely no name columns): {e}")
        print("🔄 Using alternative approach with raw JSON data...")
        return []


def find_null_ids_alternative():
    """Alternative approach: Find null player IDs in match_scores table"""
    print("🔍 Finding matches with null player IDs (any position)...")
    
    query = """
        SELECT id, match_date, home_team, away_team,
               home_player_1_id, home_player_2_id, 
               away_player_1_id, away_player_2_id,
               league_id
        FROM match_scores
        WHERE home_player_1_id IS NULL 
           OR home_player_2_id IS NULL 
           OR away_player_1_id IS NULL 
           OR away_player_2_id IS NULL
        ORDER BY match_date DESC
        LIMIT 50
    """
    
    results = execute_query(query)
    print(f"📊 Found {len(results)} matches with at least one null player ID")
    
    return results


def parse_player_name(full_name):
    """Parse full name into first and last name"""
    if not full_name:
        return None, None
        
    # Handle "Last, First" format
    if ", " in full_name:
        parts = full_name.split(", ", 1)
        return parts[1].strip(), parts[0].strip()
    
    # Handle "First Last" format
    name_parts = full_name.strip().split()
    if len(name_parts) >= 2:
        return name_parts[0], " ".join(name_parts[1:])
    elif len(name_parts) == 1:
        return name_parts[0], ""
    
    return None, None


def cross_league_player_lookup(first_name, last_name):
    """Search for player across all leagues"""
    if not first_name or not last_name:
        return None
    
    query = """
        SELECT p.tenniscores_player_id, p.first_name, p.last_name,
               l.league_id, c.name as club_name, s.name as series_name
        FROM players p
        JOIN leagues l ON p.league_id = l.id
        JOIN clubs c ON p.club_id = c.id
        JOIN series s ON p.series_id = s.id
        WHERE LOWER(p.first_name) = LOWER(%s) 
        AND LOWER(p.last_name) = LOWER(%s)
        AND p.is_active = TRUE
        ORDER BY l.league_id
    """
    
    results = execute_query(query, [first_name, last_name])
    return results


def get_match_players_from_json(match_id, home_team, away_team, match_date):
    """
    Try to get player names from the original JSON data
    This is a workaround if the database doesn't store player names
    """
    # This would require loading and searching the JSON files
    # For now, we'll return None and suggest manual inspection
    print(f"  📝 Match {match_id}: {home_team} vs {away_team} on {match_date}")
    print(f"     💡 Check original JSON data for player names")
    return []


def fix_null_player_ids(dry_run=True):
    """Main function to fix null player IDs"""
    print("🔧 Starting null player ID fix process...")
    print(f"🚀 Mode: {'DRY RUN' if dry_run else 'LIVE UPDATES'}")
    print("=" * 60)
    
    # Find matches with null player IDs
    null_matches = find_null_ids_alternative()
    
    if not null_matches:
        print("✅ No matches with null player IDs found!")
        return
    
    fixes_made = 0
    total_nulls = 0
    
    for match in null_matches[:10]:  # Process first 10 for testing
        match_id = match['id']
        match_date = match['match_date']
        home_team = match['home_team']
        away_team = match['away_team']
        league_id = match['league_id']
        
        print(f"\n🔍 Match {match_id}: {home_team} vs {away_team} ({match_date})")
        
        # Check each player position
        positions = [
            ('home_player_1_id', 'Home Player 1'),
            ('home_player_2_id', 'Home Player 2'),
            ('away_player_1_id', 'Away Player 1'),
            ('away_player_2_id', 'Away Player 2')
        ]
        
        for field, position in positions:
            if match[field] is None:
                total_nulls += 1
                print(f"  ❌ {position}: NULL player ID")
                
                # For this demo, we'll show what would happen
                # In a real scenario, you'd need to get the player name
                # either from the original JSON or user input
                print(f"     💡 Would need player name to attempt cross-league lookup")
                print(f"     📝 Consider checking original JSON data for this match")
    
    print(f"\n📊 Summary:")
    print(f"   🔍 Processed: {min(10, len(null_matches))} matches")
    print(f"   ❌ Total null player IDs: {total_nulls}")
    print(f"   ✅ Fixes made: {fixes_made}")
    
    if total_nulls > 0:
        print(f"\n💡 Next steps:")
        print(f"   1. Identify player names from original JSON data")
        print(f"   2. Use cross_league_player_lookup() to find player IDs") 
        print(f"   3. Update match_scores table with resolved IDs")


def demo_cross_league_lookup():
    """Demo the cross-league lookup functionality"""
    print("\n🎯 Demo: Cross-League Player Lookup")
    print("=" * 40)
    
    # Test with known substitute player
    test_names = [
        ("Mariano", "Martinez"),
        ("John", "Smith"),  # Common name
        ("Test", "Player")  # Non-existent
    ]
    
    for first_name, last_name in test_names:
        print(f"\n🔍 Searching for: {first_name} {last_name}")
        results = cross_league_player_lookup(first_name, last_name)
        
        if results:
            for result in results:
                print(f"  ✅ Found: {result['first_name']} {result['last_name']}")
                print(f"     ID: {result['tenniscores_player_id']}")
                print(f"     League: {result['league_id']}")
                print(f"     Club: {result['club_name']}")
                print(f"     Series: {result['series_name']}")
        else:
            print(f"  ❌ No matches found")


def create_fix_template():
    """Create a template script for manual fixes"""
    template = '''#!/usr/bin/env python3
"""
Manual Fix Template for Specific Null Player IDs
Update this script with specific player names and match IDs
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query_one, execute_update

# Manual fixes - update these with actual data
FIXES = [
    {
        "match_id": 815833,
        "field": "away_player_2_id", 
        "player_name": "Mariano Martinez",
        "resolved_id": "nndz-WkNHeHdiZjlqUT09"
    },
    # Add more fixes here...
]

def apply_manual_fixes(dry_run=True):
    """Apply the manual fixes"""
    print(f"🔧 Applying manual fixes (DRY RUN: {dry_run})")
    
    for fix in FIXES:
        match_id = fix["match_id"]
        field = fix["field"]
        player_name = fix["player_name"]
        resolved_id = fix["resolved_id"]
        
        print(f"  📝 Match {match_id}: {field} = '{player_name}' → {resolved_id}")
        
        if not dry_run:
            query = f"UPDATE match_scores SET {field} = %s WHERE id = %s"
            execute_update(query, [resolved_id, match_id])
            print(f"    ✅ Updated!")
        else:
            print(f"    🚀 Would update (dry run)")

if __name__ == "__main__":
    apply_manual_fixes(dry_run=True)
'''
    
    with open("scripts/manual_player_id_fixes.py", "w") as f:
        f.write(template)
    
    print("📝 Created manual fix template: scripts/manual_player_id_fixes.py")


def main():
    """Main function"""
    print("🎾 Null Player ID Fix Tool")
    print("=" * 50)
    
    print("\n1️⃣  Finding null player IDs...")
    fix_null_player_ids(dry_run=True)
    
    print("\n2️⃣  Demo cross-league lookup...")
    demo_cross_league_lookup()
    
    print("\n3️⃣  Creating manual fix template...")
    create_fix_template()
    
    print("\n" + "=" * 50)
    print("✅ Null Player ID analysis complete!")
    print("\n💡 Usage:")
    print("   - Run this script to identify null player ID issues")
    print("   - Use cross_league_player_lookup() to resolve player names")
    print("   - Apply fixes using the manual template or database updates")


if __name__ == "__main__":
    main() 