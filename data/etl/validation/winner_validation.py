#!/usr/bin/env python3
"""
Winner Validation for ETL Pipeline
Validates that winner determination matches score analysis and provides corrections
"""

import json
import re
import os
import sys
from typing import List, Dict, Tuple, Optional

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

def parse_score_to_determine_winner(score_str: str, league_id: str = None) -> Optional[str]:
    """
    Analyze score string to determine winner based on set scores
    Enhanced to handle league-specific formats including super tiebreaks
    Returns 'home' if home team won, 'away' if away team won, None if unclear
    """
    if not score_str or score_str.strip() == "":
        return None
    
    # Clean up score string
    score_str = score_str.strip()
    
    # Handle tiebreak scores like "6-7 [1-7]" - remove tiebreak part for set counting
    score_str_clean = re.sub(r'\s*\[[^\]]+\]', '', score_str)
    
    # Split by comma to get individual sets
    sets = [s.strip() for s in score_str_clean.split(',') if s.strip()]
    
    # CITA League: Skip validation for problematic data
    if league_id == 'CITA' and len(sets) >= 1:
        # Check for incomplete/live match data patterns
        for set_score in sets:
            if '-' in set_score:
                try:
                    parts = set_score.split('-')
                    if len(parts) == 2:
                        home_games = int(parts[0].strip())
                        away_games = int(parts[1].strip())
                        # If we see scores like 2-2, 3-3, 4-5 etc, it's likely incomplete
                        if (home_games < 6 and away_games < 6 and 
                            abs(home_games - away_games) <= 2 and
                            not (home_games == 0 and away_games == 0)):
                            return None  # Skip validation for incomplete CITA matches
                except (ValueError, IndexError):
                    pass
    
    home_sets_won = 0
    away_sets_won = 0
    
    for i, set_score in enumerate(sets):
        if '-' not in set_score:
            continue
            
        try:
            # Extract scores like "6-2" or "5-7"
            parts = set_score.split('-')
            if len(parts) != 2:
                continue
                
            home_games = int(parts[0].strip())
            away_games = int(parts[1].strip())
            
            # NSTF/CITA: Handle super tiebreak format (third "set" is actually a tiebreak to 10)
            if (i == 2 and len(sets) == 3 and 
                (league_id in ['NSTF', 'CITA'] or home_games >= 10 or away_games >= 10)):
                # This is a super tiebreak
                if home_games > away_games:
                    home_sets_won += 1
                elif away_games > home_games:
                    away_sets_won += 1
                continue
            
            # Standard set scoring
            # Determine set winner
            if home_games > away_games:
                home_sets_won += 1
            elif away_games > home_games:
                away_sets_won += 1
            # Tie sets don't count toward either team
                
        except (ValueError, IndexError):
            continue
    
    # Determine overall winner (best of 3 sets or best of 3 with super tiebreak)
    if home_sets_won > away_sets_won:
        return "home"
    elif away_sets_won > home_sets_won:
        return "away"
    else:
        return None  # Unclear or tied

