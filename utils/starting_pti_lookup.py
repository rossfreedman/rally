"""
Starting PTI lookup utility for calculating PTI deltas from beginning of season.

This module provides functionality to lookup a player's starting PTI from the database
and calculate the delta from their current PTI.
"""

import os
import sys
from typing import Optional, Dict, Any

# Add root directory to path for database imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query_one


def get_starting_pti_for_player(player_data: Dict[str, Any]) -> Optional[float]:
    """
    Get the starting PTI for a specific player from the database.
    
    Args:
        player_data: Dictionary containing player information with keys:
                    - tenniscores_player_id (required for lookup)
                    - league_id (optional, for more specific lookup)
    
    Returns:
        Starting PTI value if found, None otherwise
    """
    if not player_data:
        return None
    
    # Get tenniscores_player_id for lookup
    player_id = player_data.get('tenniscores_player_id')
    
    if not player_id:
        print(f"[PTI LOOKUP] Missing tenniscores_player_id")
        return None
    
    try:
        # Query database for starting_pti
        # Use league_id if available for more specific lookup
        league_id = player_data.get('league_id')
        
        if league_id:
            query = """
                SELECT starting_pti 
                FROM players 
                WHERE tenniscores_player_id = %s 
                  AND league_id = %s 
                  AND is_active = true
                LIMIT 1
            """
            result = execute_query_one(query, [player_id, league_id])
        else:
            query = """
                SELECT starting_pti 
                FROM players 
                WHERE tenniscores_player_id = %s 
                  AND is_active = true
                LIMIT 1
            """
            result = execute_query_one(query, [player_id])
        
        if result and result.get('starting_pti') is not None:
            starting_pti = float(result['starting_pti'])
            print(f"[PTI LOOKUP] Found starting PTI for player {player_id}: {starting_pti}")
            return starting_pti
        else:
            print(f"[PTI LOOKUP] No starting PTI found for player {player_id}")
            return None
            
    except Exception as e:
        print(f"[PTI LOOKUP] Error querying database: {e}")
        import traceback
        print(traceback.format_exc())
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
