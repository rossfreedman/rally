#!/usr/bin/env python3

"""
Standalone script to load club addresses from CSV file and update the database.
This script isolates the address loading functionality from the ETL process.

Usage: python scripts/load_club_addresses_from_csv.py [--csv-file <CSV_FILE>] [--dry-run]
"""

import argparse
import csv
import os
import re
import sys
from typing import Dict, Optional, Set
from difflib import SequenceMatcher

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_update, get_db

# Club normalization regex patterns
_ROMAN_RE = re.compile(r'\b[IVXLCDM]{1,4}\b', re.IGNORECASE)
_ALNUM_SUFFIX_RE = re.compile(r'\b(\d+[A-Za-z]?|[A-Za-z]?\d+)\b')
_LETTER_PAREN_RE = re.compile(r'\b[A-Za-z]{1,3}\(\d+\)\b')
_ALLCAP_SHORT_RE = re.compile(r'\b[A-Z]{1,3}\b')
_KEEP_SUFFIXES: Set[str] = {"CC", "GC", "RC", "PC", "TC", "AC"}  # preserve common club types


def _strip_trailing_suffix_tokens(tokens: list[str]) -> list[str]:
    """Remove trailing tokens that are likely suffixes or noise."""
    if not tokens:
        return tokens
    
    # Keep the last token if it's a common club suffix
    if tokens[-1] in _KEEP_SUFFIXES:
        return tokens
    
    # Remove trailing tokens that look like suffixes
    while tokens and (
        _ALNUM_SUFFIX_RE.match(tokens[-1]) or
        _LETTER_PAREN_RE.match(tokens[-1]) or
        _ALLCAP_SHORT_RE.match(tokens[-1]) or
        tokens[-1].lower() in {'club', 'country', 'golf', 'tennis', 'racquet', 'sports'}
    ):
        tokens.pop()
    
    return tokens


def _expand_club_abbreviation(abbrev: str) -> str:
    """Expand common club abbreviations."""
    expansions = {
        'CC': 'Country Club',
        'GC': 'Golf Club', 
        'RC': 'Racquet Club',
        'PC': 'Paddle Club',
        'TC': 'Tennis Club',
        'AC': 'Athletic Club',
        'GC': 'Golf Club'
    }
    
    return expansions.get(abbrev, abbrev)


def normalize_club_name(name: str) -> str:
    """
    Normalize club name for consistent matching.
    Handles common variations and abbreviations.
    """
    if not name:
        return ""
    
    # Convert to uppercase for consistency
    normalized = name.upper().strip()
    
    # Remove extra whitespace
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Split into tokens
    tokens = normalized.split()
    
    # Remove trailing suffix tokens
    tokens = _strip_trailing_suffix_tokens(tokens)
    
    # Expand abbreviations
    expanded_tokens = []
    for token in tokens:
        expanded = _expand_club_abbreviation(token)
        expanded_tokens.append(expanded)
    
    # Join back together
    result = ' '.join(expanded_tokens)
    
    # Clean up any double spaces
    result = re.sub(r'\s+', ' ', result).strip()
    
    return result


def load_club_addresses(csv_file: str) -> Dict[str, str]:
    """
    Load club addresses from CSV file and return a mapping of club names to addresses.
    Uses fuzzy matching to handle variations in club names.
    """
    if not os.path.exists(csv_file):
        print(f"⚠️  Club addresses CSV file not found: {csv_file}")
        return {}
    
    addresses = {}
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                raw_name = row.get('Raw Name', '').strip()
                full_name = row.get('Full Name', '').strip()
                address = row.get('Address', '').strip()
                
                # Use raw name if available, otherwise use full name
                club_name = raw_name if raw_name else full_name
                
                if club_name and address:
                    # Normalize the club name for matching
                    normalized_name = normalize_club_name(club_name)
                    addresses[normalized_name] = address
                    
                    # Also store the original name for exact matches
                    addresses[club_name] = address
        
        print(f"📊 Loaded {len(addresses)} club addresses from CSV")
        return addresses
        
    except Exception as e:
        print(f"❌ Error loading club addresses from CSV: {e}")
        return {}


def find_club_address(club_name: str, addresses: Dict[str, str]) -> Optional[str]:
    """
    Find the address for a club using fuzzy matching.
    Returns the address if found, None otherwise.
    """
    if not club_name or not addresses:
        return None
    
    # Try exact match first
    if club_name in addresses:
        return addresses[club_name]
    
    # Try normalized match
    normalized_name = normalize_club_name(club_name)
    if normalized_name in addresses:
        return addresses[normalized_name]
    
    # Try fuzzy matching
    best_match = None
    best_score = 0.0
    
    for csv_name, address in addresses.items():
        # Calculate similarity score
        score = SequenceMatcher(None, club_name.lower(), csv_name.lower()).ratio()
        
        if score > best_score and score > 0.6:  # 60% similarity threshold
            best_score = score
            best_match = address
    
    if best_match:
        print(f"    🔍 Fuzzy match found: {club_name} -> {best_match[:50]}... (score: {best_score:.2f})")
    
    return best_match