def validate_match_winner(match_data: Dict) -> Dict:
    """
    Validate a single match record and provide corrected winner if needed
    Enhanced to handle league-specific formats
    Returns dict with validation results
    """
    scores = match_data.get('Scores', '')
    recorded_winner = match_data.get('Winner', '').lower()
    league_id = match_data.get('league_id', '')
    
    # Determine winner from score analysis with league-specific logic
    calculated_winner = parse_score_to_determine_winner(scores, league_id)
    
    result = {
        'match_data': match_data,
        'scores': scores,
        'recorded_winner': recorded_winner,
        'calculated_winner': calculated_winner,
        'is_consistent': False,
        'needs_correction': False,
        'corrected_winner': recorded_winner
    }
    
    # Check consistency
    if calculated_winner is None:
        # Can't determine from score, accept recorded winner
        result['is_consistent'] = True
        result['validation_note'] = "Score inconclusive, accepted recorded winner"
    elif recorded_winner in ['home', 'away'] and recorded_winner == calculated_winner:
        # Perfect match
        result['is_consistent'] = True
        result['validation_note'] = "Winner matches score analysis"
    elif recorded_winner == 'unknown' and calculated_winner:
        # Can improve unknown winner
        result['needs_correction'] = True
        result['corrected_winner'] = calculated_winner
        result['validation_note'] = f"Improved unknown winner to {calculated_winner} based on score"
    elif recorded_winner in ['home', 'away'] and calculated_winner and recorded_winner != calculated_winner:
        # Mismatch - score analysis overrides
        result['needs_correction'] = True
        result['corrected_winner'] = calculated_winner
        result['validation_note'] = f"Corrected {recorded_winner} to {calculated_winner} based on score analysis"
    else:
        # Other cases
        result['validation_note'] = f"Complex case: recorded={recorded_winner}, calculated={calculated_winner}"
    
    return result

def validate_json_file(json_path: str, auto_fix: bool = False) -> Dict:
    """
    Validate winner data in a JSON file
    """
    print(f"\n🔍 Validating: {json_path}")
    
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        return {'error': f"Failed to load JSON: {e}"}
    
    if not isinstance(data, list):
        return {'error': "JSON should contain a list of matches"}
    
    results = {
        'total_matches': len(data),
        'consistent_matches': 0,
        'corrected_matches': 0,
        'problematic_matches': 0,
        'corrections': [],
        'problems': []
    }
    
    corrections_made = []
    
    for i, match in enumerate(data):
        validation = validate_match_winner(match)
        
        if validation['is_consistent']:
            results['consistent_matches'] += 1
        elif validation['needs_correction']:
            results['corrected_matches'] += 1
            results['corrections'].append({
                'index': i,
                'home_team': match.get('Home Team', ''),
                'away_team': match.get('Away Team', ''),
                'date': match.get('Date', ''),
                'scores': validation['scores'],
                'original_winner': validation['recorded_winner'],
                'corrected_winner': validation['corrected_winner'],
                'note': validation['validation_note']
            })
            
            # Apply correction if auto_fix is enabled
            if auto_fix:
                data[i]['Winner'] = validation['corrected_winner']
                corrections_made.append({
                    'match': f"{match.get('Home Team', '')} vs {match.get('Away Team', '')}",
                    'date': match.get('Date', ''),
                    'change': f"{validation['recorded_winner']} → {validation['corrected_winner']}"
                })
        else:
            results['problematic_matches'] += 1
            results['problems'].append({
                'index': i,
                'home_team': match.get('Home Team', ''),
                'away_team': match.get('Away Team', ''),
                'date': match.get('Date', ''),
                'scores': validation['scores'],
                'recorded_winner': validation['recorded_winner'],
                'calculated_winner': validation['calculated_winner'],
                'note': validation['validation_note']
            })
    
    # Save corrected file if auto_fix was used and corrections were made
    if auto_fix and corrections_made:
        try:
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=2)
            results['corrections_applied'] = len(corrections_made)
            print(f"✅ Applied {len(corrections_made)} corrections to {json_path}")
        except Exception as e:
            results['fix_error'] = f"Failed to save corrections: {e}"
    
    return results

