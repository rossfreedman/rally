#!/usr/bin/env python3
"""
Comprehensive validation script for APTA Chicago scraped data
Analyzes data completeness, accuracy, and consistency
"""

import json
import os
import re
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, List, Any, Tuple

def load_json_file(file_path: str) -> Dict:
    """Load JSON file with error handling"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading {file_path}: {e}")
        return {}

def validate_player_data(players: List[Dict]) -> Dict[str, Any]:
    """Validate player data structure and content"""
    validation_results = {
        'total_players': len(players),
        'required_fields': {},
        'data_quality': {},
        'captain_analysis': {},
        'series_analysis': {},
        'club_analysis': {},
        'pti_analysis': {},
        'issues': []
    }
    
    required_fields = ['Player ID', 'First Name', 'Last Name', 'Team', 'Series', 'Club', 'Captain', 'Current Season']
    
    # Check required fields
    for field in required_fields:
        missing_count = sum(1 for player in players if not player.get(field))
        validation_results['required_fields'][field] = {
            'missing_count': missing_count,
            'completeness': f"{((len(players) - missing_count) / len(players) * 100):.1f}%"
        }
    
    # Captain analysis
    captains = [p for p in players if p.get('Captain') == 'Yes']
    validation_results['captain_analysis'] = {
        'total_captains': len(captains),
        'captain_percentage': f"{(len(captains) / len(players) * 100):.2f}%",
        'captains_by_series': Counter(p.get('Series', 'Unknown') for p in captains)
    }
    
    # Series analysis
    series_counts = Counter(p.get('Series', 'Unknown') for p in players)
    validation_results['series_analysis'] = {
        'total_series': len(series_counts),
        'series_distribution': dict(series_counts.most_common()),
        'players_per_series_avg': f"{len(players) / len(series_counts):.1f}"
    }
    
    # Club analysis
    club_counts = Counter(p.get('Club', 'Unknown') for p in players)
    validation_results['club_analysis'] = {
        'total_clubs': len(club_counts),
        'top_10_clubs': dict(club_counts.most_common(10)),
        'players_per_club_avg': f"{len(players) / len(club_counts):.1f}"
    }
    
    # PTI analysis
    pti_values = [p.get('PTI') for p in players if p.get('PTI') and p.get('PTI') != 'N/A']
    pti_numeric = []
    for pti in pti_values:
        try:
            pti_numeric.append(float(pti))
        except (ValueError, TypeError):
            pass
    
    validation_results['pti_analysis'] = {
        'players_with_pti': len(pti_values),
        'pti_percentage': f"{(len(pti_values) / len(players) * 100):.1f}%",
        'pti_range': f"{min(pti_numeric):.1f} - {max(pti_numeric):.1f}" if pti_numeric else "N/A",
        'pti_avg': f"{sum(pti_numeric) / len(pti_numeric):.1f}" if pti_numeric else "N/A"
    }
    
    # Data quality checks
    issues = []
    
    # Check for empty names
    empty_names = [p for p in players if not p.get('First Name') or not p.get('Last Name')]
    if empty_names:
        issues.append(f"Found {len(empty_names)} players with empty names")
    
    # Check for invalid PTI values
    invalid_pti = [p for p in players if p.get('PTI') and p.get('PTI') != 'N/A' and not re.match(r'^\d+\.?\d*$', str(p.get('PTI')))]
    if invalid_pti:
        issues.append(f"Found {len(invalid_pti)} players with invalid PTI format")
    
    # Check for missing player IDs
    missing_ids = [p for p in players if not p.get('Player ID') or not p.get('Player ID').startswith('nndz-')]
    if missing_ids:
        issues.append(f"Found {len(missing_ids)} players with missing or invalid Player IDs")
    
    # Check for inconsistent captain field values
    invalid_captain = [p for p in players if p.get('Captain') not in ['Yes', 'No']]
    if invalid_captain:
        issues.append(f"Found {len(invalid_captain)} players with invalid Captain field values")
    
    validation_results['issues'] = issues
    validation_results['data_quality']['total_issues'] = len(issues)
    
    return validation_results

def validate_series_files(temp_dir: str) -> Dict[str, Any]:
    """Validate individual series files"""
    series_files = [f for f in os.listdir(temp_dir) if f.startswith('series_') and f.endswith('.json')]
    
    validation_results = {
        'total_series_files': len(series_files),
        'series_file_details': {},
        'consistency_issues': []
    }
    
    total_players_across_files = 0
    
    for series_file in sorted(series_files):
        file_path = os.path.join(temp_dir, series_file)
        data = load_json_file(file_path)
        
        if not data:
            validation_results['consistency_issues'].append(f"Failed to load {series_file}")
            continue
        
        player_count = len(data) if isinstance(data, list) else 0
        total_players_across_files += player_count
        
        validation_results['series_file_details'][series_file] = {
            'player_count': player_count,
            'file_size_kb': os.path.getsize(file_path) / 1024,
            'is_valid_json': isinstance(data, list)
        }
    
    validation_results['total_players_across_files'] = total_players_across_files
    
    return validation_results

def main():
    """Main validation function"""
    print("🔍 APTA CHICAGO SCRAPE DATA VALIDATION")
    print("=" * 60)
    
    # File paths
    main_file = "/Users/rossfreedman/dev/rally/data/leagues/APTA_CHICAGO/players.json"
    temp_dir = "/Users/rossfreedman/dev/rally/data/leagues/APTA_CHICAGO/temp"
    
    print(f"📁 Main file: {main_file}")
    print(f"📁 Temp directory: {temp_dir}")
    print()
    
    # Load main data
    print("📊 LOADING MAIN DATA...")
    main_data = load_json_file(main_file)
    
    if not main_data:
        print("❌ Failed to load main data file")
        return
    
    print(f"✅ Loaded {len(main_data)} players from main file")
    print()
    
    # Validate main data
    print("🔍 VALIDATING MAIN DATA...")
    main_validation = validate_player_data(main_data)
    
    print(f"📊 MAIN DATA SUMMARY:")
    print(f"   Total players: {main_validation['total_players']:,}")
    print(f"   Total series: {main_validation['series_analysis']['total_series']}")
    print(f"   Total clubs: {main_validation['club_analysis']['total_clubs']}")
    print(f"   Total captains: {main_validation['captain_analysis']['total_captains']}")
    print(f"   Players with PTI: {main_validation['pti_analysis']['players_with_pti']} ({main_validation['pti_analysis']['pti_percentage']})")
    print()
    
    # Field completeness
    print("📋 FIELD COMPLETENESS:")
    for field, stats in main_validation['required_fields'].items():
        status = "✅" if stats['missing_count'] == 0 else "⚠️" if stats['missing_count'] < 10 else "❌"
        print(f"   {status} {field}: {stats['completeness']} ({stats['missing_count']} missing)")
    print()
    
    # Captain analysis
    print("👑 CAPTAIN ANALYSIS:")
    print(f"   Total captains: {main_validation['captain_analysis']['total_captains']}")
    print(f"   Captain percentage: {main_validation['captain_analysis']['captain_percentage']}")
    print("   Captains by series (top 10):")
    for series, count in list(main_validation['captain_analysis']['captains_by_series'].most_common(10)):
        print(f"     {series}: {count} captains")
    print()
    
    # Series distribution
    print("📈 SERIES DISTRIBUTION:")
    print(f"   Total series: {main_validation['series_analysis']['total_series']}")
    print(f"   Average players per series: {main_validation['series_analysis']['players_per_series_avg']}")
    print("   Top 10 series by player count:")
    series_dist = main_validation['series_analysis']['series_distribution']
    for series, count in sorted(series_dist.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"     {series}: {count} players")
    print()
    
    # Club analysis
    print("🏢 CLUB ANALYSIS:")
    print(f"   Total clubs: {main_validation['club_analysis']['total_clubs']}")
    print(f"   Average players per club: {main_validation['club_analysis']['players_per_club_avg']}")
    print("   Top 10 clubs by player count:")
    for club, count in list(main_validation['club_analysis']['top_10_clubs'].items()):
        print(f"     {club}: {count} players")
    print()
    
    # PTI analysis
    print("🎯 PTI ANALYSIS:")
    print(f"   Players with PTI: {main_validation['pti_analysis']['players_with_pti']} ({main_validation['pti_analysis']['pti_percentage']})")
    if main_validation['pti_analysis']['pti_range'] != "N/A":
        print(f"   PTI range: {main_validation['pti_analysis']['pti_range']}")
        print(f"   PTI average: {main_validation['pti_analysis']['pti_avg']}")
    print()
    
    # Data quality issues
    print("⚠️ DATA QUALITY ISSUES:")
    if main_validation['issues']:
        for issue in main_validation['issues']:
            print(f"   ❌ {issue}")
    else:
        print("   ✅ No data quality issues found!")
    print()
    
    # Validate series files
    print("📁 VALIDATING SERIES FILES...")
    series_validation = validate_series_files(temp_dir)
    
    print(f"📊 SERIES FILES SUMMARY:")
    print(f"   Total series files: {series_validation['total_series_files']}")
    print(f"   Total players across files: {series_validation['total_players_across_files']:,}")
    
    if series_validation['consistency_issues']:
        print("   Issues found:")
        for issue in series_validation['consistency_issues']:
            print(f"     ❌ {issue}")
    else:
        print("   ✅ All series files loaded successfully")
    print()
    
    # Final assessment
    print("🎯 FINAL ASSESSMENT:")
    total_issues = main_validation['data_quality']['total_issues'] + len(series_validation['consistency_issues'])
    
    if total_issues == 0:
        print("   ✅ EXCELLENT: No data quality issues found!")
        print("   ✅ Data appears complete and accurate")
    elif total_issues < 5:
        print("   ⚠️ GOOD: Minor data quality issues found")
        print("   ⚠️ Data is mostly complete with some minor issues")
    else:
        print("   ❌ NEEDS ATTENTION: Multiple data quality issues found")
        print("   ❌ Data may have significant completeness or accuracy problems")
    
    print(f"   Total issues: {total_issues}")
    print()
    
    # Save validation report
    report = {
        'timestamp': datetime.now().isoformat(),
        'main_validation': main_validation,
        'series_validation': series_validation,
        'total_issues': total_issues
    }
    
    report_file = f"/Users/rossfreedman/dev/rally/data/leagues/APTA_CHICAGO/validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"📄 Validation report saved to: {report_file}")

if __name__ == "__main__":
    main()
