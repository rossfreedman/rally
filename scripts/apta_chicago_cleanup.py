#!/usr/bin/env python3
"""
APTA Chicago Database Cleanup Script

This script makes the APTA Chicago database match the JSON source data exactly.
It removes invalid series, adds missing series, fixes club structure, and ensures
1:1 match between database and JSON data.

Usage:
    python scripts/apta_chicago_cleanup.py --dry-run    # Show what would be done
    python scripts/apta_chicago_cleanup.py --execute    # Perform cleanup
"""

import argparse
import json
import sys
import os
from datetime import datetime
from pathlib import Path
from collections import defaultdict, Counter

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database_utils import execute_query, execute_query_one, get_db
from database_config import get_db

class APTACleanupScript:
    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        self.apta_league_id = None
        self.json_data = None
        self.changes_made = []
        
    def load_json_data(self):
        """Load and analyze the JSON source data."""
        print("📊 Loading JSON source data...")
        
        json_path = project_root / "data" / "leagues" / "APTA_CHICAGO" / "players.json"
        if not json_path.exists():
            raise FileNotFoundError(f"JSON file not found: {json_path}")
            
        with open(json_path, 'r') as f:
            self.json_data = json.load(f)
            
        print(f"✅ Loaded {len(self.json_data):,} players from JSON")
        return self.json_data
        
    def get_league_id(self):
        """Get APTA Chicago league ID from database."""
        print("🔍 Finding APTA Chicago league ID...")
        
        result = execute_query_one("SELECT id FROM leagues WHERE league_id = 'APTA_CHICAGO'")
        if not result:
            raise ValueError("APTA_CHICAGO league not found in database")
            
        self.apta_league_id = result['id']
        print(f"✅ Found APTA Chicago league ID: {self.apta_league_id}")
        return self.apta_league_id
        
    def analyze_current_state(self):
        """Analyze current database state vs JSON."""
        print("\n📈 Analyzing current database state...")
        
        # Get current player count
        player_count = execute_query_one(
            "SELECT COUNT(*) as count FROM players WHERE league_id = %s",
            [self.apta_league_id]
        )['count']
        
        # Get current series
        series_data = execute_query("""
            SELECT s.name, COUNT(p.id) as player_count
            FROM series s
            LEFT JOIN players p ON s.id = p.series_id AND p.league_id = %s
            WHERE s.league_id = %s
            GROUP BY s.name
            ORDER BY s.name
        """, [self.apta_league_id, self.apta_league_id])
        
        current_series = {row['name']: row['player_count'] for row in series_data}
        
        # Analyze JSON data
        json_series = Counter(player['Series'] for player in self.json_data)
        
        print(f"📊 Current state:")
        print(f"   Database players: {player_count:,}")
        print(f"   JSON players: {len(self.json_data):,}")
        print(f"   Database series: {len(current_series)}")
        print(f"   JSON series: {len(json_series)}")
        
        return {
            'db_players': player_count,
            'json_players': len(self.json_data),
            'db_series': current_series,
            'json_series': dict(json_series)
        }
        
    def identify_invalid_series(self, current_state):
        """Identify series that exist in DB but not in JSON."""
        db_series = set(current_state['db_series'].keys())
        json_series = set(current_state['json_series'].keys())
        
        invalid_series = db_series - json_series
        missing_series = json_series - db_series
        
        print(f"\n🔍 Series analysis:")
        print(f"   Invalid series in DB: {len(invalid_series)}")
        print(f"   Missing series in DB: {len(missing_series)}")
        
        if invalid_series:
            print(f"   Invalid series to remove:")
            for series in sorted(invalid_series):
                count = current_state['db_series'][series]
                print(f"     {series}: {count:,} players")
                
        if missing_series:
            print(f"   Missing series to add:")
            for series in sorted(missing_series):
                count = current_state['json_series'][series]
                print(f"     {series}: {count:,} players")
                
        return invalid_series, missing_series
        
    def remove_invalid_series(self, invalid_series):
        """Remove invalid series and their players."""
        if not invalid_series:
            print("✅ No invalid series to remove")
            return
            
        print(f"\n🗑️  Removing {len(invalid_series)} invalid series...")
        
        total_players_removed = 0
        
        for series_name in sorted(invalid_series):
            # Get series ID
            series_result = execute_query_one(
                "SELECT id FROM series WHERE name = %s AND league_id = %s",
                [series_name, self.apta_league_id]
            )
            
            if not series_result:
                print(f"   ⚠️  Series '{series_name}' not found, skipping")
                continue
                
            series_id = series_result['id']
            
            # Count players to remove
            player_count = execute_query_one(
                "SELECT COUNT(*) as count FROM players WHERE series_id = %s AND league_id = %s",
                [series_id, self.apta_league_id]
            )['count']
            
            if player_count == 0:
                print(f"   ⚠️  Series '{series_name}' has no players, skipping")
                continue
                
            print(f"   Removing series '{series_name}': {player_count:,} players")
            
            if not self.dry_run:
                # Remove players from this series
                execute_query(
                    "DELETE FROM players WHERE series_id = %s AND league_id = %s",
                    [series_id, self.apta_league_id]
                )
                
                # Remove the series
                execute_query(
                    "DELETE FROM series WHERE id = %s",
                    [series_id]
                )
                
                self.changes_made.append(f"Removed series '{series_name}' with {player_count:,} players")
                
            total_players_removed += player_count
            
        print(f"   ✅ Would remove {total_players_removed:,} players from invalid series")
        
    def add_missing_series(self, missing_series):
        """Add missing series to database."""
        if not missing_series:
            print("✅ No missing series to add")
            return
            
        print(f"\n➕ Adding {len(missing_series)} missing series...")
        
        for series_name in sorted(missing_series):
            print(f"   Adding series '{series_name}'")
            
            if not self.dry_run:
                # Add the series
                execute_query(
                    "INSERT INTO series (name, display_name, league_id) VALUES (%s, %s, %s)",
                    [series_name, series_name, self.apta_league_id]
                )
                
                self.changes_made.append(f"Added series '{series_name}'")
                
    def fix_club_structure(self):
        """Fix club structure to match JSON exactly."""
        print(f"\n🏢 Analyzing club structure...")
        
        # Get current clubs
        current_clubs = execute_query("""
            SELECT c.name, COUNT(p.id) as player_count
            FROM clubs c
            LEFT JOIN players p ON c.id = p.club_id AND p.league_id = %s
            GROUP BY c.name
            ORDER BY c.name
        """, [self.apta_league_id])
        
        current_club_names = {row['name'] for row in current_clubs}
        
        # Get JSON clubs
        json_clubs = set(player['Club'] for player in self.json_data)
        
        missing_clubs = json_clubs - current_club_names
        extra_clubs = current_club_names - json_clubs
        
        print(f"   Current clubs: {len(current_clubs)}")
        print(f"   JSON clubs: {len(json_clubs)}")
        print(f"   Missing clubs: {len(missing_clubs)}")
        print(f"   Extra clubs: {len(extra_clubs)}")
        
        if missing_clubs:
            print(f"\n➕ Adding {len(missing_clubs)} missing clubs...")
            
            for club_name in sorted(list(missing_clubs)[:10]):  # Show first 10
                print(f"   Would add club: {club_name}")
                
            if len(missing_clubs) > 10:
                print(f"   ... and {len(missing_clubs) - 10} more clubs")
                
            if not self.dry_run:
                # Add missing clubs
                for club_name in missing_clubs:
                    execute_query(
                        "INSERT INTO clubs (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
                        [club_name]
                    )
                    
                self.changes_made.append(f"Added {len(missing_clubs)} missing clubs")
                
    def validate_results(self):
        """Validate that database now matches JSON exactly."""
        print(f"\n✅ Validating results...")
        
        # Re-analyze state
        current_state = self.analyze_current_state()
        
        # Check player count
        if current_state['db_players'] == current_state['json_players']:
            print(f"   ✅ Player count matches: {current_state['db_players']:,}")
        else:
            print(f"   ❌ Player count mismatch: DB={current_state['db_players']:,}, JSON={current_state['json_players']:,}")
            
        # Check series
        db_series = set(current_state['db_series'].keys())
        json_series = set(current_state['json_series'].keys())
        
        if db_series == json_series:
            print(f"   ✅ Series match: {len(db_series)} series")
        else:
            print(f"   ❌ Series mismatch:")
            print(f"      Extra in DB: {db_series - json_series}")
            print(f"      Missing in DB: {json_series - db_series}")
            
        return db_series == json_series and current_state['db_players'] == current_state['json_players']
        
    def run_cleanup(self):
        """Run the complete cleanup process."""
        print("🧹 APTA Chicago Database Cleanup")
        print("=" * 50)
        print(f"Mode: {'DRY RUN' if self.dry_run else 'EXECUTE'}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        try:
            # Load data
            self.load_json_data()
            self.get_league_id()
            
            # Analyze current state
            current_state = self.analyze_current_state()
            
            # Identify issues
            invalid_series, missing_series = self.identify_invalid_series(current_state)
            
            # Remove invalid series
            self.remove_invalid_series(invalid_series)
            
            # Add missing series
            self.add_missing_series(missing_series)
            
            # Fix club structure
            self.fix_club_structure()
            
            # Validate results
            success = self.validate_results()
            
            print(f"\n{'🎯 DRY RUN COMPLETE' if self.dry_run else '🎯 CLEANUP COMPLETE'}")
            print("=" * 50)
            
            if self.changes_made:
                print("Changes made:")
                for change in self.changes_made:
                    print(f"  ✅ {change}")
            else:
                print("No changes needed")
                
            if success:
                print("\n✅ SUCCESS: Database now matches JSON exactly!")
            else:
                print("\n⚠️  Some issues remain - manual review needed")
                
            return success
            
        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

def main():
    parser = argparse.ArgumentParser(description='Clean up APTA Chicago database to match JSON exactly')
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='Show what would be done without making changes (default)')
    parser.add_argument('--execute', action='store_true',
                       help='Actually perform the cleanup (overrides --dry-run)')
    
    args = parser.parse_args()
    
    # If --execute is specified, override dry_run
    dry_run = not args.execute
    
    if not dry_run:
        print("⚠️  WARNING: This will modify the database!")
        print("Make sure you have a backup before proceeding.")
        response = input("Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            return
            
    script = APTACleanupScript(dry_run=dry_run)
    success = script.run_cleanup()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

