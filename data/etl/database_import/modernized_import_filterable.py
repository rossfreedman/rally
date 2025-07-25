#!/usr/bin/env python3
"""
Modernized Filterable ETL Script for JSON Data Import
=====================================================

This script provides incremental, filterable imports with upsert capabilities.
Key features:
- Filter by league, series, and data type
- Use tenniscores_match_id for reliable upserts
- Preserve data integrity without full overwrites
- Selective importing to avoid unnecessary data churn

Order of operations (selective based on user input):
1. Match scores (with upsert based on tenniscores_match_id)
2. Series stats
3. Players
4. Player history
5. Schedules
"""

import json
import os
import re
import sys
import time
import traceback
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
sys.path.insert(0, project_root)

import psycopg2
from psycopg2.extras import RealDictCursor

from database_config import get_db
from utils.league_utils import (
    get_league_display_name,
    get_league_url,
    normalize_league_id,
)


class ModernizedETLImporter:
    """Modernized ETL Importer with filtering and upsert capabilities"""
    
    def __init__(self):
        self.imported_counts = {
            "match_scores": 0,
            "series_stats": 0,
            "players": 0,
            "player_history": 0,
            "schedules": 0
        }
        self.batch_size = 500
        self.is_railway = os.environ.get("RAILWAY_ENVIRONMENT") is not None
        
    def log(self, message: str, level: str = "INFO"):
        """Enhanced logging with timestamps"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def get_user_filters(self):
        """Prompt user for filtering parameters"""
        print("\n" + "="*60)
        print("🎯 MODERNIZED ETL - SELECTIVE IMPORT CONFIGURATION")
        print("="*60)
        
        # Get league filter
        print("\nAvailable leagues: APTA_CHICAGO, CITA, CNSWPL, NSTF")
        league = input("Enter the league code (or 'all' for all leagues): ").strip().upper()
        if league == 'ALL':
            league = None
        
        # Get series filter
        series = input("Enter the series (e.g., '22', '7', '3a') or 'all' for all series: ").strip()
        if series.lower() == 'all':
            series = None
        
        # Get data type filters
        print("\nWhat type of data would you like to import?")
        print("1. Match scores")
        print("2. Series stats")
        print("3. Players")
        print("4. Player history")
        print("5. Schedules")
        print("6. All data types")
        
        choice = input("Enter the number(s) of the data type(s) to import (comma-separated): ").strip()
        
        # Parse data type choices
        data_types = []
        choices = [c.strip() for c in choice.split(',')]
        
        for c in choices:
            if c == '1':
                data_types.append('match_scores')
            elif c == '2':
                data_types.append('series_stats')
            elif c == '3':
                data_types.append('players')
            elif c == '4':
                data_types.append('player_history')
            elif c == '5':
                data_types.append('schedules')
            elif c == '6':
                data_types = ['match_scores', 'series_stats', 'players', 'player_history', 'schedules']
                break
        
        return {
            'league': league,
            'series': series,
            'data_types': data_types
        }
    
    def filter_match_data(self, match_data: List[Dict], filters: Dict) -> List[Dict]:
        """Filter match data based on user criteria"""
        if not filters['league'] and not filters['series']:
            return match_data
        
        filtered_data = []
        for match in match_data:
            # Apply league filter
            if filters['league']:
                match_league = normalize_league_id(match.get('league_id', ''))
                if match_league != filters['league']:
                    continue
            
            # Apply series filter
            if filters['series']:
                # Check home/away teams for series information
                home_team = match.get('Home Team', '')
                away_team = match.get('Away Team', '')
                
                # Extract series from team names (e.g., "Tennaqua - 22" -> "22")
                series_patterns = [
                    rf".*\s*-?\s*{re.escape(filters['series'])}\s*$",
                    rf".*\s+{re.escape(filters['series'])}\s*$",
                    rf"Series\s*{re.escape(filters['series'])}\s*$"
                ]
                
                series_found = False
                for pattern in series_patterns:
                    if re.search(pattern, home_team, re.IGNORECASE) or re.search(pattern, away_team, re.IGNORECASE):
                        series_found = True
                        break
                
                if not series_found:
                    continue
            
            filtered_data.append(match)
        
        return filtered_data
    
    def import_match_scores_with_upsert(self, conn, match_data: List[Dict], filters: Dict):
        """Import match scores using upsert based on tenniscores_match_id"""
        self.log("📥 Importing match scores with upsert logic...")
        
        # Filter data based on user criteria
        filtered_data = self.filter_match_data(match_data, filters)
        
        if not filtered_data:
            self.log("⚠️ No match data found for the specified filters")
            return
        
        self.log(f"🎯 Processing {len(filtered_data)} matches (filtered from {len(match_data)} total)")
        
        cursor = conn.cursor()
        imported = 0
        updated = 0
        errors = 0
        
        # Pre-cache league and team lookups
        self.log("🔧 Pre-caching league and team data...")
        
        cursor.execute("SELECT league_id, id FROM leagues")
        league_cache = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.execute("""
            SELECT l.league_id, t.team_name, t.id 
            FROM teams t 
            JOIN leagues l ON t.league_id = l.id
        """)
        team_cache = {(row[0], row[1]): row[2] for row in cursor.fetchall()}
        
        cursor.execute("SELECT tenniscores_player_id FROM players WHERE is_active = true")
        valid_player_ids = {row[0] for row in cursor.fetchall()}
        
        self.log(f"✅ Cached {len(league_cache)} leagues, {len(team_cache)} teams, {len(valid_player_ids):,} players")
        
        # Process matches in batches
        batch_data = []
        
        for record_idx, record in enumerate(filtered_data):
            try:
                # Extract core match data
                match_date_str = (record.get("Date") or "").strip()
                home_team = (record.get("Home Team") or "").strip()
                away_team = (record.get("Away Team") or "").strip()
                scores = record.get("Scores") or ""
                winner = (record.get("Winner") or "").strip()
                raw_league_id = (record.get("league_id") or "").strip()
                league_id = normalize_league_id(raw_league_id) if raw_league_id else ""
                
                # Generate unique tenniscores_match_id by combining match_id + Line
                base_match_id = record.get("match_id", "").strip()
                line = record.get("Line", "").strip()
                
                # Create unique tenniscores_match_id
                if base_match_id and line:
                    # Extract line number (e.g., "Line 1" -> "Line1", "Line 2" -> "Line2")
                    line_number = line.replace(" ", "")  # "Line 1" -> "Line1"
                    tenniscores_match_id = f"{base_match_id}_{line_number}"
                else:
                    # Fallback: use original match_id if line info is missing
                    tenniscores_match_id = base_match_id
                
                # Extract and validate player IDs
                home_player_1_id = (record.get("Home Player 1 ID") or "").strip()
                home_player_2_id = (record.get("Home Player 2 ID") or "").strip()
                away_player_1_id = (record.get("Away Player 1 ID") or "").strip()
                away_player_2_id = (record.get("Away Player 2 ID") or "").strip()
                
                # Validate player IDs against cache
                player_ids = [home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id]
                validated_ids = []
                
                for pid in player_ids:
                    if pid and pid in valid_player_ids:
                        validated_ids.append(pid)
                    else:
                        validated_ids.append(None)
                
                home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id = validated_ids
                
                # Parse date
                match_date = None
                if match_date_str:
                    try:
                        match_date = datetime.strptime(match_date_str, "%d-%b-%y").date()
                    except ValueError:
                        try:
                            match_date = datetime.strptime(match_date_str, "%m/%d/%Y").date()
                        except ValueError:
                            try:
                                match_date = datetime.strptime(match_date_str, "%Y-%m-%d").date()
                            except ValueError:
                                pass
                
                if not all([match_date, home_team, away_team]):
                    continue
                
                # Validate winner field
                if winner and winner.lower() not in ["home", "away"]:
                    winner = None
                
                # Use cached lookups
                league_db_id = league_cache.get(league_id)
                home_team_id = team_cache.get((league_id, home_team)) if home_team != "BYE" else None
                away_team_id = team_cache.get((league_id, away_team)) if away_team != "BYE" else None
                
                # Add to batch (including tenniscores_match_id)
                batch_data.append((
                    match_date, home_team, away_team, home_team_id, away_team_id,
                    home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id,
                    str(scores), winner, league_db_id, tenniscores_match_id
                ))
                
                # Process batch when it reaches batch_size
                if len(batch_data) >= self.batch_size or record_idx == len(filtered_data) - 1:
                    batch_imported, batch_updated = self._process_match_upsert_batch(cursor, batch_data)
                    imported += batch_imported
                    updated += batch_updated
                    batch_data = []
                    
                    conn.commit()
                    
                    if (imported + updated) % 1000 == 0:
                        self.log(f"   📊 Processed {imported + updated:,} matches so far (inserted: {imported}, updated: {updated})...")
                
            except Exception as e:
                errors += 1
                if errors <= 10:
                    self.log(f"❌ Error processing match record {record_idx}: {str(e)}", "ERROR")
                
                if errors > 100:
                    self.log(f"❌ Too many match errors ({errors}), stopping", "ERROR")
                    break
        
        # Process any remaining batch data
        if batch_data:
            batch_imported, batch_updated = self._process_match_upsert_batch(cursor, batch_data)
            imported += batch_imported
            updated += batch_updated
            conn.commit()
        
        self.imported_counts["match_scores"] = imported
        self.log(f"✅ Match scores complete: {imported:,} inserted, {updated:,} updated ({errors} errors)")
    
    def _process_match_upsert_batch(self, cursor, batch_data):
        """Process a batch of match records using UPSERT logic"""
        if not batch_data:
            return 0, 0
        
        inserted_count = 0
        updated_count = 0
        
        try:
            # Use UPSERT with ON CONFLICT for tenniscores_match_id
            for record in batch_data:
                (match_date, home_team, away_team, home_team_id, away_team_id,
                 home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id,
                 scores, winner, league_id, tenniscores_match_id) = record
                
                # Only use upsert if we have a valid tenniscores_match_id
                if tenniscores_match_id:
                    cursor.execute(
                        """
                        INSERT INTO match_scores (
                            match_date, home_team, away_team, home_team_id, away_team_id,
                            home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id, 
                            scores, winner, league_id, tenniscores_match_id, created_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (tenniscores_match_id) WHERE tenniscores_match_id IS NOT NULL DO UPDATE
                        SET 
                            match_date = EXCLUDED.match_date,
                            home_team = EXCLUDED.home_team,
                            away_team = EXCLUDED.away_team,
                            home_team_id = EXCLUDED.home_team_id,
                            away_team_id = EXCLUDED.away_team_id,
                            home_player_1_id = EXCLUDED.home_player_1_id,
                            home_player_2_id = EXCLUDED.home_player_2_id,
                            away_player_1_id = EXCLUDED.away_player_1_id,
                            away_player_2_id = EXCLUDED.away_player_2_id,
                            scores = EXCLUDED.scores,
                            winner = EXCLUDED.winner,
                            league_id = EXCLUDED.league_id
                        """,
                        record
                    )
                    
                    # For upserts in PostgreSQL, rowcount is always 1
                    # We need to track if it was an insert or update differently
                    if cursor.rowcount == 1:
                        # This could be either insert or update, we'll count as insert for now
                        # In a production system, we could use RETURNING clause to distinguish
                        inserted_count += 1
                else:
                    # For records without tenniscores_match_id, check for duplicates first
                    # Use match_date, home_team, away_team, and scores as duplicate detection
                    match_date, home_team, away_team = record[0], record[1], record[2]
                    scores = record[9]  # scores field
                    
                    cursor.execute(
                        """
                        SELECT id FROM match_scores 
                        WHERE match_date = %s 
                        AND home_team = %s 
                        AND away_team = %s 
                        AND scores = %s
                        LIMIT 1
                        """,
                        [match_date, home_team, away_team, scores]
                    )
                    
                    existing_record = cursor.fetchone()
                    
                    if existing_record:
                        # Record already exists, skip it (we could count this as skipped if needed)
                        pass
                    else:
                        # Record doesn't exist, insert it
                        cursor.execute(
                            """
                            INSERT INTO match_scores (
                                match_date, home_team, away_team, home_team_id, away_team_id,
                                home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id, 
                                scores, winner, league_id, created_at
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                            """,
                            record[:-1]  # Exclude tenniscores_match_id for regular insert
                        )
                        inserted_count += 1
            
            return inserted_count, updated_count
            
        except Exception as e:
            self.log(f"❌ Batch upsert failed: {str(e)}", "ERROR")
            return 0, 0
    
    def load_json_data(self, data_type: str, league_filter: Optional[str] = None):
        """Load JSON data for the specified type and league"""
        data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(script_dir))),
            "data", "leagues", "all"
        )
        
        filename_map = {
            'match_scores': 'match_history.json',
            'series_stats': 'series_stats.json',
            'players': 'players.json',
            'player_history': 'player_history.json',
            'schedules': 'schedules.json'
        }
        
        if data_type not in filename_map:
            self.log(f"❌ Unknown data type: {data_type}", "ERROR")
            return []
        
        file_path = os.path.join(data_dir, filename_map[data_type])
        
        if not os.path.exists(file_path):
            self.log(f"❌ File not found: {file_path}", "ERROR")
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.log(f"📂 Loaded {len(data):,} records from {filename_map[data_type]}")
            return data
        
        except Exception as e:
            self.log(f"❌ Error loading {file_path}: {str(e)}", "ERROR")
            return []
    
    def run_import(self):
        """Main import function with user interaction"""
        self.log("🚀 Starting Modernized ETL Import Process")
        
        # Get user filters
        filters = self.get_user_filters()
        
        self.log(f"\n📋 Import Configuration:")
        self.log(f"   League: {filters['league'] or 'All leagues'}")
        self.log(f"   Series: {filters['series'] or 'All series'}")
        self.log(f"   Data Types: {', '.join(filters['data_types'])}")
        
        # Confirm before proceeding
        confirm = input(f"\nProceed with import? (y/N): ").strip().lower()
        if confirm != 'y':
            self.log("❌ Import cancelled by user")
            return
        
        # Connect to database (will be used in context manager)
        try:
            # Test connection first
            with get_db() as test_conn:
                pass
            self.log("✅ Database connection test successful")
        except Exception as e:
            self.log(f"❌ Database connection failed: {str(e)}", "ERROR")
            return
        
        try:
            start_time = time.time()
            
            # Process each selected data type
            with get_db() as conn:
                for data_type in filters['data_types']:
                    self.log(f"\n🔄 Processing {data_type}...")
                    
                    if data_type == 'match_scores':
                        match_data = self.load_json_data('match_scores', filters['league'])
                        if match_data:
                            self.import_match_scores_with_upsert(conn, match_data, filters)
                    
                    # TODO: Add other data type handlers (series_stats, players, etc.)
                    # For now, focusing on match_scores as requested
                    elif data_type in ['series_stats', 'players', 'player_history', 'schedules']:
                        self.log(f"⚠️ {data_type} import not yet implemented in modernized ETL")
            
            # Final summary
            end_time = time.time()
            duration = end_time - start_time
            
            self.log(f"\n🎉 Import Complete! ({duration:.1f}s)")
            for data_type, count in self.imported_counts.items():
                if count > 0:
                    self.log(f"   {data_type}: {count:,} records")
        
        except Exception as e:
            self.log(f"❌ Import failed: {str(e)}", "ERROR")
            traceback.print_exc()
        
        finally:
            self.log("🔌 Database operations complete")


if __name__ == "__main__":
    importer = ModernizedETLImporter()
    importer.run_import() 