def update_existing_clubs_with_addresses(addresses: Dict[str, str], dry_run: bool = False) -> int:
    """
    Update existing clubs in the database with addresses from CSV file.
    
    Args:
        addresses: Dictionary of club names to addresses from CSV
        dry_run: If True, only show what would be updated without making changes
        
    Returns:
        Number of clubs updated with addresses
    """
    if not addresses:
        print("⚠️  No addresses loaded from CSV")
        return 0
    
    print("\n🔄 Updating existing clubs with addresses...")
    
    # Get all clubs without addresses
    clubs_without_addresses = execute_query("""
        SELECT id, name 
        FROM clubs 
        WHERE club_address IS NULL OR club_address = ''
        ORDER BY name
    """)
    
    if not clubs_without_addresses:
        print("  ✅ All clubs already have addresses")
        return 0
    
    print(f"  📊 Found {len(clubs_without_addresses)} clubs without addresses")
    
    updated_count = 0
    
    for club in clubs_without_addresses:
        club_id = club['id']
        club_name = club['name']
        
        # Try to find address using enhanced normalization
        address = find_club_address(club_name, addresses)
        
        if address:
            if dry_run:
                print(f"    🔍 DRY RUN: Would update {club_name} -> {address[:60]}...")
                updated_count += 1
            else:
                # Update the club with the address
                try:
                    success = execute_update("""
                        UPDATE clubs 
                        SET club_address = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (address, club_id))
                    
                    if success:
                        normalized_name = normalize_club_name(club_name)
                        print(f"    ✅ Updated: {club_name} -> {normalized_name} -> {address[:60]}...")
                        updated_count += 1
                    else:
                        print(f"    ❌ Failed to update {club_name}")
                except Exception as e:
                    print(f"    ❌ Error updating {club_name}: {e}")
        else:
            print(f"    ⚠️  No address found for {club_name}")
    
    if not dry_run:
        print(f"  🎉 Updated {updated_count} existing clubs with addresses")
    else:
        print(f"  🔍 DRY RUN: Would update {updated_count} clubs with addresses")
    
    return updated_count


def show_current_status():
    """Show current status of club addresses in the database."""
    print("\n📊 CURRENT CLUB ADDRESS STATUS")
    print("=" * 50)
    
    # Get counts
    total_clubs = execute_query("SELECT COUNT(*) as count FROM clubs")[0]['count']
    clubs_with_addresses = execute_query("""
        SELECT COUNT(*) as count 
        FROM clubs 
        WHERE club_address IS NOT NULL AND club_address != ''
    """)[0]['count']
    clubs_without_addresses = total_clubs - clubs_with_addresses
    
    print(f"Total clubs: {total_clubs}")
    print(f"Clubs with addresses: {clubs_with_addresses}")
    print(f"Clubs without addresses: {clubs_without_addresses}")
    
    # Show some examples
    if clubs_with_addresses > 0:
        print(f"\n✅ Sample clubs WITH addresses:")
        sample_with = execute_query("""
            SELECT name, club_address 
            FROM clubs 
            WHERE club_address IS NOT NULL AND club_address != ''
            ORDER BY name 
            LIMIT 5
        """)
        for club in sample_with:
            print(f"  • {club['name']}: {club['club_address'][:50]}...")
    
    if clubs_without_addresses > 0:
        print(f"\n❌ Sample clubs WITHOUT addresses:")
        sample_without = execute_query("""
            SELECT name 
            FROM clubs 
            WHERE club_address IS NULL OR club_address = ''
            ORDER BY name 
            LIMIT 10
        """)
        for club in sample_without:
            print(f"  • {club['name']}")


def main():
    """Main function to load club addresses from CSV."""
    parser = argparse.ArgumentParser(description="Load club addresses from CSV file")
    parser.add_argument("--csv-file", default="data/OLD-club_addresses.csv", 
                       help="Path to CSV file with club addresses (default: data/OLD-club_addresses.csv)")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be updated without making changes")
    args = parser.parse_args()
    
    print("🏓 RALLY CLUB ADDRESS LOADER")
    print("=" * 50)
    print(f"CSV file: {args.csv_file}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE UPDATE'}")
    
    # Show current status
    show_current_status()
    
    # Load addresses from CSV
    print(f"\n📖 Loading addresses from {args.csv_file}...")
    addresses = load_club_addresses(args.csv_file)
    
    if not addresses:
        print("❌ No addresses loaded. Exiting.")
        return
    
    # Update clubs with addresses
    updated_count = update_existing_clubs_with_addresses(addresses, args.dry_run)
    
    # Show final status
    if not args.dry_run:
        print("\n📊 FINAL STATUS")
        print("=" * 30)
        show_current_status()
    
    print(f"\n✅ Address loading completed!")
    if args.dry_run:
        print("💡 Run without --dry-run to apply changes")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)
