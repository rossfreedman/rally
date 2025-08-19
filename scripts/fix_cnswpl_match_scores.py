#!/usr/bin/env python3
"""
Script to fix CNSWPL match scores and winner assignments.

The scraper incorrectly scraped scores in home-away format when they should be away-home format,
and incorrectly assigned "home" as winner for every match regardless of actual score.

Fixes:
1. Convert scores from "home-away, home-away" to "away-home, away-home" format
2. Determine correct winner based on the corrected scores
"""

import json
import re
from datetime import datetime

def parse_score_set(score_set):
    """Parse a single set score like '6-4' into (away_score, home_score)"""
    try:
        parts = score_set.strip().split('-')
        if len(parts) != 2:
            return None, None
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return None, None

def flip_score_format(home_away_scores):
    """
    Convert scores from home-away format to away-home format.
    
    Input: "0-6, 1-6" (home-away format)
    Output: "6-0, 6-1" (away-home format)
    """
    if not home_away_scores or home_away_scores.strip() == "":
        return home_away_scores
    
    # Split by comma to get individual sets
    sets = [s.strip() for s in home_away_scores.split(',')]
    flipped_sets = []
    
    for set_score in sets:
        # Parse the set (currently home-away)
        home_score, away_score = parse_score_set(set_score)
        if home_score is not None and away_score is not None:
            # Flip to away-home format
            flipped_sets.append(f"{away_score}-{home_score}")
        else:
            # Keep original if we can't parse
            flipped_sets.append(set_score)
    
    return ", ".join(flipped_sets)

def determine_winner(away_home_scores):
    """
    Determine winner based on away-home formatted scores.
    
    Input: "6-0, 6-1" (away team won both sets)
    Output: "away"
    
    Input: "3-6, 2-6" (home team won both sets) 
    Output: "home"
    """
    if not away_home_scores or away_home_scores.strip() == "":
        return "home"  # Default fallback
    
    sets = [s.strip() for s in away_home_scores.split(',')]
    away_sets_won = 0
    home_sets_won = 0
    
    for set_score in sets:
        away_score, home_score = parse_score_set(set_score)
        if away_score is not None and home_score is not None:
            if away_score > home_score:
                away_sets_won += 1
            elif home_score > away_score:
                home_sets_won += 1
    
    # Winner is determined by who won more sets
    if away_sets_won > home_sets_won:
        return "away"
    elif home_sets_won > away_sets_won:
        return "home"
    else:
        # Tie or unparseable - default to home (shouldn't happen in tennis)
        return "home"

def fix_cnswpl_matches(input_file, output_file):
    """Fix all matches in the CNSWPL match history file."""
    
    print(f"Loading match data from {input_file}...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        matches = json.load(f)
    
    print(f"Found {len(matches)} matches to process")
    
    fixes_applied = 0
    winner_changes = 0
    
    for i, match in enumerate(matches):
        if i % 1000 == 0:
            print(f"Processing match {i+1}/{len(matches)}...")
        
        original_scores = match.get("Scores", "")
        original_winner = match.get("Winner", "")
        
        # Step 1: Fix score format (home-away to away-home)
        corrected_scores = flip_score_format(original_scores)
        
        # Step 2: Determine correct winner based on corrected scores
        correct_winner = determine_winner(corrected_scores)
        
        # Update the match if changes are needed
        if corrected_scores != original_scores or correct_winner != original_winner:
            match["Scores"] = corrected_scores
            match["Winner"] = correct_winner
            fixes_applied += 1
            
            if correct_winner != original_winner:
                winner_changes += 1
                
            # Log a few examples
            if fixes_applied <= 5:
                print(f"Example fix #{fixes_applied}:")
                print(f"  Match ID: {match.get('match_id', 'N/A')}")
                print(f"  Original scores: {original_scores}")
                print(f"  Corrected scores: {corrected_scores}")
                print(f"  Original winner: {original_winner}")
                print(f"  Corrected winner: {correct_winner}")
                print()
    
    print(f"\nSummary:")
    print(f"Total matches processed: {len(matches)}")
    print(f"Matches with fixes applied: {fixes_applied}")
    print(f"Winner changes: {winner_changes}")
    
    # Save the corrected data
    print(f"\nSaving corrected data to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(matches, f, indent=2, ensure_ascii=False)
    
    print("Fix complete!")
    return fixes_applied, winner_changes

def main():
    input_file = "data/leagues/CNSWPL/match_history.json"
    output_file = "data/leagues/CNSWPL/match_history.json"
    
    print("CNSWPL Match History Score Fix")
    print("=" * 40)
    print(f"Input file: {input_file}")
    print(f"Output file: {output_file}")
    print()
    
    # Verify backup exists
    backup_pattern = "data/leagues/CNSWPL/match_history_backup_*.json"
    print(f"Note: Backup should exist matching pattern: {backup_pattern}")
    print()
    
    try:
        fixes_applied, winner_changes = fix_cnswpl_matches(input_file, output_file)
        
        print(f"\n✅ Success! Applied {fixes_applied} fixes with {winner_changes} winner changes.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("The original file should be unchanged.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
