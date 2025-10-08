#!/usr/bin/env python3

"""
Script to update club addresses using fuzzy matching logic.
This script matches club names with addresses using fuzzy string matching
to handle variations in club names and find the best matches.

Usage: python scripts/fuzzy_match_club_addresses.py [--dry-run] [--threshold 0.8]
"""

import argparse
import os
import re
import sys
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_update, get_db

# Club normalization regex patterns
_ROMAN_RE = re.compile(r'\b[IVXLCDM]{1,4}\b', re.IGNORECASE)
_ALNUM_SUFFIX_RE = re.compile(r'\b(\d+[A-Za-z]?|[A-Za-z]?\d+)\b')
_LETTER_PAREN_RE = re.compile(r'\b[A-Za-z]{1,3}\(\d+\)\b')
_ALLCAP_SHORT_RE = re.compile(r'\b[A-Z]{1,3}\b')
_KEEP_SUFFIXES: set = {
    "cc", "country club", "racquet club", "paddle club", "golf club", 
    "tennis club", "sports club", "athletic club", "recreation club",
    "pd", "park district", "recreation", "center", "club", "academy"
}

def normalize_club_name(name: str) -> str:
    """
    Normalize a club name for better matching by removing common variations
    and standardizing the format.
    """
    if not name:
        return ""
    
    # Convert to uppercase for consistency
    normalized = name.upper().strip()
    
    # Remove common prefixes
    prefixes_to_remove = ["THE ", "A ", "AN "]
    for prefix in prefixes_to_remove:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
    
    # Remove trailing punctuation
    normalized = normalized.rstrip(".,!?")
    
    # Handle common abbreviations
    abbreviations = {
        "CC": "Country Club",
        "RC": "Racquet Club", 
        "PC": "Paddle Club",
        "GC": "Golf Club",
        "TC": "Tennis Club",
        "SC": "Sports Club",
        "AC": "Athletic Club",
        "PD": "Park District",
        "REC": "Recreation",
        "CTR": "Center",
        "CT": "Center"
    }
    
    for abbr, full in abbreviations.items():
        # Replace standalone abbreviations
        normalized = re.sub(rf'\b{abbr}\b', full, normalized)
    
    # Remove Roman numerals
    normalized = _ROMAN_RE.sub('', normalized)
    
    # Remove alphanumeric suffixes (like "I", "II", "A", "B", etc.)
    normalized = _ALNUM_SUFFIX_RE.sub('', normalized)
    
    # Remove letter-paren patterns (like "A(1)", "B(2)")
    normalized = _LETTER_PAREN_RE.sub('', normalized)
    
    # Remove all-caps short words (like "THE", "AND", "OF")
    words = normalized.split()
    filtered_words = []
    for word in words:
        if len(word) <= 3 and word.isupper() and word not in _KEEP_SUFFIXES:
            continue
        filtered_words.append(word)
    
    # Join back together
    normalized = ' '.join(filtered_words)
    
    # Clean up multiple spaces
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return normalized

def calculate_similarity(str1: str, str2: str) -> float:
    """
    Calculate similarity between two strings using SequenceMatcher.
    Returns a float between 0.0 and 1.0.
    """
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

def find_best_address_match(club_name: str, address_dict: Dict[str, str], threshold: float = 0.8) -> Optional[Tuple[str, str, float]]:
    """
    Find the best address match for a club name using fuzzy matching.
    
    Args:
        club_name: The club name to match
        address_dict: Dictionary mapping club names to addresses
        threshold: Minimum similarity score (0.0 to 1.0)
    
    Returns:
        Tuple of (matched_club_name, address, similarity_score) or None if no good match
    """
    if not club_name or not address_dict:
        return None
    
    # Normalize the input club name
    normalized_name = normalize_club_name(club_name)
    
    best_match = None
    best_score = 0.0
    
    # Try exact match first
    if club_name in address_dict:
        return (club_name, address_dict[club_name], 1.0)
    
    # Try normalized exact match
    if normalized_name in address_dict:
        return (normalized_name, address_dict[normalized_name], 1.0)
    
    # Try fuzzy matching against all available club names
    for available_name, address in address_dict.items():
        # Calculate similarity with original name
        score1 = calculate_similarity(club_name, available_name)
        
        # Calculate similarity with normalized names
        normalized_available = normalize_club_name(available_name)
        score2 = calculate_similarity(normalized_name, normalized_available)
        
        # Use the higher score
        score = max(score1, score2)
        
        if score > best_score and score >= threshold:
            best_score = score
            best_match = (available_name, address, score)
    
    return best_match