def validate_all_match_files(leagues_dir: str = None, auto_fix: bool = False) -> Dict:
    """
    Validate winner data across all league match history files
    """
    if leagues_dir is None:
        # Default to project structure
        script_dir = os.path.dirname(os.path.abspath(__file__))
        leagues_dir = os.path.join(script_dir, '../../leagues')
    
    print(f"🔍 Scanning for match_history.json files in: {leagues_dir}")
    
    results = {
        'files_processed': 0,
        'total_matches': 0,
        'total_consistent': 0,
        'total_corrected': 0,
        'total_problems': 0,
        'file_results': {}
    }
    
    # Find all match_history.json files
    for root, dirs, files in os.walk(leagues_dir):
        if 'match_history.json' in files:
            json_path = os.path.join(root, 'match_history.json')
            league_name = os.path.basename(root)
            
            file_result = validate_json_file(json_path, auto_fix)
            
            if 'error' not in file_result:
                results['files_processed'] += 1
                results['total_matches'] += file_result['total_matches']
                results['total_consistent'] += file_result['consistent_matches']
                results['total_corrected'] += file_result['corrected_matches']
                results['total_problems'] += file_result['problematic_matches']
                results['file_results'][league_name] = file_result
                
                # Print summary for this file
                print(f"   {league_name}: {file_result['total_matches']} matches, "
                      f"{file_result['consistent_matches']} consistent, "
                      f"{file_result['corrected_matches']} corrected, "
                      f"{file_result['problematic_matches']} problems")
            else:
                print(f"   ❌ {league_name}: {file_result['error']}")
                results['file_results'][league_name] = file_result
    
    return results

def print_validation_summary(results: Dict):
    """Print a comprehensive validation summary"""
    print(f"\n📊 VALIDATION SUMMARY")
    print(f"=" * 50)
    print(f"Files processed: {results['files_processed']}")
    print(f"Total matches: {results['total_matches']:,}")
    print(f"Consistent matches: {results['total_consistent']:,} ({results['total_consistent']/results['total_matches']*100:.1f}%)")
    if results['total_corrected'] > 0:
        print(f"Corrected matches: {results['total_corrected']:,} ({results['total_corrected']/results['total_matches']*100:.1f}%)")
    if results['total_problems'] > 0:
        print(f"Problematic matches: {results['total_problems']:,} ({results['total_problems']/results['total_matches']*100:.1f}%)")
    
    print(f"\n🔧 CORRECTION DETAILS")
    print(f"=" * 50)
    
    for league, file_result in results['file_results'].items():
        if 'error' in file_result:
            continue
            
        if file_result['corrected_matches'] > 0:
            print(f"\n{league} - {file_result['corrected_matches']} corrections:")
            for correction in file_result['corrections'][:5]:  # Show first 5
                print(f"   • {correction['home_team']} vs {correction['away_team']} ({correction['date']})")
                print(f"     Score: {correction['scores']}")
                print(f"     Change: {correction['original_winner']} → {correction['corrected_winner']}")
            if len(file_result['corrections']) > 5:
                print(f"   ... and {len(file_result['corrections']) - 5} more")

def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate winner data in match history JSON files')
    parser.add_argument('--auto-fix', action='store_true', help='Automatically fix detected issues')
    parser.add_argument('--leagues-dir', help='Path to leagues directory (default: auto-detect)')
    parser.add_argument('--file', help='Validate specific JSON file instead of all files')
    
    args = parser.parse_args()
    
    if args.file:
        # Validate single file
        result = validate_json_file(args.file, args.auto_fix)
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
            return 1
        
        print(f"\n📊 Results for {args.file}:")
        print(f"Total matches: {result['total_matches']}")
        print(f"Consistent: {result['consistent_matches']}")
        print(f"Corrected: {result['corrected_matches']}")
        print(f"Problems: {result['problematic_matches']}")
        
        if result['corrections']:
            print(f"\n🔧 Corrections needed:")
            for correction in result['corrections'][:10]:
                print(f"   • {correction['home_team']} vs {correction['away_team']} ({correction['date']})")
                print(f"     {correction['note']}")
    else:
        # Validate all files
        results = validate_all_match_files(args.leagues_dir, args.auto_fix)
        print_validation_summary(results)
        
        if args.auto_fix:
            print(f"\n✅ Auto-fix mode: Corrections have been applied to JSON files")
        else:
            print(f"\n💡 Tip: Use --auto-fix to automatically apply corrections")
    
    return 0

if __name__ == "__main__":
    exit(main()) 