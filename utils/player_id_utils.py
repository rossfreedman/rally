import re

def extract_tenniscores_player_id(href_url):
    """
    Extract the native TennisScores player ID from a URL.
    
    Args:
        href_url (str): The href URL from a player link
        
    Returns:
        str: The native TennisScores player ID (e.g., 'nndz-WkMrK3didjlnUT09')
             or None if no ID found
    """
    if not href_url:
        return None
    
    # TennisScores uses 'uid' parameter for player IDs
    # Example: /?mod=nndz-SkhmOW1PQ3V4dXBjakNnUA%3D%3D&uid=nndz-WkMrK3didjlnUT09
    
    id_patterns = [
        r'uid=([^&]+)',           # uid= parameter (primary)
        r'p=([^&]+)',             # p= parameter (alternative)
        r'player_id=([^&]+)',     # player_id= parameter
        r'player=([^&]+)'         # player= parameter
    ]
    
    for pattern in id_patterns:
        match = re.search(pattern, href_url)
        if match:
            return match.group(1)
    
    return None

def create_player_id(tenniscores_id, first_name=None, last_name=None, club_name=None):
    """
    Create a player ID using TennisScores native ID as the primary method,
    with fallback to name-based ID generation.
    
    Args:
        tenniscores_id (str): The native TennisScores player ID
        first_name (str): Player's first name (for fallback)
        last_name (str): Player's last name (for fallback) 
        club_name (str): Player's club name (for fallback)
        
    Returns:
        str: The raw TennisScores native ID or fallback ID
    """
    # Primary: Use TennisScores native ID (raw, no prefix)
    if tenniscores_id:
        return tenniscores_id
    
    # Fallback: Create deterministic ID from name + club
    if first_name and last_name and club_name:
        import hashlib
        first_clean = first_name.strip().title()
        last_clean = last_name.strip().title()
        club_clean = club_name.strip().replace(" ", "_").replace("&", "AND")
        
        fallback_data = f"{first_clean}_{last_clean}_{club_clean}"
        fallback_id = hashlib.md5(fallback_data.encode()).hexdigest()[:8].upper()
        return f"FALLBACK_{fallback_id}"
    
    return None

def normalize_player_name(first_name, last_name):
    """
    Normalize player name for consistent matching.
    
    Args:
        first_name (str): Player's first name
        last_name (str): Player's last name
        
    Returns:
        tuple: (normalized_first, normalized_last)
    """
    first_clean = first_name.strip().title() if first_name else ""
    last_clean = last_name.strip().title() if last_name else ""
    return first_clean, last_clean 