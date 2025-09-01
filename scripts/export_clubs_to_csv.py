#!/usr/bin/env python3
"""
Export Clubs to CSV
Exports all clubs from the clubs table to a CSV file for analysis or reporting.
"""

import csv
import logging
import os
import sys
from datetime import datetime

# Add the parent directory to the path so we can import from the project
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def export_clubs_to_csv(output_file="clubs_export.csv"):
    """
    Export all clubs from the database to a CSV file.
    
    Args:
        output_file (str): Name of the output CSV file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Starting clubs export to {output_file}")
        
        # Connect to database
        with get_db() as conn:
            with conn.cursor() as cursor:
                # Query all clubs with their details
                query = """
                SELECT 
                    id,
                    name,
                    club_address,
                    logo_filename,
                    updated_at
                FROM clubs 
                ORDER BY name
                """
                
                cursor.execute(query)
                clubs = cursor.fetchall()
                
                logger.info(f"Found {len(clubs)} clubs in database")
                
                # Write to CSV
                with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['id', 'name', 'club_address', 'logo_filename', 'updated_at']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    # Write header
                    writer.writeheader()
                    
                    # Write data
                    for club in clubs:
                        writer.writerow({
                            'id': club[0],
                            'name': club[1],
                            'club_address': club[2] or '',
                            'logo_filename': club[3] or '',
                            'updated_at': club[4].isoformat() if club[4] else ''
                        })
                
                logger.info(f"Successfully exported {len(clubs)} clubs to {output_file}")
                return True
                
    except Exception as e:
        logger.error(f"Error exporting clubs: {str(e)}")
        return False


def export_clubs_names_only(output_file="clubs_names_only.csv"):
    """
    Export only club names to a simple CSV file.
    
    Args:
        output_file (str): Name of the output CSV file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Starting clubs names export to {output_file}")
        
        # Connect to database
        with get_db() as conn:
            with conn.cursor() as cursor:
                # Query only club names
                query = "SELECT name FROM clubs ORDER BY name"
                cursor.execute(query)
                clubs = cursor.fetchall()
                
                logger.info(f"Found {len(clubs)} clubs in database")
                
                # Write to CSV
                with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    
                    # Write header
                    writer.writerow(['club_name'])
                    
                    # Write data
                    for club in clubs:
                        writer.writerow([club[0]])
                
                logger.info(f"Successfully exported {len(clubs)} club names to {output_file}")
                return True
                
    except Exception as e:
        logger.error(f"Error exporting club names: {str(e)}")
        return False


def main():
    """Main function to run the export"""
    print("🏓 Rally Clubs Export Tool")
    print("=" * 40)
    
    # Create timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    full_export_file = f"clubs_full_export_{timestamp}.csv"
    names_only_file = f"clubs_names_only_{timestamp}.csv"
    
    print(f"📊 Exporting clubs to CSV files...")
    print(f"   Full export: {full_export_file}")
    print(f"   Names only: {names_only_file}")
    print()
    
    # Export full clubs data
    if export_clubs_to_csv(full_export_file):
        print(f"✅ Full clubs export successful: {full_export_file}")
    else:
        print(f"❌ Full clubs export failed")
    
    # Export names only
    if export_clubs_names_only(names_only_file):
        print(f"✅ Club names export successful: {names_only_file}")
    else:
        print(f"❌ Club names export failed")
    
    print()
    print("📁 Files created in current directory")
    print("💡 Use the names-only file for simple club name lists")
    print("💡 Use the full export for complete club information")


if __name__ == "__main__":
    main()
