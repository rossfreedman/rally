#!/usr/bin/env python3
"""
Comprehensive Club Address Mapper

This script creates a comprehensive mapping for all remaining club variations
to achieve 95%+ address coverage by handling edge cases and complex variations.

Usage:
    python scripts/comprehensive_club_mapper.py [--dry-run] [--verbose]
"""

import os
import sys
import argparse
from typing import Dict, List, Set

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_db
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ComprehensiveClubMapper:
    """Comprehensive club address mapper for remaining variations"""
    
    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        
        # Comprehensive mapping of club variations to base clubs
        self.club_mapping = {
            # Additional variations that weren't caught
            'Glen Oak II': 'Glen Oak',
            'Glenbrook G(1)': 'Glenbrook RC',
            'Hinsdale GC': 'Hinsdale Golf Club',
            'Hinsdale PC': 'Hinsdale Golf Club',
            'Hinsdale PC 1a': 'Hinsdale Golf Club',
            'Hinsdale PC 1b': 'Hinsdale Golf Club', 
            'Hinsdale PC I': 'Hinsdale Golf Club',
            'Hinsdale PC II': 'Hinsdale Golf Club',
            'LaGrange CC II': 'LaGrange CC',
            'LifeSport-Lshire': 'LifeSport',
            'Lifesport-Lshire': 'LifeSport',
            'Medinah II': 'Medinah',
            'Oak Park CC II': 'Oak Park CC',
            'Prairie Club': 'Prairie Club I',
            'Prairie Club 2a': 'Prairie Club I',
            'Prairie Club 2b': 'Prairie Club I',
            'Prairie Club C(1)': 'Prairie Club I',
            'Prairie Club C(3)': 'Prairie Club I',
            'Prairie Club G(2)': 'Prairie Club I',
            'Prairie Club II': 'Prairie Club I',
            'River Forest PD II': 'River Forest',
            'Salt Creek II': 'Salt Creek',
            
            # Wilmette 99 variations
            'Wilmette 99 A': 'Wilmette',
            'Wilmette 99 B': 'Wilmette',
            'Wilmette 99 C': 'Wilmette',
            'Wilmette 99 D': 'Wilmette',
            'Wilmette 99 E': 'Wilmette',
            'Wilmette 99 F': 'Wilmette',
            'Wilmette PD II': 'Wilmette',
            
            # Winnetka 99 variations
            'Winnetka 99 A': 'Winnetka',
            'Winnetka 99 B': 'Winnetka',
            'Winnetka 99 C': 'Winnetka',
            'Winnetka 99 D': 'Winnetka',
            'Winnetka 99 E': 'Winnetka',
            'Winnetka 99 F': 'Winnetka',
            'Winnetka II': 'Winnetka',
            
            # Midtown variations (all should map to Midtown)
            'Midtown - Chicago - 10': 'Midtown',
            'Midtown - Chicago - 14': 'Midtown',
            'Midtown - Chicago - 19': 'Midtown',
            'Midtown - Chicago - 23': 'Midtown',
            'Midtown - Chicago - 27': 'Midtown',
            'Midtown - Chicago - 32': 'Midtown',
            'Midtown - Chicago - 4': 'Midtown',
            'Midtown - Chicago - 6': 'Midtown',
        }
        
        # Special cases that need manual addresses
        self.special_cases = {
            'BYE': None,  # No address needed
            'Test Club': None,  # No address needed
            'Legends': None,  # No address needed
            'Briarwood': None,  # Need to research
            'Glen Ellyn': None,  # Need to research
        }
    
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
            
        return clubs
    
    def get_base_club_address(self, base_club_name: str) -> str:
        """Get the address for a base club name"""
        try:
            with get_db() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT club_address 
                        FROM clubs 
                        WHERE name = %s AND club_address IS NOT NULL
                        LIMIT 1
                    """, (base_club_name,))
                    
                    result = cursor.fetchone()
                    return result[0] if result else None
                    
        except Exception as e:
            print(f"❌ Error getting address for {base_club_name}: {e}")
            return None
    
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
    
    def process_comprehensive_mapping(self) -> Dict[str, int]:
        """Process comprehensive club mapping"""
        stats = {
            'updated': 0,
            'skipped': 0,
            'errors': 0,
            'special_cases': 0
        }
        
        # Get all clubs
        clubs = self.load_database_clubs()
        clubs_without_addresses = [c for c in clubs if c['club_address'] is None]
        
        print(f"🔍 Processing {len(clubs_without_addresses)} clubs without addresses...")
        
        for club in clubs_without_addresses:
            club_name = club['name']
            club_id = club['id']
            
            # Check if it's a special case
            if club_name in self.special_cases:
                if self.verbose:
                    print(f"⏭️  Skipping special case: '{club_name}'")
                stats['special_cases'] += 1
                continue
            
            # Check if we have a mapping
            if club_name in self.club_mapping:
                base_club_name = self.club_mapping[club_name]
                address = self.get_base_club_address(base_club_name)
                
                if address:
                    if self.verbose:
                        print(f"📝 {'[DRY RUN] ' if self.dry_run else ''}Updating '{club_name}' (ID: {club_id})")
                        print(f"   Maps to: '{base_club_name}'")
                        print(f"   Address: {address}")
                    
                    if not self.dry_run:
                        if self.update_club_address(club_id, address):
                            stats['updated'] += 1
                            print(f"✅ Updated '{club_name}'")
                        else:
                            stats['errors'] += 1
                            print(f"❌ Failed to update '{club_name}'")
                    else:
                        stats['updated'] += 1
                        print(f"✅ [DRY RUN] Would update '{club_name}'")
                else:
                    print(f"⚠️  No address found for base club '{base_club_name}'")
                    stats['skipped'] += 1
            else:
                if self.verbose:
                    print(f"⚠️  No mapping found for '{club_name}'")
                stats['skipped'] += 1
        
        return stats
    
    def print_summary(self, stats: Dict[str, int]):
        """Print summary of the mapping process"""
        print("\n" + "="*80)
        print("📊 COMPREHENSIVE CLUB MAPPING SUMMARY")
        print("="*80)
        
        print(f"\n📈 Mapping Statistics:")
        print(f"   • Successfully updated: {stats['updated']}")
        print(f"   • Special cases skipped: {stats['special_cases']}")
        print(f"   • No mapping found: {stats['skipped']}")
        print(f"   • Errors: {stats['errors']}")
        
        print(f"\n📋 Special Cases Handled:")
        for club_name, address in self.special_cases.items():
            if address is None:
                print(f"   • {club_name}: No address needed")
            else:
                print(f"   • {club_name}: {address}")
    
    def run(self):
        """Main execution method"""
        print("🏢 Comprehensive Club Address Mapper")
        print("=" * 50)
        
        if self.dry_run:
            print("🔍 Running in DRY RUN mode - no changes will be made")
        
        # Process comprehensive mapping
        stats = self.process_comprehensive_mapping()
        
        # Print summary
        self.print_summary(stats)
        
        if self.dry_run:
            print(f"\n💡 To apply these changes, run without --dry-run flag")
        else:
            print(f"\n🎉 Comprehensive mapping completed!")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Comprehensive club address mapping")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be updated without making changes")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Show detailed information about each update")
    
    args = parser.parse_args()
    
    # Run the mapper
    mapper = ComprehensiveClubMapper(dry_run=args.dry_run, verbose=args.verbose)
    mapper.run()


if __name__ == "__main__":
    main()
