#!/usr/bin/env python3
"""
Surgical removal of women players from APTA Chicago players.json
This script removes women players by individual player records, not by series or club
"""

import json
import shutil
from datetime import datetime

def is_women_name(first_name):
    """Check if a first name is commonly associated with women - CORRECTED VERSION"""
    women_names = {
        'alicia', 'amy', 'andrea', 'angela', 'anne', 'ann', 'april', 'ashley', 'audrey',
        'barbara', 'beth', 'bonnie', 'brenda', 'brittany', 'carla', 'carol', 'carolyn',
        'cassandra', 'catherine', 'charlene', 'charlotte', 'cheryl', 'christina', 'christine',
        'claire', 'claudia', 'constance', 'cynthia', 'darlene', 'dawn', 'deborah', 'debra',
        'delores', 'denise', 'diana', 'diane', 'donna', 'dorothy', 'doris', 'edith',
        'eleanor', 'elaine', 'elizabeth', 'ella', 'ellen', 'elena', 'elisa', 'elise',
        'emily', 'esther', 'evelyn', 'faye', 'frances', 'gail', 'gayle', 'gloria', 'grace',
        'gwendolyn', 'harriet', 'hazel', 'heather', 'helen', 'ida', 'irene', 'jacqueline',
        'jane', 'janet', 'janice', 'jennifer', 'jenny', 'jessica', 'jill',
        'joan', 'joanne', 'joy', 'joyce', 'judith', 'judy', 'julia', 'julie', 'karen',
        'karla', 'kate', 'katherine', 'kathleen', 'kathryn', 'kathy', 'kelli', 'kelly',
        'kim', 'kimberly', 'kristen', 'kristin', 'kristi', 'laura', 'lauren', 'leah',
        'lena', 'lillian', 'linda', 'lisa', 'lois', 'lori', 'lorraine', 'louise', 'lucia',
        'lucille', 'lucy', 'lynn', 'marcia', 'margaret', 'maria', 'marie', 'marilyn',
        'marlene', 'martha', 'mary', 'maxine', 'megan', 'melissa', 'michelle', 'mildred',
        'minnie', 'monica', 'myrtle', 'nancy', 'nellie', 'nicole', 'norma', 'nina',
        'opal', 'pamela', 'patricia', 'patti', 'paula', 'peggy', 'penny', 'phyllis',
        'priscilla', 'rachel', 'ramona', 'rebecca', 'renee', 'rhonda', 'rita', 'roberta',
        'rosa', 'rose', 'rosemary', 'rosie', 'roxanne', 'ruby', 'ruth',
        'sabrina', 'sally', 'sandra', 'sandy', 'sarah', 'sharon', 'shelley', 'sherry',
        'shirley', 'stacey', 'stacy', 'stephanie', 'sue', 'susan', 'sylvia', 'tamara',
        'tammy', 'tanya', 'teresa', 'teri', 'tiffany', 'tina', 'toni', 'tonya', 'tracy',
        'tracey', 'traci', 'valerie', 'vanessa', 'vera', 'vicki', 'vickie', 'victoria',
        'violet', 'virginia', 'vivian', 'wanda', 'wendy', 'willa', 'winona', 'yvette',
        'yvonne', 'zoe'
    }
    
    # Remove ambiguous names that can be both male and female
    ambiguous_names = {'jean', 'jordan', 'taylor', 'casey', 'morgan', 'alex', 'sam', 'chris', 'pat', 'terry', 'dana', 'jamie', 'lee', 'robin', 'sandy', 'tracy', 'tracey'}
    
    # Remove ambiguous names from women's list
    women_names = women_names - ambiguous_names
    
    return first_name.lower() in women_names

