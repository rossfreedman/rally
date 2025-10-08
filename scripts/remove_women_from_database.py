#!/usr/bin/env python3
"""
Remove women players from APTA Chicago database
Uses the final CSV list to remove women players from the database
"""

import csv
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one, execute_update

def backup_database_tables():
    """Create backup tables before removal"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print("📁 Creating database backups...")
    
    backup_queries = [
        f"CREATE TABLE players_backup_before_women_removal_{timestamp} AS SELECT * FROM players WHERE league_id = (SELECT id FROM leagues WHERE league_id = 'APTA_CHICAGO')",
        f"CREATE TABLE user_player_associations_backup_before_women_removal_{timestamp} AS SELECT * FROM user_player_associations",
        f"CREATE TABLE match_scores_backup_before_women_removal_{timestamp} AS SELECT * FROM match_scores WHERE league_id = (SELECT id FROM leagues WHERE league_id = 'APTA_CHICAGO')",
        f"CREATE TABLE series_stats_backup_before_women_removal_{timestamp} AS SELECT * FROM series_stats WHERE league_id = (SELECT id FROM leagues WHERE league_id = 'APTA_CHICAGO')"
    ]
    
    backup_tables = []
    for query in backup_queries:
        try:
            table_name = query.split('AS SELECT')[0].split()[-1]
            execute_update(query)
            backup_tables.append(table_name)
            print(f"  ✅ Created backup: {table_name}")
        except Exception as e:
            print(f"  ❌ Failed to create backup {table_name}: {e}")
            return None
    
    return backup_tables

def load_removal_list():
    """Load the list of women players to remove from the CSV file"""
    csv_file = '/Users/rossfreedman/dev/rally/final_women_players_to_remove_20250918_093646.csv'
    
    print(f"📋 Loading removal list from: {csv_file}")
    
    players_to_remove = []
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                players_to_remove.append({
                    'player_id': row['Player_ID'],
                    'name': row['Full_Name'],
                    'team': row['Team'],
                    'series': row['Series'],
                    'club': row['Club'],
                    'reason': row['Removal_Reason']
                })
        
        print(f"✅ Loaded {len(players_to_remove)} players to remove")
        return players_to_remove
        
    except Exception as e:
        print(f"❌ Failed to load removal list: {e}")
        return []

def get_apta_league_id():
    """Get the APTA Chicago league ID from database"""
    try:
        result = execute_query_one("SELECT id FROM leagues WHERE league_id = 'APTA_CHICAGO'")
        if result:
            return result['id']
        else:
            print("❌ APTA_CHICAGO league not found in database")
            return None
    except Exception as e:
        print(f"❌ Failed to get APTA league ID: {e}")
        return None

def remove_women_from_database():
    """Remove women players from the database"""
    
    print("🗑️  Removing women players from APTA Chicago database...")
    print("=" * 70)
    
    # Step 1: Get APTA league ID
    apta_league_id = get_apta_league_id()
    if not apta_league_id:
        return False
    
    print(f"✅ APTA Chicago League ID: {apta_league_id}")
    
    # Step 2: Create backups
    backup_tables = backup_database_tables()
    if not backup_tables:
        print("❌ Cannot proceed without database backups. Exiting.")
        return False
    
    # Step 3: Load removal list
    players_to_remove = load_removal_list()
    if not players_to_remove:
        print("❌ Cannot proceed without removal list. Exiting.")
        return False
    
    # Step 4: Get current counts
    print(f"\n📊 Current database counts:")
    
    player_count_query = "SELECT COUNT(*) as count FROM players WHERE league_id = %s"
    player_count = execute_query_one(player_count_query, [apta_league_id])['count']
    print(f"  • APTA players: {player_count}")
    
    association_count_query = "SELECT COUNT(*) as count FROM user_player_associations"
    association_count = execute_query_one(association_count_query)['count']
    print(f"  • User associations: {association_count}")
    
    match_count_query = "SELECT COUNT(*) as count FROM match_scores WHERE league_id = %s"
    match_count = execute_query_one(match_count_query, [apta_league_id])['count']
    print(f"  • APTA matches: {match_count}")
    
    # Step 5: Remove players and related data
    print(f"\n🗑️  Removing {len(players_to_remove)} women players and related data...")
    
    removed_players = 0
    removed_associations = 0
    removed_matches = 0
    removed_series_stats = 0
    
    for player_info in players_to_remove:
        player_id = player_info['player_id']
        
        try:
            # Remove from user_player_associations first (foreign key constraint)
            assoc_query = "DELETE FROM user_player_associations WHERE tenniscores_player_id = %s"
            assoc_result = execute_update(assoc_query, [player_id])
            if assoc_result:
                removed_associations += 1
            
            # Remove from players table
            player_query = "DELETE FROM players WHERE tenniscores_player_id = %s AND league_id = %s"
            player_result = execute_update(player_query, [player_id, apta_league_id])
            if player_result:
                removed_players += 1
                print(f"  ❌ Removed: {player_info['name']} ({player_id})")
            
        except Exception as e:
            print(f"  ⚠️  Failed to remove {player_info['name']} ({player_id}): {e}")
    
    # Step 6: Remove orphaned match scores (where both players are removed)
    print(f"\n🧹 Cleaning up orphaned match data...")
    
    # Remove matches where both home and away players are no longer in the database
    orphaned_matches_query = """
        DELETE FROM match_scores ms
        WHERE ms.league_id = %s
        AND NOT EXISTS (
            SELECT 1 FROM players p1 
            WHERE p1.tenniscores_player_id = ms.home_player_id 
            AND p1.league_id = %s
        )
        AND NOT EXISTS (
            SELECT 1 FROM players p2 
            WHERE p2.tenniscores_player_id = ms.away_player_id 
            AND p2.league_id = %s
        )
    """
    
    try:
        orphaned_result = execute_update(orphaned_matches_query, [apta_league_id, apta_league_id, apta_league_id])
        print(f"  ✅ Cleaned up orphaned matches")
    except Exception as e:
        print(f"  ⚠️  Failed to clean orphaned matches: {e}")
    
    # Step 7: Remove orphaned series stats
    orphaned_stats_query = """
        DELETE FROM series_stats ss
        WHERE ss.league_id = %s
        AND NOT EXISTS (
            SELECT 1 FROM players p 
            WHERE p.tenniscores_player_id = ss.player_id 
            AND p.league_id = %s
        )
    """
    
    try:
        orphaned_stats_result = execute_update(orphaned_stats_query, [apta_league_id, apta_league_id])
        print(f"  ✅ Cleaned up orphaned series stats")
    except Exception as e:
        print(f"  ⚠️  Failed to clean orphaned series stats: {e}")
    
    # Step 8: Get final counts
    print(f"\n📊 Final database counts:")
    
    final_player_count = execute_query_one(player_count_query, [apta_league_id])['count']
    print(f"  • APTA players: {final_player_count} (removed {player_count - final_player_count})")
    
    final_association_count = execute_query_one(association_count_query)['count']
    print(f"  • User associations: {final_association_count} (removed {association_count - final_association_count})")
    
    final_match_count = execute_query_one(match_count_query, [apta_league_id])['count']
    print(f"  • APTA matches: {final_match_count} (removed {match_count - final_match_count})")
    
    # Step 9: Verification - check for remaining women names
    print(f"\n🔍 VERIFICATION:")
    print("=" * 40)
    
    women_names_query = """
        SELECT DISTINCT p.first_name, p.last_name, COUNT(*) as count
        FROM players p
        WHERE p.league_id = %s
        AND LOWER(p.first_name) IN (
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
            'sabrina', 'sally', 'sandra', 'sarah', 'sharon', 'shelley', 'sherry',
            'shirley', 'stacey', 'stacy', 'stephanie', 'sue', 'susan', 'sylvia', 'tamara',
            'tammy', 'tanya', 'teresa', 'teri', 'tiffany', 'tina', 'toni', 'tonya', 'tracy',
            'valerie', 'vanessa', 'vera', 'vicki', 'vickie', 'victoria',
            'violet', 'virginia', 'vivian', 'wanda', 'wendy', 'willa', 'winona', 'yvette',
            'yvonne', 'zoe'
        )
        GROUP BY p.first_name, p.last_name
        ORDER BY p.first_name, p.last_name
    """
    
    remaining_women = execute_query(women_names_query, [apta_league_id])
    
    if remaining_women:
        print(f"⚠️  {len(remaining_women)} women names still in database:")
        for woman in remaining_women:
            print(f"  • {woman['first_name']} {woman['last_name']} ({woman['count']} records)")
    else:
        print("✅ No women names remaining in APTA Chicago database!")
    
    # Step 10: Create removal log
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f'/Users/rossfreedman/dev/rally/database_women_removal_log_{timestamp}.json'
    
    log_data = {
        'removal_date': datetime.now().isoformat(),
        'backup_tables': backup_tables,
        'apta_league_id': apta_league_id,
        'players_removed': removed_players,
        'associations_removed': removed_associations,
        'matches_removed': match_count - final_match_count,
        'series_stats_removed': match_count - final_match_count,  # Approximate
        'remaining_women_count': len(remaining_women),
        'remaining_women': remaining_women
    }
    
    try:
        import json
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        print(f"\n📝 Database removal log saved: {log_file}")
    except Exception as e:
        print(f"⚠️  Failed to save removal log: {e}")
    
    print(f"\n✅ DATABASE REMOVAL COMPLETED!")
    print(f"   • Backup tables: {len(backup_tables)}")
    print(f"   • Players removed: {removed_players}")
    print(f"   • Associations removed: {removed_associations}")
    print(f"   • Matches removed: {match_count - final_match_count}")
    print(f"   • Log file: {log_file}")
    
    return True

if __name__ == "__main__":
    success = remove_women_from_database()
    if success:
        print("\n🎉 Database cleanup completed!")
    else:
        print("\n❌ Database removal failed. Check logs above.")
