"""
Starting PTI lookup utility for calculating PTI deltas from beginning of season.

This module provides functionality to lookup a player's starting PTI from the CSV file
and calculate the delta from their current PTI.
"""

import csv
import os
from typing import Optional, Dict, Any


def load_starting_pti_data() -> Dict[str, float]:
    """
    Load starting PTI data from CSV file into a lookup dictionary.
    
    Returns:
        Dict mapping player identifiers to starting PTI values
    """
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'APTA Players - 2025 Season Starting PTI.csv')
    
    if not os.path.exists(csv_path):
        print(f"Warning: Starting PTI CSV file not found at {csv_path}")
        return {}
    
    starting_pti_data = {}
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                first_name = row.get('First Name', '').strip()
                last_name = row.get('Last Name', '').strip()
                club = row.get('Club', '').strip()
                series = row.get('Series', '').strip()
                pti_str = row.get('PTI', '').strip()
                
                # Skip rows with empty PTI values
                if not pti_str:
                    continue
                
                try:
                    pti_value = float(pti_str)
                except ValueError:
                    continue
                
                # Create lookup key: "FirstName LastName Club Series"
                # This matches the pattern used in the database for player identification
                lookup_key = f"{first_name} {last_name} {club} {series}"
                starting_pti_data[lookup_key] = pti_value
                
    except Exception as e:
        print(f"Error loading starting PTI data: {e}")
        return {}
    
    print(f"Loaded {len(starting_pti_data)} starting PTI records")
    return starting_pti_data


def get_starting_pti_for_player(player_data: Dict[str, Any]) -> Optional[float]:
    """
    Get the starting PTI for a specific player based on their data.
    
    Args:
        player_data: Dictionary containing player information with keys:
                    - first_name, last_name, club, series (for CSV lookup)
                    - tenniscores_player_id (for database lookup)
    
    Returns:
        Starting PTI value if found, None otherwise
    """
    if not player_data:
        return None
    
    # Load starting PTI data (cached on first call)
    if not hasattr(get_starting_pti_for_player, '_cached_data'):
        get_starting_pti_for_player._cached_data = load_starting_pti_data()
    
    cached_data = get_starting_pti_for_player._cached_data
    
    # Try to match by name, club, and series
    first_name = player_data.get('first_name', '').strip()
    last_name = player_data.get('last_name', '').strip()
    club = player_data.get('club', '').strip()
    series = player_data.get('series', '').strip()
    
    if all([first_name, last_name, club, series]):
        lookup_key = f"{first_name} {last_name} {club} {series}"
        starting_pti = cached_data.get(lookup_key)
        
        if starting_pti is not None:
            print(f"Found starting PTI for {lookup_key}: {starting_pti}")
            return starting_pti
    
    # If no match found, try alternative matching strategies
    player_id = player_data.get('tenniscores_player_id')
    if player_id:
        print(f"No starting PTI found for {first_name} {last_name} ({club}, {series})")
        print(f"Player ID: {player_id}")
    
    return None


def calculate_pti_delta(current_pti: Optional[float], starting_pti: Optional[float]) -> Optional[float]:
    """
    Calculate the PTI delta (current - starting).
    
    Args:
        current_pti: Current PTI value
        starting_pti: Starting PTI value from beginning of season
    
    Returns:
        PTI delta if both values are available, None otherwise
    """
    if current_pti is None or starting_pti is None:
        return None
    
    return round(current_pti - starting_pti, 1)


def get_pti_delta_for_user(user_data: Dict[str, Any], current_pti: Optional[float]) -> Dict[str, Any]:
    """
    Get PTI delta information for a user.
    
    Args:
        user_data: User session data containing player information
        current_pti: Current PTI value
    
    Returns:
        Dictionary containing:
        - starting_pti: Starting PTI value
        - pti_delta: Delta from starting PTI
        - delta_available: Boolean indicating if delta calculation is possible
    """
    starting_pti = get_starting_pti_for_player(user_data)
    pti_delta = calculate_pti_delta(current_pti, starting_pti)
    
    return {
        'starting_pti': starting_pti,
        'pti_delta': pti_delta,
        'delta_available': pti_delta is not None
    }
