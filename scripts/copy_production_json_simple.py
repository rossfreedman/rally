#!/usr/bin/env python3
"""
Simple script to copy production JSON files using Railway CLI

This creates a temporary Python script on production that reads and outputs files,
then executes it via Railway.
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Main function"""
    print("=" * 80)
    print("📋 Copying JSON Files from Production")
    print("=" * 80)
    print()
    print("Since Railway has multiple services, we'll use SSH directly.")
    print()
    print("Please run these commands manually:")
    print()
    print("1. SSH into production:")
    print("   railway ssh")
    print()
    print("2. Once connected, run these commands:")
    print()
    
    # CNSWPL files
    print("   # CNSWPL files")
    print("   cat /app/data/leagues/CNSWPL/series_stats.json")
    print("   # Copy the output above and save to: data/leagues/CNSWPL/series_stats.json")
    print()
    print("   cat /app/data/leagues/CNSWPL/match_history.json")
    print("   cat /app/data/leagues/CNSWPL/match_scores.json")
    print("   cat /app/data/leagues/CNSWPL/schedules.json")
    print("   cat /app/data/leagues/CNSWPL/players.json")
    print()
    
    # APTA files
    print("   # APTA_CHICAGO files")
    print("   cat /app/data/leagues/APTA_CHICAGO/series_stats.json")
    print("   cat /app/data/leagues/APTA_CHICAGO/match_history.json")
    print("   cat /app/data/leagues/APTA_CHICAGO/match_scores.json")
    print("   cat /app/data/leagues/APTA_CHICAGO/schedules.json")
    print("   cat /app/data/leagues/APTA_CHICAGO/players.json")
    print("   cat /app/data/leagues/APTA_CHICAGO/players_career_stats.json")
    print("   cat /app/data/leagues/APTA_CHICAGO/player_history.json")
    print()
    
    print("3. Or use this one-liner to save files locally (from SSH session):")
    print()
    print("   # Create a tar archive on production")
    print("   cd /app/data/leagues")
    print("   tar -czf /tmp/league_json_files.tar.gz CNSWPL/*.json APTA_CHICAGO/*.json")
    print("   exit")
    print()
    print("4. Then from your local machine, download the archive:")
    print("   # This would require Railway CLI file transfer capability")
    print("   # Or use Railway's web interface to download files")
    print()
    
    print("=" * 80)
    print("⚠️  Automated download requires Railway CLI service specification")
    print("=" * 80)
    print()
    print("Alternative: Use Railway web dashboard to download files")
    print("  or manually copy/paste file contents via SSH")

if __name__ == "__main__":
    main()

