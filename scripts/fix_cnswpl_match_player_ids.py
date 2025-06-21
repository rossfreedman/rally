#!/usr/bin/env python3
"""
Fix CNSWPL Match History Player IDs
==================================

This script fixes null player IDs in the CNSWPL match_history.json file
by matching player names to the players.json data using enhanced name matching.
"""

import sys
import os
import json
import re
from typing import Dict, List, Optional

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Common nickname mappings for better name matching
NICKNAME_MAPPINGS = {
    # Common nicknames to full names
    'mike': ['michael'],
    'jim': ['james'],
    'bob': ['robert'],
    'bill': ['william'],
    'dave': ['david'],
    'steve': ['steven', 'stephen'],
    'chris': ['christopher'],
    'matt': ['matthew'],
    'dan': ['daniel'],
    'tom': ['thomas'],
    'tony': ['anthony'],
    'rick': ['richard'],
    'dick': ['richard'],
    'nick': ['nicholas'],
    'ben': ['benjamin'],
    'sam': ['samuel'],
    'alex': ['alexander'],
    'brad': ['bradley'],
    'greg': ['gregory'],
    'rob': ['robert'],
    'joe': ['joseph'],
    'pat': ['patrick'],
    'ed': ['edward'],
    'ted': ['theodore', 'edward'],
    'andy': ['andrew'],
    'brian': ['bryan'],  # Common spelling variation
    'bryan': ['brian'],  # Reverse mapping
    
    # Full names to nicknames (reverse mappings)
    'michael': ['mike'],
    'james': ['jim', 'jimmy'],
    'robert': ['bob', 'rob'],
    'william': ['bill', 'will'],
    'david': ['dave'],
    'steven': ['steve'],
    'stephen': ['steve'],
    'christopher': ['chris'],
    'matthew': ['matt'],
    'daniel': ['dan', 'danny'],
    'thomas': ['tom'],
    'anthony': ['tony'],
    'richard': ['rick', 'dick'],
    'nicholas': ['nick'],
    'benjamin': ['ben'],
    'samuel': ['sam'],
    'alexander': ['alex'],
    'bradley': ['brad'],
    'gregory': ['greg'],
    'joseph': ['joe'],
    'patrick': ['pat'],
    'edward': ['ed', 'ted'],
    'theodore': ['ted'],
    'andrew': ['andy'],
}

def get_name_variations(name):
    """Get all possible variations of a name including nicknames."""
    if not name:
        return []
    
    name_lower = name.lower()
    variations = [name_lower]  # Always include the original
    
    # Add mapped variations
    if name_lower in NICKNAME_MAPPINGS:
        variations.extend(NICKNAME_MAPPINGS[name_lower])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_variations = []
    for var in variations:
        if var not in seen:
            seen.add(var)
            unique_variations.append(var)
    
    return unique_variations

def normalize_name_for_lookup(name):
    """Normalize a name for more flexible matching."""
    if not name:
        return ""
    # Convert to lowercase and strip whitespace
    normalized = name.lower().strip()
    
    # Remove common suffixes and patterns
    patterns_to_remove = [
        ' by forfeit',
        ' forfeit',
        'by forfeit',
        ' jr.',
        ' jr',
        ' sr.',
        ' sr',
        ' iii',
        ' iv',
        ' ii'
    ]
    
    for pattern in patterns_to_remove:
        if normalized.endswith(pattern):
            normalized = normalized[:-len(pattern)].strip()
    
    # Remove periods and other punctuation
    normalized = normalized.replace(".", "").replace(",", "")
    
    return normalized

def extract_club_name_from_team(team_name):
    """Extract the club name from a team name like 'Birchwood 1' -> 'Birchwood'."""
    if not team_name:
        return ""
    
    # For CNSWPL format: "Club Number" or "Club NumberLetter" 
    # Remove series suffixes like "1", "1a", "2b", etc.
    pattern = r'\s+\d+[a-zA-Z]*$'
    cleaned = re.sub(pattern, '', team_name).strip()
    return cleaned if cleaned else team_name.strip()

def extract_series_name_from_team(team_name):
    """Extract series name from CNSWPL team name."""
    if not team_name:
        return None
        
    team_name = team_name.strip()
    
    # CNSWPL format: "Club Number" or "Club NumberLetter" (e.g., "Birchwood 1", "Hinsdale PC 1a")
    match = re.search(r'\s(\d+[a-zA-Z]?)$', team_name)
    if match:
        series_identifier = match.group(1)
        return f"Series {series_identifier}"
    
    return None

