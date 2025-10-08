#!/usr/bin/env python3

"""
Wrapper script to load club addresses from CSV.
This script calls the main address loading script in data/etl/import/
"""

import subprocess
import sys
import os

def main():
    """Call the main address loading script with all arguments passed through."""
    
    # Get the path to the main script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(script_dir, '..', 'data', 'etl', 'import', 'load_club_addresses_from_csv.py')
    
    # Pass all arguments to the main script
    cmd = [sys.executable, main_script] + sys.argv[1:]
    
    # Run the main script
    result = subprocess.run(cmd)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
