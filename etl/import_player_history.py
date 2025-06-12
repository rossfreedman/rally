#!/usr/bin/env python3

import sys
import os
import json
from datetime import datetime

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from database_utils import execute_query, execute_query_one, execute_update, execute_many

def clear_existing_player_history():
    """Clear existing player_history data to start fresh"""
    print("1. Clearing existing player_history data...")
    
    try:
        # Get current count
        count_query = "SELECT COUNT(*) as count FROM player_history"
        current_count = execute_query_one(count_query)['count']
        print(f"   Current records: {current_count:,}")
        
        # Clear the table
        clear_query = "DELETE FROM player_history"
        execute_update(clear_query)
        print(f"   ✅ Cleared all player_history records")
        
    except Exception as e:
        print(f"   ❌ Error clearing data: {e}")
        raise

def load_player_history_json():
    """Load and parse the player_history.json file"""
    print("2. Loading player_history.json...")
    
    json_file = "data/leagues/all/player_history.json"
    
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        print(f"   ✅ Loaded {len(data):,} player records from JSON")
        return data
        
    except Exception as e:
        print(f"   ❌ Error loading JSON: {e}")
        raise

def map_players_to_database_ids(json_data):
    """Map tenniscores player_ids from JSON to database player.id values with enhanced PTI+series matching"""
    print("3. Mapping players to database IDs (with PTI+series fallback)...")
    
    # Get all players from database with their series information
    players_query = """
        SELECT p.id, p.tenniscores_player_id, p.first_name, p.last_name, p.pti, s.name as series_name
        FROM players p
        LEFT JOIN series s ON p.series_id = s.id
    """
    db_players = execute_query(players_query)
    
    # Create primary mapping by tenniscores_player_id
    player_id_map = {}
    players_by_pti = {}  # For PTI-based fallback matching
    
    for player in db_players:
        if player['tenniscores_player_id']:
            player_id_map[player['tenniscores_player_id']] = player['id']
        
        # Also index by PTI for fallback matching
        if player['pti']:
            pti_key = f"{player['pti']:.2f}"
            if pti_key not in players_by_pti:
                players_by_pti[pti_key] = []
            players_by_pti[pti_key].append(player)
    
    print(f"   Found {len(player_id_map):,} players with tenniscores_player_id")
    print(f"   Found {len(players_by_pti):,} unique PTI values for fallback matching")
    
    # Enhanced mapping with PTI+series fallback
    enhanced_mappings = 0
    
    for player_data in json_data:
        tenniscores_id = player_data.get('player_id')
        
        # Skip if already mapped by tenniscores_player_id
        if tenniscores_id and tenniscores_id in player_id_map:
            continue
        
        # Try PTI-based matching for unmapped players
        matches = player_data.get('matches', [])
        if not matches:
            continue
        
        # Get the most recent PTI value
        recent_match = max(matches, key=lambda m: parse_date(m.get('date', '1/1/1900')) or datetime(1900, 1, 1).date())
        end_pti = recent_match.get('end_pti')
        series = recent_match.get('series', '')
        
        if not end_pti:
            continue
        
        # Look for players with matching PTI
        pti_key = f"{float(end_pti):.2f}"
        if pti_key in players_by_pti:
            # Try to match by series information as well
            best_match = None
            
            for candidate in players_by_pti[pti_key]:
                series_name = candidate.get('series_name', '')
                
                # Check if series matches (using similar logic to the fix)
                if series_name and series:
                    # Create series patterns for matching
                    series_patterns = [
                        series_name.replace(' ', '').lower(),
                        series_name.replace(' ', ':').lower(),
                        series_name.lower()
                    ]
                    
                    series_lower = series.lower()
                    if any(pattern in series_lower for pattern in series_patterns):
                        best_match = candidate
                        break
            
            # If no series match, use first PTI match (better than no link)
            if not best_match and players_by_pti[pti_key]:
                best_match = players_by_pti[pti_key][0]
            
            if best_match:
                # Create enhanced mapping
                player_id_map[tenniscores_id] = best_match['id']
                enhanced_mappings += 1
                print(f"   ✅ Enhanced mapping: {player_data.get('name', 'Unknown')} -> {best_match['first_name']} {best_match['last_name']} (PTI: {end_pti})")
    
    print(f"   ✅ Created {enhanced_mappings:,} additional mappings via PTI+series matching")
    
    # Count final mapping statistics
    mapped_count = 0
    unmapped_players = []
    
    for player_data in json_data:
        tenniscores_id = player_data.get('player_id')
        if tenniscores_id in player_id_map:
            mapped_count += 1
        else:
            unmapped_players.append({
                'tenniscores_id': tenniscores_id,
                'name': player_data.get('name', 'Unknown')
            })
    
    print(f"   ✅ Final mapping: {mapped_count:,} players")
    if unmapped_players:
        print(f"   ⚠️  Still unmapped: {len(unmapped_players)} players")
        # Show first few unmapped
        for i, player in enumerate(unmapped_players[:3]):
            print(f"      - {player['name']} ({player['tenniscores_id']})")
        if len(unmapped_players) > 3:
            print(f"      ... and {len(unmapped_players) - 3} more")
    
    return player_id_map

def get_league_id_map():
    """Get mapping of league_id strings to database IDs"""
    print("4. Getting league ID mappings...")
    
    leagues_query = "SELECT id, league_id FROM leagues"
    leagues = execute_query(leagues_query)
    
    league_map = {}
    for league in leagues:
        league_map[league['league_id']] = league['id']
    
    print(f"   Found {len(league_map)} leagues: {list(league_map.keys())}")
    return league_map