def levenshtein_distance(s1, s2):
    """Calculate Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]

def similar_strings(s1, s2, threshold=0.8):
    """Check if two strings are similar using Levenshtein distance and character overlap."""
    if not s1 or not s2:
        return False
    
    # Quick exact match
    if s1.lower() == s2.lower():
        return True
    
    # Levenshtein distance approach for short strings
    if len(s1) <= 8 and len(s2) <= 8:
        max_len = max(len(s1), len(s2))
        if max_len == 0:
            return True
        distance = levenshtein_distance(s1.lower(), s2.lower())
        similarity = 1 - (distance / max_len)
        if similarity >= threshold:
            return True
    
    # Character overlap method for longer strings
    set1 = set(s1.lower())
    set2 = set(s2.lower())
    
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    
    similarity = intersection / union if union > 0 else 0
    return similarity >= threshold

def lookup_player_id_enhanced(players_data, series, team_name, first_name, last_name):
    """Enhanced Player ID lookup with multiple strategies for better accuracy."""
    # Convert series from "Series X" to "Division X" format used in players.json
    players_series = series.replace("Series ", "Division ") if series else ""
    
    # For CNSWPL, the Club field in players.json contains the full team name
    # So use the full team_name for club matching
    club_name = team_name  # Use full team name like "Birchwood 1"
    
    # Also try with just the club name extracted
    club_name_short = extract_club_name_from_team(team_name)  # Just "Birchwood"
    
    # Normalize names for lookup
    first_name_norm = normalize_name_for_lookup(first_name)
    last_name_norm = normalize_name_for_lookup(last_name)
    
    if not first_name_norm or not last_name_norm:
        return None
    
    print(f"      Looking for: '{first_name}' '{last_name}' in '{players_series}' at '{club_name}'")
    
    # Strategy 1: Exact match (Series + Full Team Name + Names)
    for player in players_data:
        if (player.get('Series') == players_series and 
            player.get('Club') == club_name and
            normalize_name_for_lookup(player.get('First Name', '')) == first_name_norm and
            normalize_name_for_lookup(player.get('Last Name', '')) == last_name_norm):
            print(f"      ✅ Strategy 1 match: {player.get('First Name')} {player.get('Last Name')} → {player.get('Player ID')}")
            return player.get('Player ID')
    
    # Strategy 2: Series-wide matching (handles club changes)
    series_matches = []
    for player in players_data:
        if (player.get('Series') == players_series and
            normalize_name_for_lookup(player.get('First Name', '')) == first_name_norm and
            normalize_name_for_lookup(player.get('Last Name', '')) == last_name_norm):
            series_matches.append(player)
    
    if len(series_matches) == 1:
        player = series_matches[0]
        print(f"      ✅ Strategy 2 match: {player.get('First Name')} {player.get('Last Name')} → {player.get('Player ID')} (Club: {player.get('Club')})")
        return player.get('Player ID')
    
    # Strategy 3: Nickname matching (same club)
    first_name_variations = get_name_variations(first_name_norm)
    last_name_variations = get_name_variations(last_name_norm)
    
    for player in players_data:
        if (player.get('Series') == players_series and 
            player.get('Club') == club_name):
            
            player_first_norm = normalize_name_for_lookup(player.get('First Name', ''))
            player_last_norm = normalize_name_for_lookup(player.get('Last Name', ''))
            
            # Check if any variation of the search name matches any variation of the player name
            first_match = (player_first_norm in first_name_variations or 
                          any(var in get_name_variations(player_first_norm) for var in first_name_variations))
            
            last_match = (player_last_norm in last_name_variations or
                         any(var in get_name_variations(player_last_norm) for var in last_name_variations))
            
            if first_match and last_match:
                print(f"      ✅ Strategy 3 match: {player.get('First Name')} {player.get('Last Name')} → {player.get('Player ID')}")
                return player.get('Player ID')
    
    # Strategy 4: Fuzzy matching (same club)
    for player in players_data:
        if (player.get('Series') == players_series and 
            player.get('Club') == club_name):
            
            player_first_norm = normalize_name_for_lookup(player.get('First Name', ''))
            player_last_norm = normalize_name_for_lookup(player.get('Last Name', ''))
            
            # Try various fuzzy matching approaches
            first_similar = similar_strings(first_name_norm, player_first_norm, threshold=0.8)
            last_similar = similar_strings(last_name_norm, player_last_norm, threshold=0.8)
            
            if first_similar and last_similar:
                print(f"      ✅ Strategy 4 match: {player.get('First Name')} {player.get('Last Name')} → {player.get('Player ID')}")
                return player.get('Player ID')
    
    # No match found
    print(f"      ❌ No match found for {first_name} {last_name}")
    return None

def fix_cnswpl_match_player_ids(league_data_dir=None, verbose=True):
    """Main function to fix null player IDs in CNSWPL match history"""
    
    if verbose:
        print("🔧 Fixing CNSWPL Match History Player IDs")
        print("=" * 50)
    
    # Get project paths
    if league_data_dir:
        cnswpl_dir = league_data_dir
    else:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cnswpl_dir = os.path.join(project_root, 'data', 'leagues', 'CNSWPL')
    
    match_history_path = os.path.join(cnswpl_dir, 'match_history.json')
    players_path = os.path.join(cnswpl_dir, 'players.json')
    
    # Load players data
    if verbose:
        print(f"📂 Loading players data from: {players_path}")
    try:
        with open(players_path, 'r', encoding='utf-8') as f:
            players_data = json.load(f)
        if verbose:
            print(f"✅ Loaded {len(players_data)} players")
    except Exception as e:
        if verbose:
            print(f"❌ Error loading players data: {e}")
        return False
    
    # Load match history
    if verbose:
        print(f"📂 Loading match history from: {match_history_path}")
    try:
        with open(match_history_path, 'r', encoding='utf-8') as f:
            matches = json.load(f)
        if verbose:
            print(f"✅ Loaded {len(matches)} matches")
    except Exception as e:
        if verbose:
            print(f"❌ Error loading match history: {e}")
        return False
    
    # Statistics
    stats = {
        'total_matches': len(matches),
        'total_players': 0,
        'null_players': 0,
        'fixed_players': 0,
        'still_null': 0
    }
    
    if verbose:
        print(f"\n🔍 Processing {stats['total_matches']} matches...")
        print("-" * 50)
    
    # Process each match
    for match_idx, match in enumerate(matches):
        if match_idx % 100 == 0 and verbose:
            print(f"📊 Processing match {match_idx + 1}/{len(matches)}")
        
        # Extract match info
        home_team = match.get('Home Team', '')
        away_team = match.get('Away Team', '')
        date = match.get('Date', '')
        
        # Show detailed output for first few matches only in verbose mode
        show_debug = match_idx < 3 and verbose
        
        if show_debug:
            print(f"\n🔍 Debug Match {match_idx + 1}: {home_team} vs {away_team} on {date}")
        
        # Process each player position
        player_positions = [
            ('Home Player 1', 'Home Player 1 ID', home_team),
            ('Home Player 2', 'Home Player 2 ID', home_team),
            ('Away Player 1', 'Away Player 1 ID', away_team),
            ('Away Player 2', 'Away Player 2 ID', away_team),
        ]
        
        for player_name_key, player_id_key, team_name in player_positions:
            stats['total_players'] += 1
            
            player_name = match.get(player_name_key, '')
            current_player_id = match.get(player_id_key)
            
            # Skip if already has ID
            if current_player_id is not None:
                continue
            
            stats['null_players'] += 1
            
            # Skip if no player name
            if not player_name:
                continue
            
            # Split player name into first and last
            name_parts = player_name.strip().split()
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = " ".join(name_parts[1:])
            else:
                continue
            
            # Get series name for this team
            series_name = extract_series_name_from_team(team_name)
            if not series_name:
                if show_debug:
                    print(f"    ⚠️ Could not extract series from team: {team_name}")
                continue
            
            if show_debug:
                print(f"    🔍 Processing: {player_name} (Team: {team_name} → Series: {series_name})")
            
            # Lookup player ID (suppress output unless in debug mode)
            if show_debug:
                player_id = lookup_player_id_enhanced(players_data, series_name, team_name, first_name, last_name)
            elif verbose:
                # Suppress detailed lookup output but allow basic output
                import io
                import contextlib
                f = io.StringIO()
                with contextlib.redirect_stdout(f):
                    player_id = lookup_player_id_enhanced(players_data, series_name, team_name, first_name, last_name)
            else:
                # Completely suppress all output for non-verbose mode
                import io
                import contextlib
                f = io.StringIO()
                with contextlib.redirect_stdout(f):
                    player_id = lookup_player_id_enhanced(players_data, series_name, team_name, first_name, last_name)
            
            if player_id:
                match[player_id_key] = player_id
                stats['fixed_players'] += 1
                if (stats['fixed_players'] <= 10 or show_debug) and verbose:  # Show first 10 fixes or debug matches
                    print(f"   ✅ Fixed: {player_name} → {player_id}")
            else:
                stats['still_null'] += 1
                if show_debug:
                    print(f"   ❌ Could not find ID for: {player_name}")
    
    # Save updated match history
    if verbose:
        print(f"\n💾 Saving updated match history...")
    try:
        with open(match_history_path, 'w', encoding='utf-8') as f:
            json.dump(matches, f, indent=2)
        if verbose:
            print(f"✅ Saved updated match history to: {match_history_path}")
    except Exception as e:
        if verbose:
            print(f"❌ Error saving match history: {e}")
        return False
    
    # Print final statistics
    if verbose:
        print("\n" + "=" * 50)
        print("📊 FINAL STATISTICS")
        print("=" * 50)
        print(f"Total matches processed: {stats['total_matches']}")
        print(f"Total player positions: {stats['total_players']}")
        print(f"Originally null player IDs: {stats['null_players']}")
        print(f"Successfully fixed: {stats['fixed_players']}")
        print(f"Still null: {stats['still_null']}")
        
        if stats['null_players'] > 0:
            fix_rate = (stats['fixed_players'] / stats['null_players']) * 100
            print(f"\n🎯 Fix rate: {fix_rate:.1f}%")
        
        if stats['fixed_players'] > 0:
            print(f"\n✅ Successfully fixed {stats['fixed_players']} player IDs!")
    
    # Return statistics for programmatic use
    return stats

if __name__ == "__main__":
    stats = fix_cnswpl_match_player_ids()
    
    if stats and isinstance(stats, dict):
        print("\n🎉 CNSWPL player ID fix completed successfully!")
    else:
        print("\n❌ Player ID fix failed. Check the output above.") 