def load_addresses_from_csv(csv_file: str) -> Dict[str, str]:
    """Load addresses from CSV file"""
    addresses = {}
    
    if not os.path.exists(csv_file):
        print(f"⚠️  CSV file not found: {csv_file}")
        return addresses
    
    try:
        import csv
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                club_name = row.get('club_name', '').strip()
                address = row.get('address', '').strip()
                
                if club_name and address:
                    addresses[club_name] = address
                    # Also add normalized version
                    normalized = normalize_club_name(club_name)
                    if normalized != club_name:
                        addresses[normalized] = address
        
        print(f"📊 Loaded {len(addresses)} addresses from CSV")
        return addresses
        
    except Exception as e:
        print(f"❌ Error loading addresses from CSV: {e}")
        return {}

def get_clubs_without_addresses() -> List[Tuple[int, str]]:
    """Get all clubs that don't have addresses"""
    query = """
        SELECT id, name 
        FROM clubs 
        WHERE club_address IS NULL OR club_address = ''
        ORDER BY name
    """
    
    clubs = execute_query(query)
    return [(club['id'], club['name']) for club in clubs]

def update_club_address(club_id: int, club_name: str, address: str, dry_run: bool = False) -> bool:
    """Update a club's address in the database"""
    if dry_run:
        print(f"  🔍 [DRY RUN] Would update: {club_name} -> {address[:50]}...")
        return True
    
    try:
        query = """
            UPDATE clubs 
            SET club_address = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """
        
        execute_update(query, (address, club_id))
        print(f"  ✅ Updated: {club_name} -> {address[:50]}...")
        return True
        
    except Exception as e:
        print(f"  ❌ Error updating {club_name}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Update club addresses using fuzzy matching')
    parser.add_argument('--csv-file', default='data/club_addresses.csv', 
                       help='CSV file containing club addresses')
    parser.add_argument('--threshold', type=float, default=0.8,
                       help='Minimum similarity threshold for matches (0.0-1.0)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be updated without making changes')
    
    args = parser.parse_args()
    
    print("🏓 RALLY CLUB ADDRESS FUZZY MATCHER")
    print("=" * 50)
    print(f"CSV file: {args.csv_file}")
    print(f"Threshold: {args.threshold}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE UPDATE'}")
    print()
    
    # Load addresses from CSV
    print("📖 Loading addresses from CSV...")
    addresses = load_addresses_from_csv(args.csv_file)
    
    if not addresses:
        print("❌ No addresses loaded. Exiting.")
        return
    
    # Get clubs without addresses
    print("🔍 Finding clubs without addresses...")
    clubs_without_addresses = get_clubs_without_addresses()
    
    print(f"📊 Found {len(clubs_without_addresses)} clubs without addresses")
    print()
    
    if not clubs_without_addresses:
        print("✅ All clubs already have addresses!")
        return
    
    # Process each club
    updated_count = 0
    no_match_count = 0
    
    print("🔄 Processing clubs...")
    for club_id, club_name in clubs_without_addresses:
        print(f"\n🔍 Processing: {club_name}")
        
        # Find best match
        match = find_best_address_match(club_name, addresses, args.threshold)
        
        if match:
            matched_name, address, score = match
            print(f"  🎯 Best match: {matched_name} (score: {score:.2f})")
            
            # Update the club
            if update_club_address(club_id, club_name, address, args.dry_run):
                updated_count += 1
        else:
            print(f"  ⚠️  No good match found (threshold: {args.threshold})")
            no_match_count += 1
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    print(f"Clubs processed: {len(clubs_without_addresses)}")
    print(f"Successfully updated: {updated_count}")
    print(f"No match found: {no_match_count}")
    
    if args.dry_run:
        print("\n💡 Run without --dry-run to apply changes")
    else:
        print(f"\n✅ Address matching completed!")

if __name__ == "__main__":
    main()
