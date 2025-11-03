#!/usr/bin/env python3
"""
Manually consolidate temp_match_scores files into final match_scores.json

This script consolidates the temp series files that exist in the volume
into the final match_scores.json file.
"""

import os
import sys
import json
import glob
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from data.etl.utils.league_directory_manager import get_league_file_path

def consolidate_temp_files(league_key="CNSWPL"):
    """Consolidate temp match scores files into final file."""
    
    print("=" * 70)
    print(f"Consolidating temp match scores for {league_key}")
    print("=" * 70)
    print()
    
    # Get the output file path
    output_file = get_league_file_path(league_key, "match_scores.json")
    output_file = os.path.abspath(output_file)
    
    print(f"Output file: {output_file}")
    
    # Get temp directory
    tmp_dir = os.path.join(os.path.dirname(output_file), 'temp_match_scores')
    print(f"Temp directory: {tmp_dir}")
    print()
    
    # Load existing matches if file exists
    existing_matches = []
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r') as f:
                existing_matches = json.load(f)
            print(f"✅ Loaded {len(existing_matches):,} existing matches from {output_file}")
        except Exception as e:
            print(f"⚠️ Could not load existing file: {e}")
            existing_matches = []
    else:
        print("ℹ️ No existing match_scores.json file found")
    
    # Load all temp series files
    temp_files = []
    if os.path.isdir(tmp_dir):
        temp_files = glob.glob(os.path.join(tmp_dir, 'series_*.json'))
        print(f"Found {len(temp_files)} temp series files")
    else:
        print(f"⚠️ Temp directory doesn't exist: {tmp_dir}")
        return
    
    if not temp_files:
        print("⚠️ No temp files found to consolidate")
        return
    
    # Deduplication function (same as scraper)
    def _dedupe_key(m: dict) -> str:
        mid = (m.get('match_id') or '').strip()
        line_marker = (m.get('Line') or m.get('Court') or m.get('Court #') or '').strip()
        if mid:
            return f"{mid}|{line_marker}".lower()
        home = (m.get('Home Team') or '').strip()
        away = (m.get('Away Team') or '').strip()
        date = (m.get('Date') or '').strip()
        return f"{home}|{away}|{date}|{line_marker}".lower()
    
    # Merge all matches
    merged_by_key = {}
    
    # 1) Start with existing
    for m in existing_matches:
        merged_by_key[_dedupe_key(m)] = m
    
    # 2) Load and merge temp files
    for temp_file in temp_files:
        try:
            with open(temp_file, 'r') as f:
                series_matches = json.load(f)
            print(f"  Loaded {len(series_matches)} matches from {os.path.basename(temp_file)}")
            for m in series_matches:
                merged_by_key[_dedupe_key(m)] = m
        except Exception as e:
            print(f"  ⚠️ Failed to load {temp_file}: {e}")
    
    all_matches = list(merged_by_key.values())
    
    print()
    print(f"📊 Consolidation Summary:")
    print(f"   Existing matches: {len(existing_matches):,}")
    print(f"   Matches from temp files: {len(all_matches) - len(existing_matches):,}")
    print(f"   Total matches: {len(all_matches):,}")
    print()
    
    # Save consolidated file
    print(f"💾 Saving consolidated file to: {output_file}")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Atomic write
    tmp_file = output_file + '.tmp'
    with open(tmp_file, 'w') as f:
        json.dump(all_matches, f, indent=2)
    os.replace(tmp_file, output_file)
    
    print(f"✅ Successfully saved {len(all_matches):,} matches to {output_file}")
    print()
    print("=" * 70)
    print("✅ Consolidation Complete!")
    print("=" * 70)

if __name__ == "__main__":
    consolidate_temp_files()


