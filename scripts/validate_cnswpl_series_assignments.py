#!/usr/bin/env python3
"""
CNSWPL Series Assignment Validator
==================================

Validates that CNSWPL players have correct series assignments based on their team names.
This script should be run after ETL imports to ensure data integrity.

Usage:
    python3 scripts/validate_cnswpl_series_assignments.py
    python3 scripts/validate_cnswpl_series_assignments.py --fix-errors
    python3 scripts/validate_cnswpl_series_assignments.py --detailed-report

Exit codes:
    0: All assignments correct
    1: Validation errors found
    2: Script error
"""

import sys
import os
import json
import argparse
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from database_utils import execute_query, execute_update, execute_query_one


class CNSWPLSeriesValidator:
    """Validates CNSWPL series assignments"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.stats = {
            'total_players': 0,
            'correct_assignments': 0,
            'incorrect_assignments': 0,
            'missing_team_context': 0,
            'fallback_assignments': 0
        }
    
    def extract_expected_series_from_team_name(self, team_name: str) -> str:
        """Extract expected series from team name using the same logic as the scraper"""
        if not team_name:
            return "Series 1"
        
        # Same logic as scraper: team_parts[-1] should be series number/letter
        team_parts = team_name.split()
        if len(team_parts) >= 2:
            series_part = team_parts[-1]  # Last part should be series number/letter
            return f"Series {series_part}"
        else:
            return "Series 1"  # Fallback
    
    def validate_cnswpl_assignments(self) -> bool:
        """Validate all CNSWPL player series assignments"""
        print("🔍 Validating CNSWPL series assignments...")
        
        # Get all CNSWPL players with their team and series info
        players = execute_query("""
            SELECT 
                p.id,
                p.tenniscores_player_id,
                p.first_name,
                p.last_name,
                COALESCE(t.team_name, '') as team_name,
                COALESCE(s.name, '') as series_name,
                COALESCE(c.name, '') as club_name
            FROM players p
            JOIN leagues l ON p.league_id = l.id
            LEFT JOIN teams t ON p.team_id = t.id
            LEFT JOIN series s ON p.series_id = s.id
            LEFT JOIN clubs c ON p.club_id = c.id
            WHERE l.league_id = 'CNSWPL'
            ORDER BY p.last_name, p.first_name
        """)
        
        self.stats['total_players'] = len(players)
        print(f"📊 Found {len(players)} CNSWPL players to validate")
        
        for player in players:
            self._validate_single_player(player)
        
        return len(self.errors) == 0
    
    def _validate_single_player(self, player: Dict):
        """Validate a single player's series assignment"""
        team_name = player['team_name']
        current_series = player['series_name']
        player_name = f"{player['first_name']} {player['last_name']}"
        
        # Check for missing team context
        if not team_name:
            self.warnings.append({
                'type': 'missing_team',
                'player': player_name,
                'player_id': player['tenniscores_player_id'],
                'message': 'Player has no team assignment'
            })
            self.stats['missing_team_context'] += 1
            return
        
        # Extract expected series from team name
        expected_series = self.extract_expected_series_from_team_name(team_name)
        
        # Check if assignment is correct
        if current_series == expected_series:
            self.stats['correct_assignments'] += 1
        else:
            # Check if this is a fallback to "Series 1"
            if current_series == "Series 1" and expected_series != "Series 1":
                self.stats['fallback_assignments'] += 1
                error_type = 'fallback_assignment'
            else:
                self.stats['incorrect_assignments'] += 1
                error_type = 'incorrect_assignment'
            
            self.errors.append({
                'type': error_type,
                'player': player_name,
                'player_id': player['tenniscores_player_id'],
                'team_name': team_name,
                'current_series': current_series,
                'expected_series': expected_series,
                'db_player_id': player['id']
            })
    
    def fix_assignment_errors(self) -> int:
        """Fix detected assignment errors"""
        if not self.errors:
            print("✅ No errors to fix")
            return 0
        
        print(f"🔧 Fixing {len(self.errors)} assignment errors...")
        fixed_count = 0
        
        for error in self.errors:
            try:
                # Get the correct series ID
                series_row = execute_query_one(
                    "SELECT id FROM series WHERE name = %s", 
                    (error['expected_series'],)
                )
                
                if not series_row:
                    print(f"⚠️  Series not found: {error['expected_series']} for {error['player']}")
                    continue
                
                # Update the player's series assignment
                execute_update(
                    "UPDATE players SET series_id = %s WHERE id = %s",
                    (series_row['id'], error['db_player_id'])
                )
                
                print(f"✅ Fixed {error['player']}: {error['current_series']} → {error['expected_series']}")
                fixed_count += 1
                
            except Exception as e:
                print(f"❌ Failed to fix {error['player']}: {e}")
        
        return fixed_count
    
    def generate_report(self, detailed: bool = False) -> str:
        """Generate validation report"""
        report = []
        report.append("=" * 60)
        report.append("CNSWPL Series Assignment Validation Report")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Summary statistics
        report.append("📊 SUMMARY STATISTICS")
        report.append("-" * 30)
        report.append(f"Total Players:           {self.stats['total_players']}")
        report.append(f"Correct Assignments:     {self.stats['correct_assignments']}")
        report.append(f"Incorrect Assignments:   {self.stats['incorrect_assignments']}")
        report.append(f"Fallback Assignments:    {self.stats['fallback_assignments']}")
        report.append(f"Missing Team Context:    {self.stats['missing_team_context']}")
        report.append("")
        
        # Calculate accuracy
        total_with_teams = self.stats['total_players'] - self.stats['missing_team_context']
        if total_with_teams > 0:
            accuracy = (self.stats['correct_assignments'] / total_with_teams) * 100
            report.append(f"Accuracy Rate:           {accuracy:.1f}%")
        report.append("")
        
        # Errors section
        if self.errors:
            report.append("❌ ASSIGNMENT ERRORS")
            report.append("-" * 30)
            
            for error in self.errors:
                if error['type'] == 'fallback_assignment':
                    icon = "⚠️ "
                    error_type = "FALLBACK"
                else:
                    icon = "❌"
                    error_type = "INCORRECT"
                
                report.append(f"{icon} {error_type}: {error['player']}")
                report.append(f"   Team: {error['team_name']}")
                report.append(f"   Current: {error['current_series']}")
                report.append(f"   Expected: {error['expected_series']}")
                if detailed:
                    report.append(f"   Player ID: {error['player_id']}")
                report.append("")
        else:
            report.append("✅ NO ASSIGNMENT ERRORS FOUND")
            report.append("")
        
        # Warnings section
        if self.warnings:
            report.append("⚠️  WARNINGS")
            report.append("-" * 30)
            
            for warning in self.warnings:
                report.append(f"⚠️  {warning['player']}: {warning['message']}")
                if detailed:
                    report.append(f"   Player ID: {warning['player_id']}")
            report.append("")
        
        # Recommendations
        report.append("💡 RECOMMENDATIONS")
        report.append("-" * 30)
        
        if self.stats['fallback_assignments'] > 0:
            report.append("• Review fallback assignments - may indicate scraper issues")
        
        if self.stats['missing_team_context'] > 0:
            report.append("• Investigate players with missing team assignments")
        
        if self.stats['incorrect_assignments'] > 0:
            report.append("• Run with --fix-errors to automatically correct assignments")
        
        if len(self.errors) == 0 and len(self.warnings) == 0:
            report.append("• System is working correctly! ✅")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def check_scraper_patterns(self) -> Dict:
        """Check if scraped data follows expected patterns"""
        print("🔍 Checking scraper pattern consistency...")
        
        # Load scraped data to check patterns
        scraped_file = f"{project_root}/data/leagues/CNSWPL/players.json"
        if not os.path.exists(scraped_file):
            return {'error': 'CNSWPL players.json not found'}
        
        with open(scraped_file, 'r') as f:
            scraped_players = json.load(f)
        
        pattern_stats = {
            'total_scraped': len(scraped_players),
            'hardcoded_series_1': 0,
            'valid_patterns': 0,
            'unusual_patterns': []
        }
        
        for player in scraped_players:
            series = player.get('Series', '')
            team_name = player.get('Series Mapping ID', '')
            
            if series == 'Series 1' and team_name and not team_name.endswith(' 1'):
                pattern_stats['hardcoded_series_1'] += 1
                pattern_stats['unusual_patterns'].append({
                    'player': f"{player.get('First Name', '')} {player.get('Last Name', '')}",
                    'team': team_name,
                    'series': series
                })
            else:
                pattern_stats['valid_patterns'] += 1
        
        return pattern_stats


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Validate CNSWPL series assignments")
    parser.add_argument('--fix-errors', action='store_true', 
                       help='Automatically fix detected errors')
    parser.add_argument('--detailed-report', action='store_true',
                       help='Generate detailed report with player IDs')
    parser.add_argument('--check-patterns', action='store_true',
                       help='Check scraped data for pattern consistency')
    
    args = parser.parse_args()
    
    try:
        validator = CNSWPLSeriesValidator()
        
        # Check scraper patterns if requested
        if args.check_patterns:
            pattern_stats = validator.check_scraper_patterns()
            if 'error' in pattern_stats:
                print(f"❌ {pattern_stats['error']}")
                return 2
            
            print(f"📊 Scraper Pattern Analysis:")
            print(f"   Total Scraped: {pattern_stats['total_scraped']}")
            print(f"   Valid Patterns: {pattern_stats['valid_patterns']}")
            print(f"   Hardcoded Series 1: {pattern_stats['hardcoded_series_1']}")
            
            if pattern_stats['unusual_patterns']:
                print("⚠️  Unusual patterns detected:")
                for pattern in pattern_stats['unusual_patterns'][:5]:  # Show first 5
                    print(f"   {pattern['player']}: {pattern['team']} → {pattern['series']}")
            print()
        
        # Run validation
        is_valid = validator.validate_cnswpl_assignments()
        
        # Fix errors if requested
        if args.fix_errors:
            fixed_count = validator.fix_assignment_errors()
            if fixed_count > 0:
                print(f"✅ Fixed {fixed_count} assignment errors")
                # Re-run validation to verify fixes
                validator = CNSWPLSeriesValidator()
                is_valid = validator.validate_cnswpl_assignments()
        
        # Generate and display report
        report = validator.generate_report(detailed=args.detailed_report)
        print(report)
        
        # Exit with appropriate code
        if is_valid:
            print("✅ All CNSWPL series assignments are correct!")
            return 0
        else:
            print("❌ Series assignment errors detected")
            return 1
            
    except Exception as e:
        print(f"❌ Script error: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
