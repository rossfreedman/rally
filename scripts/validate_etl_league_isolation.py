#!/usr/bin/env python3
"""
Validate ETL League Isolation
=============================

Final validation that ETL scripts properly handle league isolation.
"""

import re
from pathlib import Path

def validate_file(file_path):
    """Validate a specific file for league isolation"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        issues = []
        good_practices = []
        
        # Check for critical bad patterns
        # 1. Series INSERT without league_id
        bad_insert_pattern = r'INSERT INTO series \([^)]*name[^)]*\) VALUES[^(]*\([^)]*%s[^)]*\)(?![^;]*league_id)'
        bad_inserts = re.findall(bad_insert_pattern, content, re.IGNORECASE | re.DOTALL)
        if bad_inserts:
            issues.append(f"Series INSERT without league_id: {len(bad_inserts)} instances")
        
        # 2. Series SELECT without league_id filter
        bad_select_pattern = r'SELECT[^;]*FROM series[^;]*WHERE[^;]*name = %s(?![^;]*league_id)'
        bad_selects = re.findall(bad_select_pattern, content, re.IGNORECASE | re.DOTALL)
        if bad_selects:
            issues.append(f"Series SELECT without league_id filter: {len(bad_selects)} instances")
        
        # Check for good patterns
        # 1. Proper ensure_series function signature
        good_ensure_series = re.search(r'def ensure_series\([^)]*league_id[^)]*int[^)]*\)', content)
        if good_ensure_series:
            good_practices.append("ensure_series function accepts league_id parameter")
        
        # 2. Proper series INSERT with league_id
        good_insert = re.search(r'INSERT INTO series[^;]*league_id[^;]*VALUES', content, re.IGNORECASE)
        if good_insert:
            good_practices.append("Series INSERT includes league_id")
        
        # 3. Proper series SELECT with league_id
        good_select = re.search(r'SELECT[^;]*FROM series[^;]*WHERE[^;]*league_id', content, re.IGNORECASE)
        if good_select:
            good_practices.append("Series SELECT filters by league_id")
        
        # 4. Composite unique constraint usage
        composite_constraint = re.search(r'ON CONFLICT.*name.*league_id', content, re.IGNORECASE)
        if composite_constraint:
            good_practices.append("Uses composite unique constraint (name, league_id)")
        
        return {
            'issues': issues,
            'good_practices': good_practices,
            'status': 'GOOD' if not issues else 'NEEDS_FIX'
        }
        
    except Exception as e:
        return {
            'issues': [f"Error reading file: {e}"],
            'good_practices': [],
            'status': 'ERROR'
        }

def main():
    """Main validation function"""
    project_root = Path(__file__).parent.parent
    etl_dir = project_root / "data" / "etl" / "database_import"
    
    # Critical ETL files that handle series
    critical_files = [
        "bootstrap_series_from_players.py",
        "bootstrap_teams_from_players.py", 
        "comprehensive_series_team_bootstrap.py",
        "enhanced_bootstrap_system.py",
        "import_stats.py"
    ]
    
    print("🔍 FINAL ETL LEAGUE ISOLATION VALIDATION")
    print("=" * 60)
    
    all_good = True
    total_issues = 0
    
    for filename in critical_files:
        file_path = etl_dir / filename
        if not file_path.exists():
            print(f"⚠️ {filename}: FILE NOT FOUND")
            all_good = False
            continue
        
        result = validate_file(file_path)
        status = result['status']
        issues = result['issues']
        good_practices = result['good_practices']
        
        emoji = "✅" if status == "GOOD" else "❌"
        print(f"\n{emoji} {filename}: {status}")
        
        if issues:
            total_issues += len(issues)
            for issue in issues:
                print(f"   ❌ {issue}")
            all_good = False
        
        if good_practices:
            for practice in good_practices[:2]:  # Show first 2
                print(f"   ✅ {practice}")
            if len(good_practices) > 2:
                print(f"   ... and {len(good_practices) - 2} more good practices")
    
    print("\n" + "=" * 60)
    
    if all_good:
        print("🎉 ALL ETL SCRIPTS ARE PROPERLY HANDLING LEAGUE ISOLATION!")
        print("✅ Ready for production ETL runs")
        print("✅ Series conflicts will not be recreated")
    else:
        print(f"⚠️ FOUND {total_issues} ISSUES ACROSS ETL SCRIPTS")
        print("❌ ETL runs may recreate series conflicts")
        print("🔧 Fix required before next import")
    
    print("\n💡 SUMMARY:")
    print("- All series creation should include league_id")
    print("- All series lookups should filter by league_id") 
    print("- Use composite constraints (name, league_id)")
    print("- Test on staging before production")
    
    return 0 if all_good else 1

if __name__ == "__main__":
    exit(main())
