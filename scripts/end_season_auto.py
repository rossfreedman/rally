#!/usr/bin/env python3
"""
Auto-confirm end season script
"""

import subprocess
import sys

def main():
    # Run end_season.py with auto-confirmation
    process = subprocess.Popen(
        ['python3', 'data/etl/import/end_season.py', 'APTA_CHICAGO'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Send 'YES' and 'CONFIRM' to confirm
    stdout, stderr = process.communicate(input='YES\nCONFIRM\n')
    
    print(stdout)
    if stderr:
        print("STDERR:", stderr)
    
    return process.returncode

if __name__ == "__main__":
    sys.exit(main())