def remove_women_from_apta():
    """Remove women players from APTA Chicago players.json"""
    
    input_file = '/Users/rossfreedman/dev/rally/data/leagues/APTA_CHICAGO/players.json'
    backup_file = f'/Users/rossfreedman/dev/rally/data/leagues/APTA_CHICAGO/players_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    
    print("🔍 Reading APTA Chicago players.json...")
    
    # Create backup first
    print(f"💾 Creating backup: {backup_file}")
    shutil.copy2(input_file, backup_file)
    
    # Read the JSON file
    with open(input_file, 'r') as f:
        players = json.load(f)
    
    print(f"📊 Total players before removal: {len(players)}")
    
    # Identify women and men
    women_players = []
    men_players = []
    
    for player in players:
        first_name = player.get('First Name', '').strip()
        if is_women_name(first_name):
            women_players.append(player)
        else:
            men_players.append(player)
    
    print(f"👩 Women players to remove: {len(women_players)}")
    print(f"👨 Men players to keep: {len(men_players)}")
    
    # Show some examples of women being removed
    print("\n🚫 Sample women players being removed:")
    for i, player in enumerate(women_players[:10]):  # Show first 10
        print(f"  {i+1}. {player.get('First Name', '')} {player.get('Last Name', '')} - {player.get('Team', '')} - {player.get('Series', '')}")
    if len(women_players) > 10:
        print(f"  ... and {len(women_players) - 10} more women players")
    
    # Write the cleaned data (men only)
    print(f"\n✍️  Writing cleaned data with {len(men_players)} men players...")
    with open(input_file, 'w') as f:
        json.dump(men_players, f, indent=2)
    
    print("✅ Women players successfully removed from APTA Chicago!")
    print(f"📁 Backup saved as: {backup_file}")
    
    # Verification
    print("\n🔍 Verification:")
    with open(input_file, 'r') as f:
        cleaned_players = json.load(f)
    
    # Check for any remaining women
    remaining_women = []
    for player in cleaned_players:
        first_name = player.get('First Name', '').strip()
        if is_women_name(first_name):
            remaining_women.append(player)
    
    if remaining_women:
        print(f"⚠️  WARNING: {len(remaining_women)} women players still remain!")
        for player in remaining_women:
            print(f"  - {player.get('First Name', '')} {player.get('Last Name', '')}")
    else:
        print("✅ No women players remain - removal successful!")
    
    print(f"📊 Final count: {len(cleaned_players)} players (all men)")
    
    return {
        'original_count': len(players),
        'women_removed': len(women_players),
        'men_remaining': len(men_players),
        'backup_file': backup_file
    }

def analyze_removal_impact():
    """Analyze the impact of removing women players"""
    
    input_file = '/Users/rossfreedman/dev/rally/data/leagues/APTA_CHICAGO/players.json'
    
    with open(input_file, 'r') as f:
        players = json.load(f)
    
    # Analyze by series
    women_by_series = {}
    men_by_series = {}
    
    for player in players:
        first_name = player.get('First Name', '').strip()
        series = player.get('Series', '')
        
        if is_women_name(first_name):
            if series not in women_by_series:
                women_by_series[series] = []
            women_by_series[series].append(player)
        else:
            if series not in men_by_series:
                men_by_series[series] = []
            men_by_series[series].append(player)
    
    print("\n📈 IMPACT ANALYSIS BY SERIES:")
    print("=" * 60)
    
    all_series = set(women_by_series.keys()) | set(men_by_series.keys())
    
    for series in sorted(all_series):
        women_count = len(women_by_series.get(series, []))
        men_count = len(men_by_series.get(series, []))
        
        if women_count > 0:
            print(f"{series}: Removing {women_count} women, keeping {men_count} men")
            
            # Show clubs affected
            women_clubs = set(p.get('Club', '') for p in women_by_series.get(series, []))
            men_clubs = set(p.get('Club', '') for p in men_by_series.get(series, []))
            shared_clubs = women_clubs.intersection(men_clubs)
            
            if shared_clubs:
                print(f"  ⚠️  Affected clubs: {', '.join(sorted(shared_clubs))}")
            else:
                print(f"  ✅ Women-only clubs: {', '.join(sorted(women_clubs))}")

if __name__ == "__main__":
    print("🎾 APTA Chicago Women Removal Tool")
    print("=" * 50)
    
    # Ask for confirmation
    response = input("\n⚠️  This will remove ALL women players from APTA Chicago. Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Operation cancelled.")
        exit(1)
    
    # Perform removal
    result = remove_women_from_apta()
    
    # Show impact analysis
    analyze_removal_impact()
    
    print(f"\n🎉 SUCCESS!")
    print(f"   • Removed {result['women_removed']} women players")
    print(f"   • Kept {result['men_remaining']} men players")
    print(f"   • Backup saved: {result['backup_file']}")
