#!/usr/bin/env python3
"""
Clean APTA CSV file by removing HTML entities and extra spaces
"""

import csv
import re
import sys

def clean_csv(input_file, output_file):
    """Clean the CSV file by removing HTML entities and extra spaces."""
    
    with open(input_file, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        
        with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
            fieldnames = ['First Name', 'Last Name', 'Email', 'Phone', 'Player ID']
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for row in reader:
                # Clean first name
                first_name = row['First Name'].replace('&nbsp;', '').strip()
                
                # Clean last name
                last_name = row['Last Name'].replace('&nbsp;', '').strip()
                
                # Clean email
                email = row['Email'].strip()
                
                # Clean phone
                phone = row['Phone'].strip()
                
                # Generate clean player ID
                if first_name and last_name:
                    clean_first = re.sub(r'[^A-Za-z]', '', first_name)
                    clean_last = re.sub(r'[^A-Za-z]', '', last_name)
                    player_id = f"nndz-{clean_first.upper()}{clean_last.upper()}"
                else:
                    player_id = row['Player ID']
                
                writer.writerow({
                    'First Name': first_name,
                    'Last Name': last_name,
                    'Email': email,
                    'Phone': phone,
                    'Player ID': player_id
                })

if __name__ == "__main__":
    input_file = "apta_directory_complete.csv"
    output_file = "apta_directory_clean.csv"
    
    clean_csv(input_file, output_file)
    print(f"✅ Cleaned CSV saved to {output_file}")


