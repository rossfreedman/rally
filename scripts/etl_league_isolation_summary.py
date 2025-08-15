#!/usr/bin/env python3
"""
ETL League Isolation Summary
===========================

Quick summary of ETL scripts' league isolation status.
"""

import re
from pathlib import Path

def check_file_league_isolation(file_path):
    """Check if a file properly handles league isolation"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Look for ensure_series function signature
        ensure_series_with_league = bool(re.search(r'def ensure_series.*league_id.*int', content))
        
        # Look for INSERT with league_id
        insert_with_league = bool(re.search(r'INSERT INTO series.*league_id.*VALUES', content))
        
        # Look for SELECT with league_id filter
        select_with_league = bool(re.search(r'SELECT.*FROM series.*WHERE.*league_id', content))
        
        # Look for bad patterns (INSERT without league_id)
        bad_insert = bool(re.search(r'INSERT INTO series \(name\) VALUES', content))
        bad_select = bool(re.search(r'SELECT.*FROM series WHERE name = %s(?!.*league_id)', content))
        
        return {
            'ensure_series_good': ensure_series_with_league,
            'insert_good': insert_with_league,
            'select_good': select_with_league,
            'bad_insert': bad_insert,
            'bad_select': bad_select,
            'overall_status': 'GOOD' if (ensure_series_with_league or insert_with_league) and not (bad_insert or bad_select) else 'NEEDS_FIX'
        }
    except:
        return {'overall_status': 'ERROR'}

def main():
    project_root = Path(__file__).parent.parent
    etl_dir = project_root / "data" / "etl" / "database_import"
    
    critical_files = [
        "bootstrap_series_from_players.py",
        "bootstrap_teams_from_players.py", 
        "comprehensive_series_team_bootstrap.py",
        "enhanced_bootstrap_system.py",
        "import_stats.py",
        "master_import.py"
    ]
    
    print("🔍 ETL LEAGUE ISOLATION SUMMARY")
    print("=" * 50)
    
    for filename in critical_files:
        file_path = etl_dir / filename
        if file_path.exists():
            result = check_file_league_isolation(file_path)
            status = result['overall_status']
            emoji = "✅" if status == "GOOD" else "❌" if status == "NEEDS_FIX" else "⚠️"
            print(f"{emoji} {filename}: {status}")
            
            if status == "NEEDS_FIX":
                if result.get('bad_insert'):
                    print(f"   - Has INSERT without league_id")
                if result.get('bad_select'):
                    print(f"   - Has SELECT without league_id filter")
        else:
            print(f"⚠️ {filename}: FILE_NOT_FOUND")
    
    print("\n💡 RECOMMENDATION:")
    print("Run the comprehensive audit for detailed analysis.")

if __name__ == "__main__":
    main()
