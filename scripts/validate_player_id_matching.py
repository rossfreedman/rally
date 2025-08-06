#!/usr/bin/env python3
"""
Player ID Matching Validation Script
===================================

This script validates player ID matching during JSON imports and identifies
potential mismatches that could cause data inconsistencies.

Usage:
    python scripts/validate_player_id_matching.py
"""

import json
import os
import sys
from typing import Dict, List

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from database_utils import execute_query, execute_query_one
from utils.league_utils import normalize_league_id
from utils.database_player_lookup import find_player_by_database_lookup


class PlayerIDValidator:
    """Validates player ID consistency between JSON files and database"""
    
    def __init__(self):
        self.data_dir = os.path.join(project_root, "data", "leagues", "all")
        self.validation_results = {
            'match_history_issues': [],
            'player_history_issues': [],
            'resolution_stats': {
                'total_checked': 0,
                'exact_matches': 0,
                'fallback_matches': 0,
                'failed_matches': 0
            }
        }
    
    def load_json_file(self, filename: str) -> List[Dict]:
        """Load JSON file with error handling"""
        filepath = os.path.join(self.data_dir, filename)
        print(f"📂 Loading {filename}...")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"✅ Loaded {len(data):,} records from {filename}")
            return data
        except Exception as e:
            print(f"❌ Error loading {filename}: {e}")
            return []
    
    def validate_player_id_in_database(self, tenniscores_player_id: str) -> bool:
        """Check if a player ID exists in the database"""
        if not tenniscores_player_id:
            return False
            
        result = execute_query_one(
            "SELECT tenniscores_player_id FROM players WHERE tenniscores_player_id = %s AND is_active = true",
            (tenniscores_player_id,)
        )
        return result is not None
    
    def validate_match_history_player_ids(self, match_history_data: List[Dict]):
        """Validate player IDs in match history data"""
        print("\n🔍 VALIDATING MATCH HISTORY PLAYER IDS")
        print("=" * 50)
        
        issues_found = 0
        total_player_ids = 0
        
        for i, record in enumerate(match_history_data):
            if i % 1000 == 0 and i > 0:
                print(f"   📊 Processed {i:,} matches...")
            
            match_date = record.get("Date", "")
            home_team = record.get("Home Team", "")
            away_team = record.get("Away Team", "")
            league_id = normalize_league_id(record.get("league_id", ""))
            
            # Check all player IDs in this match
            player_fields = [
                ("Home Player 1 ID", "Home Player 1"),
                ("Home Player 2 ID", "Home Player 2"),
                ("Away Player 1 ID", "Away Player 1"),
                ("Away Player 2 ID", "Away Player 2")
            ]
            
            for id_field, name_field in player_fields:
                player_id = (record.get(id_field) or "").strip()
                player_name = (record.get(name_field) or "").strip()
                
                if player_id:
                    total_player_ids += 1
                    self.validation_results['resolution_stats']['total_checked'] += 1
                    
                    if self.validate_player_id_in_database(player_id):
                        self.validation_results['resolution_stats']['exact_matches'] += 1
                    else:
                        # Player ID not found - try fallback matching
                        team_name = home_team if "Home" in id_field else away_team
                        club_name = self._extract_club_name_from_team(team_name)
                        series_name = self._extract_series_from_team_name(team_name)
                        first_name, last_name = self._parse_player_name(player_name)
                        
                        if first_name and last_name and league_id:
                            # Attempt fallback resolution
                            result = find_player_by_database_lookup(
                                first_name=first_name,
                                last_name=last_name,
                                club_name=club_name,
                                series_name=series_name,
                                league_id=league_id
                            )
                            
                            if result and isinstance(result, dict) and result.get('match_type') in ['exact', 'probable', 'high_confidence']:
                                self.validation_results['resolution_stats']['fallback_matches'] += 1
                                resolved_id = result['player']['tenniscores_player_id']
                                
                                issue = {
                                    'match_date': match_date,
                                    'teams': f"{home_team} vs {away_team}",
                                    'player_name': player_name,
                                    'original_id': player_id,
                                    'resolved_id': resolved_id,
                                    'resolution_type': result['match_type'],
                                    'message': result.get('message', '')
                                }
                                self.validation_results['match_history_issues'].append(issue)
                            else:
                                self.validation_results['resolution_stats']['failed_matches'] += 1
                                
                                issue = {
                                    'match_date': match_date,
                                    'teams': f"{home_team} vs {away_team}",
                                    'player_name': player_name,
                                    'original_id': player_id,
                                    'resolved_id': None,
                                    'resolution_type': 'failed',
                                    'message': 'No fallback match found'
                                }
                                self.validation_results['match_history_issues'].append(issue)
                        else:
                            self.validation_results['resolution_stats']['failed_matches'] += 1
                            
                        issues_found += 1
        
        print(f"\n📊 MATCH HISTORY VALIDATION RESULTS:")
        print(f"   Total player IDs checked: {total_player_ids:,}")
        print(f"   Issues found: {issues_found:,}")
        print(f"   Success rate: {((total_player_ids - issues_found) / total_player_ids * 100) if total_player_ids > 0 else 0:.1f}%")
    
    def validate_player_history_player_ids(self, player_history_data: List[Dict]):
        """Validate player IDs in player history data"""
        print("\n🔍 VALIDATING PLAYER HISTORY PLAYER IDS")
        print("=" * 50)
        
        issues_found = 0
        total_players = len(player_history_data)
        
        for i, record in enumerate(player_history_data):
            if i % 500 == 0 and i > 0:
                print(f"   📊 Processed {i:,} players...")
            
            player_id = record.get("player_id", "").strip()
            player_name = record.get("name", "").strip()
            league_id = normalize_league_id(record.get("league_id", ""))
            series = record.get("series", "").strip()
            
            if player_id:
                self.validation_results['resolution_stats']['total_checked'] += 1
                
                if self.validate_player_id_in_database(player_id):
                    self.validation_results['resolution_stats']['exact_matches'] += 1
                else:
                    # Player ID not found - try fallback matching
                    first_name, last_name = self._parse_player_name(player_name)
                    
                    if first_name and last_name and league_id:
                        result = find_player_by_database_lookup(
                            first_name=first_name,
                            last_name=last_name,
                            club_name="",  # Not available in player history
                            series_name=series,
                            league_id=league_id
                        )
                        
                        if result and isinstance(result, dict) and result.get('match_type') in ['exact', 'probable', 'high_confidence']:
                            self.validation_results['resolution_stats']['fallback_matches'] += 1
                            resolved_id = result['player']['tenniscores_player_id']
                            
                            issue = {
                                'player_name': player_name,
                                'original_id': player_id,
                                'resolved_id': resolved_id,
                                'resolution_type': result['match_type'],
                                'series': series,
                                'league_id': league_id,
                                'message': result.get('message', '')
                            }
                            self.validation_results['player_history_issues'].append(issue)
                        else:
                            self.validation_results['resolution_stats']['failed_matches'] += 1
                            
                            issue = {
                                'player_name': player_name,
                                'original_id': player_id,
                                'resolved_id': None,
                                'resolution_type': 'failed',
                                'series': series,
                                'league_id': league_id,
                                'message': 'No fallback match found'
                            }
                            self.validation_results['player_history_issues'].append(issue)
                    else:
                        self.validation_results['resolution_stats']['failed_matches'] += 1
                        
                    issues_found += 1
        
        print(f"\n📊 PLAYER HISTORY VALIDATION RESULTS:")
        print(f"   Total players checked: {total_players:,}")
        print(f"   Issues found: {issues_found:,}")
        print(f"   Success rate: {((total_players - issues_found) / total_players * 100) if total_players > 0 else 0:.1f}%")
    
    def _extract_club_name_from_team(self, team_name: str) -> str:
        """Extract club name from team name"""
        if not team_name:
            return ""
        
        # APTA format: "Club - Number"
        if " - " in team_name:
            return team_name.split(" - ")[0].strip()
        

        
        return team_name
    
    def _extract_series_from_team_name(self, team_name: str) -> str:
        """Extract series name from team name"""
        if not team_name:
            return ""
        
        # Try to extract series info from team name
        import re
        

        
        # APTA format: "Club - Number" -> "Series Number"
        if " - " in team_name:
            parts = team_name.split(" - ")
            if len(parts) > 1:
                return f"Series {parts[1]}"
        
        return ""
    
    def _parse_player_name(self, full_name: str) -> tuple:
        """Parse full name into first and last name"""
        if not full_name:
            return None, None
        
        # Handle "Last, First" format
        if ", " in full_name:
            parts = full_name.split(", ", 1)
            return parts[1].strip(), parts[0].strip()
        
        # Handle "First Last" format
        name_parts = full_name.strip().split()
        if len(name_parts) >= 2:
            return name_parts[0], " ".join(name_parts[1:])
        elif len(name_parts) == 1:
            return name_parts[0], ""
        
        return None, None
    
    def print_detailed_results(self):
        """Print detailed validation results"""
        print("\n" + "=" * 60)
        print("📊 DETAILED VALIDATION RESULTS")
        print("=" * 60)
        
        stats = self.validation_results['resolution_stats']
        total = stats['total_checked']
        
        if total > 0:
            print(f"Total player IDs validated: {total:,}")
            print(f"Exact matches: {stats['exact_matches']:,} ({stats['exact_matches']/total*100:.1f}%)")
            print(f"Fallback matches: {stats['fallback_matches']:,} ({stats['fallback_matches']/total*100:.1f}%)")
            print(f"Failed matches: {stats['failed_matches']:,} ({stats['failed_matches']/total*100:.1f}%)")
            
            success_rate = (stats['exact_matches'] + stats['fallback_matches']) / total * 100
            print(f"\n✅ OVERALL SUCCESS RATE: {success_rate:.1f}%")
        
        # Show sample issues
        if self.validation_results['match_history_issues']:
            print(f"\n⚠️  MATCH HISTORY ISSUES ({len(self.validation_results['match_history_issues'])} total):")
            for i, issue in enumerate(self.validation_results['match_history_issues'][:5]):
                print(f"   {i+1}. {issue['player_name']} in {issue['teams']} ({issue['match_date']})")
                print(f"      Original ID: {issue['original_id']}")
                if issue['resolved_id']:
                    print(f"      Resolved ID: {issue['resolved_id']} ({issue['resolution_type']})")
                else:
                    print(f"      Resolution: {issue['message']}")
            
            if len(self.validation_results['match_history_issues']) > 5:
                print(f"   ... and {len(self.validation_results['match_history_issues']) - 5} more")
        
        if self.validation_results['player_history_issues']:
            print(f"\n⚠️  PLAYER HISTORY ISSUES ({len(self.validation_results['player_history_issues'])} total):")
            for i, issue in enumerate(self.validation_results['player_history_issues'][:5]):
                print(f"   {i+1}. {issue['player_name']} in {issue['league_id']}")
                print(f"      Original ID: {issue['original_id']}")
                if issue['resolved_id']:
                    print(f"      Resolved ID: {issue['resolved_id']} ({issue['resolution_type']})")
                else:
                    print(f"      Resolution: {issue['message']}")
            
            if len(self.validation_results['player_history_issues']) > 5:
                print(f"   ... and {len(self.validation_results['player_history_issues']) - 5} more")
    
    def run_validation(self):
        """Run complete validation process"""
        print("🔍 PLAYER ID MATCHING VALIDATION")
        print("=" * 60)
        
        # Load JSON files
        match_history_data = self.load_json_file("match_history.json")
        player_history_data = self.load_json_file("player_history.json")
        
        # Run validations
        if match_history_data:
            self.validate_match_history_player_ids(match_history_data)
        
        if player_history_data:
            self.validate_player_history_player_ids(player_history_data)
        
        # Print results
        self.print_detailed_results()
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if self.validation_results['resolution_stats']['failed_matches'] > 0:
            print(f"   1. Run the enhanced import process to fix {self.validation_results['resolution_stats']['failed_matches']} player ID mismatches")
            print(f"   2. Review failed matches to identify potential data quality issues")
            print(f"   3. Consider updating name variation mappings for better fallback matching")
        else:
            print(f"   ✅ No player ID issues detected - import process should run cleanly!")


def main():
    """Main entry point"""
    validator = PlayerIDValidator()
    validator.run_validation()


if __name__ == "__main__":
    main() 