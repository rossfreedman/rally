#!/usr/bin/env python3
"""
Script to update the clubs table with addresses from the updated club_addresses.csv file.
This script reads the CSV file and updates the database clubs table with the correct addresses.
"""

import os
import sys
import pandas as pd
import logging

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from database_utils import execute_query, execute_update

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ClubTableUpdater:
    def __init__(self, csv_file=None):
        if csv_file is None:
            # Get the project root directory
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            self.csv_file = os.path.join(project_root, 'data', 'club_addresses.csv')
        else:
            self.csv_file = csv_file
        
    def load_csv_data(self):
        """Load club addresses from CSV file."""
        try:
            df = pd.read_csv(self.csv_file)
            logger.info(f"Loaded {len(df)} records from CSV file")
            return df
        except Exception as e:
            logger.error(f"Error loading CSV file: {e}")
            return None
    
    def load_database_clubs(self):
        """Load all clubs from the database."""
        try:
            clubs = execute_query("""
                SELECT id, name, club_address 
                FROM clubs 
                ORDER BY name
            """)
            logger.info(f"Loaded {len(clubs)} clubs from database")
            return clubs
        except Exception as e:
            logger.error(f"Error loading clubs from database: {e}")
            return None
    
    def normalize_club_name(self, name):
        """Normalize club names for matching."""
        if not name or pd.isna(name):
            return ""
        
        name = str(name).strip()
        # Remove common suffixes
        name = name.replace(' Country Club', '').replace(' CC', '').replace(' Club', '')
        # Normalize whitespace
        name = ' '.join(name.split())
        return name.lower()
    
    def find_matching_club(self, csv_name, database_clubs):
        """Find the best matching club in the database."""
        csv_normalized = self.normalize_club_name(csv_name)
        
        best_match = None
        best_score = 0
        
        for club in database_clubs:
            db_name = club['name']
            db_normalized = self.normalize_club_name(db_name)
            
            # Exact match
            if csv_normalized == db_normalized:
                return club
            
            # Check if one contains the other
            if csv_normalized in db_normalized or db_normalized in csv_normalized:
                score = min(len(csv_normalized), len(db_normalized)) / max(len(csv_normalized), len(db_normalized))
                if score > best_score:
                    best_score = score
                    best_match = club
        
        return best_match if best_score > 0.7 else None
    
    def update_club_address(self, club_id, address):
        """Update a single club's address in the database."""
        try:
            success = execute_update(
                "UPDATE clubs SET club_address = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (address, club_id)
            )
            return success
        except Exception as e:
            logger.error(f"Error updating club ID {club_id}: {e}")
            return False
    
    def process_updates(self):
        """Process all club address updates from CSV to database."""
        logger.info("Starting club address update process...")
        
        # Load data
        csv_df = self.load_csv_data()
        if csv_df is None:
            return
        
        database_clubs = self.load_database_clubs()
        if database_clubs is None:
            return
        
        # Track results
        updates_made = []
        not_found = []
        no_changes = []
        
        # Process each CSV record
        for index, row in csv_df.iterrows():
            csv_name = row['Raw Name']
            csv_address = row['Address']
            
            if pd.isna(csv_name) or not csv_name.strip():
                continue
            
            # Find matching club in database
            matching_club = self.find_matching_club(csv_name, database_clubs)
            
            if matching_club:
                club_id = matching_club['id']
                club_name = matching_club['name']
                current_address = matching_club['club_address']
                
                # Check if address needs updating
                if str(current_address) != str(csv_address):
                    # Update the address
                    if self.update_club_address(club_id, csv_address):
                        updates_made.append({
                            'club_name': club_name,
                            'club_id': club_id,
                            'old_address': current_address,
                            'new_address': csv_address
                        })
                        logger.info(f"Updated {club_name} (ID: {club_id}): '{current_address}' -> '{csv_address}'")
                    else:
                        logger.error(f"Failed to update {club_name} (ID: {club_id})")
                else:
                    no_changes.append({
                        'club_name': club_name,
                        'address': csv_address
                    })
            else:
                not_found.append({
                    'csv_name': csv_name,
                    'address': csv_address
                })
                logger.warning(f"No matching club found for CSV entry: {csv_name}")
        
        # Print summary
        self.print_summary(updates_made, not_found, no_changes)
        
        return {
            'updates_made': updates_made,
            'not_found': not_found,
            'no_changes': no_changes
        }
    
    def print_summary(self, updates_made, not_found, no_changes):
        """Print a summary of the update process."""
        print("\n" + "="*60)
        print("📊 CLUB ADDRESS UPDATE SUMMARY")
        print("="*60)
        print(f"✅ Successfully updated: {len(updates_made)}")
        print(f"⚠️  No changes needed: {len(no_changes)}")
        print(f"❌ Not found in database: {len(not_found)}")
        print(f"📝 Total CSV records processed: {len(updates_made) + len(no_changes) + len(not_found)}")
        
        if updates_made:
            print(f"\n🔄 UPDATES MADE:")
            for update in updates_made:
                print(f"  • {update['club_name']} (ID: {update['club_id']})")
                print(f"    Old: {update['old_address']}")
                print(f"    New: {update['new_address']}")
                print()
        
        if not_found:
            print(f"\n⚠️  NOT FOUND IN DATABASE:")
            for nf in not_found:
                print(f"  • {nf['csv_name']}: {nf['address']}")
        
        if no_changes:
            print(f"\n✅ NO CHANGES NEEDED (already up-to-date):")
            for nc in no_changes[:10]:  # Show first 10
                print(f"  • {nc['club_name']}: {nc['address']}")
            if len(no_changes) > 10:
                print(f"  ... and {len(no_changes) - 10} more")

def main():
    """Main function."""
    print("🏓 CLUB ADDRESS DATABASE UPDATE UTILITY")
    print("="*60)
    print("🔄 Updating clubs table with addresses from CSV file...")
    print()
    
    updater = ClubTableUpdater()
    results = updater.process_updates()
    
    if results and results['updates_made']:
        print(f"\n✅ Successfully updated {len(results['updates_made'])} club addresses in the database!")
    else:
        print(f"\n✅ No updates needed - all club addresses are already up-to-date!")

if __name__ == "__main__":
    main()