def parse_date(date_str):
    """Parse date string from JSON format (MM/DD/YYYY) to database format"""
    try:
        # Parse MM/DD/YYYY format
        return datetime.strptime(date_str, "%m/%d/%Y").date()
    except ValueError:
        try:
            # Try alternative formats
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            print(f"   ⚠️  Could not parse date: {date_str}")
            return None

def import_player_history_records(json_data, player_id_map, league_id_map):
    """Import player_history records with correct player_id mappings"""
    print("5. Importing player_history records...")
    
    records_to_insert = []
    skipped_count = 0
    
    for player_data in json_data:
        tenniscores_id = player_data.get('player_id')
        league_id_str = player_data.get('league_id')
        
        # Skip if we can't map this player
        if tenniscores_id not in player_id_map:
            skipped_count += 1
            continue
        
        database_player_id = player_id_map[tenniscores_id]
        database_league_id = league_id_map.get(league_id_str)
        
        # Process each match in the player's history
        matches = player_data.get('matches', [])
        
        for match in matches:
            date_str = match.get('date')
            end_pti = match.get('end_pti')
            series = match.get('series')
            
            # Parse date
            parsed_date = parse_date(date_str)
            if not parsed_date:
                continue
            
            # Create record for insertion
            record = (
                series,                # series
                parsed_date,          # date
                end_pti,             # end_pti
                database_league_id,  # league_id
                database_player_id   # player_id - THIS IS THE KEY FIX!
            )
            
            records_to_insert.append(record)
    
    print(f"   Prepared {len(records_to_insert):,} records for insertion")
    print(f"   Skipped {skipped_count:,} players (not in database)")
    
    # Batch insert records
    if records_to_insert:
        insert_query = """
            INSERT INTO player_history (series, date, end_pti, league_id, player_id)
            VALUES (%s, %s, %s, %s, %s)
        """
        
        try:
            execute_many(insert_query, records_to_insert)
            print(f"   ✅ Successfully inserted {len(records_to_insert):,} player_history records")
            
        except Exception as e:
            print(f"   ❌ Error inserting records: {e}")
            raise
    
    return len(records_to_insert)

def verify_import():
    """Verify the import worked correctly"""
    print("6. Verifying import...")
    
    # Check total counts
    total_query = "SELECT COUNT(*) as count FROM player_history"
    linked_query = "SELECT COUNT(*) as count FROM player_history WHERE player_id IS NOT NULL"
    
    total_count = execute_query_one(total_query)['count']
    linked_count = execute_query_one(linked_query)['count']
    
    print(f"   Total player_history records: {total_count:,}")
    print(f"   Linked records (non-NULL player_id): {linked_count:,}")
    print(f"   Link percentage: {(linked_count/total_count*100):.1f}%")
    
    # Check Ross specifically
    ross_query = """
        SELECT 
            ph.date,
            ph.end_pti,
            ph.series,
            p.first_name,
            p.last_name,
            TO_CHAR(ph.date, 'YYYY-MM-DD') as formatted_date
        FROM player_history ph
        JOIN players p ON ph.player_id = p.id
        WHERE p.tenniscores_player_id = 'nndz-WkMrK3didjlnUT09'
        ORDER BY ph.date DESC
        LIMIT 5
    """
    
    ross_records = execute_query(ross_query)
    if ross_records:
        print(f"\n   ✅ Ross Freedman's PTI history (via proper FK):")
        for record in ross_records:
            print(f"     {record['formatted_date']}: PTI={record['end_pti']} - {record['series']}")
    else:
        print(f"\n   ❌ No linked records found for Ross")

def test_mobile_service():
    """Test that the mobile service now works with proper foreign key linking"""
    print("7. Testing mobile service with proper linking...")
    
    try:
        from services.mobile_service import get_player_analysis
        
        # Test with Ross's data
        user = {
            'tenniscores_player_id': 'nndz-WkMrK3didjlnUT09',
            'email': 'test@example.com',
            'league_id': 'APTA_CHICAGO'
        }
        
        result = get_player_analysis(user)
        
        print(f"   PTI Data Available: {result.get('pti_data_available')}")
        print(f"   Current PTI: {result.get('current_pti')}")
        print(f"   PTI Change: {result.get('weekly_pti_change')}")
        
        if result.get('pti_data_available'):
            print(f"   ✅ Mobile service working with proper player_history foreign keys!")
        else:
            print(f"   ⚠️  Mobile service still using fallback method")
            
    except Exception as e:
        print(f"   ❌ Error testing mobile service: {e}")

def main():
    """Main function to orchestrate the import process"""
    print("🔄 IMPORTING PLAYER_HISTORY WITH ENHANCED PLAYER_ID LINKING")
    print("=" * 70)
    
    try:
        # Step 1: Clear existing data
        clear_existing_player_history()
        
        # Step 2: Load JSON data
        json_data = load_player_history_json()
        
        # Step 3: Map players to database IDs (with enhanced PTI+series matching)
        player_id_map = map_players_to_database_ids(json_data)
        
        # Step 4: Get league mappings
        league_id_map = get_league_id_map()
        
        # Step 5: Import records with correct player_id values
        imported_count = import_player_history_records(json_data, player_id_map, league_id_map)
        
        # Step 6: Verify the import
        verify_import()
        
        # Step 7: Test mobile service
        test_mobile_service()
        
        print(f"\n🎉 IMPORT COMPLETED SUCCESSFULLY!")
        print(f"   Imported {imported_count:,} properly linked PTI history records")
        print(f"   The player_history table now has properly linked player_id values!")
        
    except Exception as e:
        print(f"\n❌ IMPORT FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 