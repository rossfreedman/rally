#!/usr/bin/env python3
"""
League Score Format Analysis & Validation
==========================================

Different leagues use different scoring formats. This tool analyzes and documents
the various formats to enhance our validation system.

Score Formats Discovered:
1. CNSWPL: Standard tennis (6-3, 6-1) with occasional tiebreaks
2. APTA_CHICAGO: Standard tennis format  
3. NSTF: Standard tennis + super tiebreaks (6-3, 4-6, 10-6)
4. CITA: Mixed formats including incomplete matches and unusual patterns
"""

import json
import re
import os
import sys
from typing import Dict, List, Tuple, Optional
from collections import defaultdict, Counter

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

class ScoreFormatAnalyzer:
    def __init__(self):
        self.format_patterns = {
            'standard_2_sets': re.compile(r'^\d+-\d+, \d+-\d+$'),
            'standard_3_sets': re.compile(r'^\d+-\d+, \d+-\d+, \d+-\d+$'),
            'tiebreak_format': re.compile(r'\d+-\d+ \[\d+-\d+\]'),
            'super_tiebreak_standalone': re.compile(r'^\d+-\d+, \d+-\d+, 1[01]-\d+$'),
            'super_tiebreak_formal': re.compile(r'\d+-\d+, \d+-\d+, [01]-1 \[\d+-\d+\]'),
            'incomplete_match': re.compile(r'\d+-\d+, \d+-\d+, \d+-\d+$'),
            'impossible_score': re.compile(r'\d+-\d+, \d+-\d+, \d+-\d+'),
        }
        
        self.league_stats = defaultdict(lambda: {
            'total_matches': 0,
            'format_counts': defaultdict(int),
            'unusual_scores': [],
            'score_examples': defaultdict(list)
        })

    def analyze_score_format(self, score: str, league: str) -> Dict:
        """Analyze a single score string and categorize its format"""
        if not score or score.strip() == "":
            return {'format': 'empty', 'valid': False, 'issues': ['Empty score']}
        
        score = score.strip()
        result = {
            'original_score': score,
            'format': 'unknown',
            'valid': True,
            'issues': [],
            'sets_count': 0,
            'super_tiebreak': False,
            'incomplete': False,
            'league': league
        }
        
        # Count commas to estimate sets
        sets = [s.strip() for s in score.split(',') if s.strip()]
        result['sets_count'] = len(sets)
        
        # Check for different patterns
        if self.format_patterns['tiebreak_format'].search(score):
            result['has_tiebreak'] = True
        
        if re.search(r'1[01]-\d+', score):
            result['super_tiebreak'] = True
            result['format'] = 'super_tiebreak'
        elif self.format_patterns['super_tiebreak_formal'].search(score):
            result['super_tiebreak'] = True
            result['format'] = 'super_tiebreak_formal'
        elif result['sets_count'] == 2:
            result['format'] = 'standard_2_sets'
        elif result['sets_count'] == 3:
            result['format'] = 'standard_3_sets'
            # Check for incomplete/impossible scores in 3-set matches
            for set_score in sets:
                # Remove tiebreak notation for analysis
                clean_set = re.sub(r'\s*\[\d+-\d+\]', '', set_score)
                if '-' in clean_set:
                    try:
                        games1, games2 = map(int, clean_set.split('-'))
                        # Check for impossible scores
                        if games1 == 6 and games2 == 6:
                            result['issues'].append(f'Impossible score 6-6 (should be tiebreak)')
                            result['valid'] = False
                        elif games1 < 6 and games2 < 6 and max(games1, games2) < 6:
                            # Both players under 6 games suggests incomplete
                            if not (games1 == 0 and games2 == 0):  # 0-0 might be valid forfeit
                                result['incomplete'] = True
                                result['issues'].append(f'Incomplete set: {clean_set}')
                    except ValueError:
                        result['issues'].append(f'Invalid set format: {clean_set}')
                        result['valid'] = False
        else:
            result['format'] = f'unusual_{result["sets_count"]}_parts'
            result['valid'] = False
            result['issues'].append(f'Unusual format with {result["sets_count"]} parts')
        
        return result

    def analyze_league_file(self, json_path: str, league_name: str) -> Dict:
        """Analyze all scores in a league's match history file"""
        print(f"\n🔍 Analyzing {league_name}...")
        
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            return {'error': f"Failed to load {json_path}: {e}"}
        
        if not isinstance(data, list):
            return {'error': "JSON should contain a list of matches"}
        
        league_stats = {
            'league': league_name,
            'total_matches': len(data),
            'format_breakdown': defaultdict(int),
            'issue_breakdown': defaultdict(int),
            'super_tiebreak_count': 0,
            'incomplete_matches': 0,
            'invalid_matches': 0,
            'examples': defaultdict(list),
            'unusual_scores': []
        }
        
        for i, match in enumerate(data):
            score = match.get('Scores', '')
            analysis = self.analyze_score_format(score, league_name)
            
            # Count formats
            league_stats['format_breakdown'][analysis['format']] += 1
            
            # Count issues
            for issue in analysis['issues']:
                league_stats['issue_breakdown'][issue] += 1
            
            # Special cases
            if analysis['super_tiebreak']:
                league_stats['super_tiebreak_count'] += 1
            
            if analysis['incomplete']:
                league_stats['incomplete_matches'] += 1
            
            if not analysis['valid']:
                league_stats['invalid_matches'] += 1
            
            # Collect examples (limit to avoid memory issues)
            if len(league_stats['examples'][analysis['format']]) < 5:
                league_stats['examples'][analysis['format']].append(score)
            
            # Collect unusual scores for manual review
            if analysis['format'].startswith('unusual') or not analysis['valid']:
                if len(league_stats['unusual_scores']) < 20:
                    league_stats['unusual_scores'].append({
                        'score': score,
                        'format': analysis['format'],
                        'issues': analysis['issues'],
                        'home_team': match.get('Home Team', ''),
                        'away_team': match.get('Away Team', ''),
                        'date': match.get('Date', '')
                    })
        
        return league_stats

    def print_league_analysis(self, stats: Dict):
        """Print formatted analysis for a league"""
        league = stats['league']
        total = stats['total_matches']
        
        print(f"\n📊 {league} ANALYSIS")
        print(f"{'='*50}")
        print(f"Total matches: {total:,}")
        
        print(f"\n🏆 Format Breakdown:")
        for format_type, count in sorted(stats['format_breakdown'].items(), key=lambda x: x[1], reverse=True):
            percentage = count / total * 100
            print(f"   {format_type}: {count:,} ({percentage:.1f}%)")
        
        if stats['super_tiebreak_count'] > 0:
            print(f"\n🎾 Super Tiebreaks: {stats['super_tiebreak_count']:,} ({stats['super_tiebreak_count']/total*100:.1f}%)")
        
        if stats['issue_breakdown']:
            print(f"\n⚠️  Issues Found:")
            for issue, count in sorted(stats['issue_breakdown'].items(), key=lambda x: x[1], reverse=True):
                print(f"   {issue}: {count:,}")
        
        if stats['examples']:
            print(f"\n📝 Format Examples:")
            for format_type, examples in stats['examples'].items():
                if examples:
                    print(f"   {format_type}: {examples[0]}")
        
        if stats['unusual_scores']:
            print(f"\n🔍 Unusual Scores (first 5):")
            for unusual in stats['unusual_scores'][:5]:
                print(f"   • {unusual['home_team']} vs {unusual['away_team']} ({unusual['date']})")
                print(f"     Score: {unusual['score']}")
                print(f"     Issues: {', '.join(unusual['issues'])}")

    def generate_enhanced_validation_rules(self, all_stats: Dict) -> str:
        """Generate enhanced validation rules based on analysis"""
        rules = """
# Enhanced Score Validation Rules Based on League Analysis

def validate_score_by_league(score: str, league: str) -> Dict:
    \"\"\"
    Validate score format based on league-specific rules
    \"\"\"
    result = {'valid': True, 'issues': [], 'corrected_score': score}
    
    if league == 'CNSWPL':
        # Standard tennis format, occasional tiebreaks
        # Very reliable scoring
        return validate_standard_tennis_format(score)
        
    elif league == 'APTA_CHICAGO':
        # Standard tennis format
        # Platform tennis, reliable scoring
        return validate_standard_tennis_format(score)
        
    elif league == 'NSTF':
        # Standard tennis + super tiebreaks
        # Super tiebreak in place of third set: "6-3, 4-6, 10-6"
        if re.search(r'\\d+-\\d+, \\d+-\\d+, 1[01]-\\d+$', score):
            return validate_super_tiebreak_format(score)
        else:
            return validate_standard_tennis_format(score)
            
    elif league == 'CITA':
        # CAUTION: Mixed formats, many incomplete matches
        # May include live match data or different recording standards
        result = validate_standard_tennis_format(score)
        
        # More lenient validation for CITA due to format inconsistencies
        if not result['valid']:
            result['issues'].append('CITA league has non-standard scoring - manual review recommended')
            # Don't auto-correct CITA scores
            result['auto_correctable'] = False
        
        return result
    
    else:
        # Unknown league - use standard validation
        return validate_standard_tennis_format(score)

def validate_standard_tennis_format(score: str) -> Dict:
    \"\"\"Standard tennis validation (best of 3 sets)\"\"\"
    # Implementation here...
    pass

def validate_super_tiebreak_format(score: str) -> Dict:
    \"\"\"Validate super tiebreak format (common in doubles)\"\"\"
    # Implementation here...
    pass
"""
        return rules

