#!/usr/bin/env python3
"""
Club Address Update Script with Fuzzy Logic Matching

This script updates the clubs table using fuzzy logic to match club names
from data/club_addresses.csv with existing club names in the database.
It handles variations in naming and provides detailed reporting.

Usage:
    python scripts/update_club_addresses_fuzzy.py [--dry-run] [--verbose]
"""

import csv
import os
import sys
import argparse
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from difflib import SequenceMatcher

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_db
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class ClubMatch:
    """Represents a potential match between CSV and database club"""
    csv_name: str
    db_name: str
    db_id: int
    address: str
    similarity_score: float
    match_type: str
    current_address: Optional[str] = None


class FuzzyClubMatcher:
    """Handles fuzzy matching between CSV club names and database club names"""
    
    def __init__(self, similarity_threshold: float = 0.6):
        self.similarity_threshold = similarity_threshold
        
    def normalize_name(self, name: str) -> str:
        """Normalize club name for better matching"""
        if not name:
            return ""
        
        # Convert to lowercase and strip whitespace
        normalized = name.lower().strip()
        
        # Remove common suffixes that might vary
        suffixes_to_remove = [
            'country club', 'counrty club', 'cc', 'club',
            'tennis club', 'racquet club', 'sports club'
        ]
        
        for suffix in suffixes_to_remove:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)].strip()
                break
                
        # Remove common prefixes
        prefixes_to_remove = ['the ']
        for prefix in prefixes_to_remove:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):].strip()
                break
                
        return normalized
    
    def calculate_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two club names"""
        if not name1 or not name2:
            return 0.0
            
        # Direct similarity
        direct_sim = SequenceMatcher(None, name1.lower(), name2.lower()).ratio()
        
        # Normalized similarity
        norm1 = self.normalize_name(name1)
        norm2 = self.normalize_name(name2)
        normalized_sim = SequenceMatcher(None, norm1, norm2).ratio()
        
        # Return the higher of the two scores
        return max(direct_sim, normalized_sim)
    
    def find_best_matches(self, csv_clubs: List[Dict], db_clubs: List[Dict]) -> List[ClubMatch]:
        """Find the best matches between CSV and database clubs"""
        matches = []
        
        for csv_club in csv_clubs:
            csv_name = csv_club['name']
            csv_address = csv_club['address']
            
            if not csv_name or not csv_address:
                continue
                
            best_match = None
            best_score = 0.0
            
            for db_club in db_clubs:
                db_name = db_club['name']
                db_id = db_club['id']
                current_address = db_club.get('club_address')
                
                # Calculate similarity
                similarity = self.calculate_similarity(csv_name, db_name)
                
                if similarity > best_score and similarity >= self.similarity_threshold:
                    best_score = similarity
                    best_match = ClubMatch(
                        csv_name=csv_name,
                        db_name=db_name,
                        db_id=db_id,
                        address=csv_address,
                        similarity_score=similarity,
                        match_type=self._determine_match_type(similarity),
                        current_address=current_address
                    )
            
            if best_match:
                matches.append(best_match)
            else:
                # Log unmatched CSV clubs
                print(f"⚠️  No match found for CSV club: '{csv_name}'")
        
        return matches
    
    def _determine_match_type(self, similarity: float) -> str:
        """Determine the type of match based on similarity score"""
        if similarity >= 0.9:
            return "exact"
        elif similarity >= 0.8:
            return "high_confidence"
        elif similarity >= 0.7:
            return "medium_confidence"
        else:
            return "low_confidence"


class ClubAddressUpdater:
    """Main class for updating club addresses in the database"""
    
    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.matcher = FuzzyClubMatcher()
        
    def load_csv_data(self, csv_file: str) -> List[Dict]:
        """Load club data from CSV file"""
        clubs = []
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    # Clean up the data
                    club = {
                        'name': row.get('Raw Name', '').strip(),
                        'full_name': row.get('Full Name', '').strip(),
                        'address': row.get('Address', '').strip()
                    }
                    
                    # Use full name if raw name is empty
                    if not club['name'] and club['full_name']:
                        club['name'] = club['full_name']
                    
                    if club['name'] and club['address']:
                        clubs.append(club)
                        
        except FileNotFoundError:
            print(f"❌ Error: CSV file '{csv_file}' not found")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error reading CSV file: {e}")
            sys.exit(1)
            
        print(f"📊 Loaded {len(clubs)} clubs from CSV")
        return clubs
    
    def load_database_clubs(self) -> List[Dict]:
        """Load all clubs from the database"""
        try:
            with get_db() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, name, club_address 
                        FROM clubs 
                        ORDER BY name
                    """)
                    
                    clubs = []
                    for row in cursor.fetchall():
                        clubs.append({
                            'id': row[0],
                            'name': row[1],
                            'club_address': row[2]
                        })
                        
        except Exception as e:
            print(f"❌ Error loading clubs from database: {e}")
            sys.exit(1)
            
        print(f"📊 Loaded {len(clubs)} clubs from database")
        return clubs
    
    def analyze_address_duplicates(self, matches: List[ClubMatch]) -> Dict[str, List[ClubMatch]]:
        """Analyze which addresses are shared by multiple clubs"""
        address_groups = {}
        
        for match in matches:
            address = match.address
            if address not in address_groups:
                address_groups[address] = []
            address_groups[address].append(match)
            
        # Filter to only addresses with multiple clubs
        duplicates = {addr: clubs for addr, clubs in address_groups.items() if len(clubs) > 1}
        
        return duplicates
    
    def update_club_address(self, club_id: int, address: str) -> bool:
        """Update a single club's address in the database"""
        try:
            with get_db() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE clubs 
                        SET club_address = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (address, club_id))
                    
                    if cursor.rowcount > 0:
                        conn.commit()
                        return True
                    else:
                        print(f"⚠️  No rows updated for club ID {club_id}")
                        return False
                        
        except Exception as e:
            print(f"❌ Error updating club ID {club_id}: {e}")
            return False
    
    def process_updates(self, matches: List[ClubMatch]) -> Dict[str, int]:
        """Process all club address updates"""
        stats = {
            'updated': 0,
            'skipped': 0,
            'errors': 0,
            'already_updated': 0
        }
        
        print(f"\n🔄 Processing {len(matches)} potential updates...")
        
        for match in matches:
            # Check if address is already the same
            if match.current_address and match.current_address.strip() == match.address.strip():
                print(f"⏭️  Skipping '{match.db_name}' - address already matches")
                stats['already_updated'] += 1
                continue
            
            # Skip low confidence matches unless forced
            if match.match_type == "low_confidence":
                print(f"⚠️  Skipping low confidence match: '{match.csv_name}' -> '{match.db_name}' (score: {match.similarity_score:.2f})")
                stats['skipped'] += 1
                continue
            
            if self.verbose:
                print(f"📝 {'[DRY RUN] ' if self.dry_run else ''}Updating '{match.db_name}' (ID: {match.db_id})")
                print(f"   Match: '{match.csv_name}' -> '{match.db_name}' (score: {match.similarity_score:.2f}, type: {match.match_type})")
                if match.current_address:
                    print(f"   Current: {match.current_address}")
                print(f"   New:     {match.address}")
            
            if not self.dry_run:
                if self.update_club_address(match.db_id, match.address):
                    stats['updated'] += 1
                    print(f"✅ Updated '{match.db_name}'")
                else:
                    stats['errors'] += 1
                    print(f"❌ Failed to update '{match.db_name}'")
            else:
                stats['updated'] += 1
                print(f"✅ [DRY RUN] Would update '{match.db_name}'")
        
        return stats
    
    def print_summary(self, matches: List[ClubMatch], stats: Dict[str, int], duplicates: Dict[str, List[ClubMatch]]):
        """Print a comprehensive summary of the update process"""
        print("\n" + "="*80)
        print("📊 CLUB ADDRESS UPDATE SUMMARY")
        print("="*80)
        
        # Statistics
        print(f"\n📈 Update Statistics:")
        print(f"   • Total matches found: {len(matches)}")
        print(f"   • Successfully updated: {stats['updated']}")
        print(f"   • Already up to date: {stats['already_updated']}")
        print(f"   • Skipped (low confidence): {stats['skipped']}")
        print(f"   • Errors: {stats['errors']}")
        
        # Match type breakdown
        match_types = {}
        for match in matches:
            match_type = match.match_type
            match_types[match_type] = match_types.get(match_type, 0) + 1
        
        print(f"\n🎯 Match Quality Breakdown:")
        for match_type, count in sorted(match_types.items()):
            print(f"   • {match_type.replace('_', ' ').title()}: {count}")
        
        # Duplicate addresses
        if duplicates:
            print(f"\n🏢 Clubs with Shared Addresses ({len(duplicates)} addresses):")
            for address, clubs in duplicates.items():
                print(f"\n   📍 {address}")
                for club in clubs:
                    print(f"      • {club.db_name} (ID: {club.db_id})")
        
        # High confidence matches
        high_conf_matches = [m for m in matches if m.match_type in ['exact', 'high_confidence']]
        if high_conf_matches:
            print(f"\n✅ High Confidence Matches ({len(high_conf_matches)}):")
            for match in high_conf_matches:
                print(f"   • {match.csv_name} -> {match.db_name} (score: {match.similarity_score:.2f})")
        
        # Medium confidence matches
        med_conf_matches = [m for m in matches if m.match_type == 'medium_confidence']
        if med_conf_matches:
            print(f"\n⚠️  Medium Confidence Matches ({len(med_conf_matches)}):")
            for match in med_conf_matches:
                print(f"   • {match.csv_name} -> {match.db_name} (score: {match.similarity_score:.2f})")
    
    def run(self, csv_file: str = "data/club_addresses.csv"):
        """Main execution method"""
        print("🏢 Club Address Update Script with Fuzzy Logic")
        print("=" * 50)
        
        if self.dry_run:
            print("🔍 Running in DRY RUN mode - no changes will be made")
        
        # Load data
        csv_clubs = self.load_csv_data(csv_file)
        db_clubs = self.load_database_clubs()
        
        if not csv_clubs:
            print("❌ No clubs found in CSV file")
            return
        
        if not db_clubs:
            print("❌ No clubs found in database")
            return
        
        # Find matches
        print("\n🔍 Finding fuzzy matches...")
        matches = self.matcher.find_best_matches(csv_clubs, db_clubs)
        
        if not matches:
            print("❌ No matches found between CSV and database clubs")
            return
        
        print(f"✅ Found {len(matches)} potential matches")
        
        # Analyze duplicates
        duplicates = self.analyze_address_duplicates(matches)
        
        # Process updates
        stats = self.process_updates(matches)
        
        # Print summary
        self.print_summary(matches, stats, duplicates)
        
        if self.dry_run:
            print(f"\n💡 To apply these changes, run without --dry-run flag")
        else:
            print(f"\n🎉 Update process completed!")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Update club addresses using fuzzy logic matching")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be updated without making changes")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Show detailed information about each update")
    parser.add_argument("--csv-file", default="data/club_addresses.csv",
                       help="Path to the CSV file with club addresses")
    
    args = parser.parse_args()
    
    # Validate CSV file exists
    if not os.path.exists(args.csv_file):
        print(f"❌ Error: CSV file '{args.csv_file}' not found")
        sys.exit(1)
    
    # Run the updater
    updater = ClubAddressUpdater(dry_run=args.dry_run, verbose=args.verbose)
    updater.run(args.csv_file)


if __name__ == "__main__":
    main()