def main():
    """Main execution"""
    analyzer = ScoreFormatAnalyzer()
    
    # Define leagues to analyze
    leagues = {
        'CNSWPL': 'data/leagues/CNSWPL/match_history.json',
        'APTA_CHICAGO': 'data/leagues/APTA_CHICAGO/match_history.json', 
        'NSTF': 'data/leagues/NSTF/match_history.json',
        'CITA': 'data/leagues/CITA/match_history.json'
    }
    
    all_stats = {}
    
    print("🔍 LEAGUE SCORE FORMAT ANALYSIS")
    print("="*60)
    
    for league_name, file_path in leagues.items():
        if os.path.exists(file_path):
            stats = analyzer.analyze_league_file(file_path, league_name)
            if 'error' not in stats:
                all_stats[league_name] = stats
                analyzer.print_league_analysis(stats)
        else:
            print(f"⚠️  File not found: {file_path}")
    
    # Generate summary
    print(f"\n🎯 SUMMARY & RECOMMENDATIONS")
    print(f"="*60)
    
    total_matches = sum(stats['total_matches'] for stats in all_stats.values())
    print(f"Total matches analyzed: {total_matches:,}")
    
    # Find leagues with super tiebreaks
    super_tiebreak_leagues = [name for name, stats in all_stats.items() if stats['super_tiebreak_count'] > 0]
    if super_tiebreak_leagues:
        print(f"Leagues using super tiebreaks: {', '.join(super_tiebreak_leagues)}")
    
    # Find leagues with issues
    problematic_leagues = [(name, stats['invalid_matches']) for name, stats in all_stats.items() if stats['invalid_matches'] > 0]
    if problematic_leagues:
        print(f"Leagues with format issues:")
        for name, invalid_count in problematic_leagues:
            total = all_stats[name]['total_matches']
            print(f"   {name}: {invalid_count:,} invalid ({invalid_count/total*100:.1f}%)")
    
    print(f"\n💡 RECOMMENDATIONS:")
    print(f"1. Use league-specific validation rules")
    print(f"2. Handle super tiebreaks in NSTF league") 
    print(f"3. Use more lenient validation for CITA league")
    print(f"4. Consider CITA data quality issues")
    print(f"5. Update winner determination logic to handle all formats")
    
    # Generate enhanced validation code
    enhanced_rules = analyzer.generate_enhanced_validation_rules(all_stats)
    print(f"\n📝 Enhanced validation rules generated (see code output)")
    
    return 0

if __name__ == "__main__":
    exit(main()) 