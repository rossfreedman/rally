#!/usr/bin/env python3
"""
Comprehensive ETL Script for JSON Data Import
===========================================

This script imports data from JSON files in data/leagues/all/ into the PostgreSQL database
in the correct order based on foreign key constraints.

Order of operations:
1. Extract leagues from players.json -> import to leagues table
2. Extract clubs from players.json -> import to clubs table  
3. Extract series from players.json -> import to series table
4. Analyze club-league relationships -> populate club_leagues table
5. Analyze series-league relationships -> populate series_leagues table
6. Import players.json -> players table
7. Import career stats from player_history.json -> update players table career columns
8. Import player_history.json -> player_history table
9. Import match_history.json -> match_scores table
10. Import series_stats.json -> series_stats table
11. Import schedules.json -> schedule table
"""

import json
import sys
import os
from datetime import datetime, date
from decimal import Decimal
import traceback
from typing import Dict, List, Set, Any, Optional
import re

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
sys.path.insert(0, project_root)

from database_config import get_db
from utils.league_utils import normalize_league_id, get_league_display_name, get_league_url
import psycopg2
from psycopg2.extras import RealDictCursor

class ComprehensiveETL:
    def __init__(self):
        # Fix path calculation - script is in data/etl/database_import/, need to go up 3 levels to project root
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
        self.data_dir = os.path.join(project_root, 'data', 'leagues', 'all')
        self.imported_counts = {}
        self.errors = []
        
    def log(self, message: str, level: str = "INFO"):
        """Enhanced logging with timestamps"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def load_json_file(self, filename: str) -> List[Dict]:
        """Load and parse JSON file with error handling"""
        filepath = os.path.join(self.data_dir, filename)
        self.log(f"Loading {filename}...")
        
        try:
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"File not found: {filepath}")
                
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            self.log(f"✅ Loaded {len(data):,} records from {filename}")
            return data
            
        except Exception as e:
            self.log(f"❌ Error loading {filename}: {str(e)}", "ERROR")
            raise
            
    def clear_target_tables(self, conn):
        """Clear existing data from target tables in reverse dependency order"""
        self.log("🗑️  Clearing existing data from target tables...")
        
        tables_to_clear = [
            'schedule',           # No dependencies 
            'series_stats',       # References leagues, teams
            'match_scores',       # References players, leagues, teams
            'player_history',     # References players, leagues  
            'players',           # References leagues, clubs, series, teams
            'teams',             # References leagues, clubs, series
            'series_leagues',    # References series, leagues
            'club_leagues',      # References clubs, leagues
            'series',           # Referenced by others
            'clubs',            # Referenced by others
            'leagues'           # Referenced by others
        ]
        
        try:
            cursor = conn.cursor()
            
            # Disable foreign key checks temporarily
            cursor.execute("SET session_replication_role = replica;")
            
            for table in tables_to_clear:
                try:
                    cursor.execute(f"DELETE FROM {table}")
                    deleted_count = cursor.rowcount
                    self.log(f"   ✅ Cleared {deleted_count:,} records from {table}")
                except Exception as e:
                    self.log(f"   ⚠️  Could not clear {table}: {str(e)}", "WARNING")
            
            # Re-enable foreign key checks
            cursor.execute("SET session_replication_role = DEFAULT;")
            conn.commit()
            self.log("✅ All target tables cleared successfully")
            
        except Exception as e:
            self.log(f"❌ Error clearing tables: {str(e)}", "ERROR")
            conn.rollback()
            raise
            
    def extract_leagues(self, players_data: List[Dict]) -> List[Dict]:
        """Extract unique leagues from players data"""
        self.log("🔍 Extracting leagues from players data...")
        
        leagues = set()
        for player in players_data:
            league = player.get('League', '').strip()
            if league:
                # Normalize the league ID
                normalized_league = normalize_league_id(league)
                if normalized_league:
                    leagues.add(normalized_league)
                
        # Convert to standardized format
        league_records = []
        for league_id in sorted(leagues):
            # Create standardized league data using utility functions
            league_record = {
                'league_id': league_id,
                'league_name': get_league_display_name(league_id),
                'league_url': get_league_url(league_id)
            }
            league_records.append(league_record)
            
        self.log(f"✅ Found {len(league_records)} unique leagues: {', '.join([l['league_id'] for l in league_records])}")
        return league_records
        
    def extract_clubs(self, players_data: List[Dict]) -> List[Dict]:
        """Extract unique clubs from players data"""
        self.log("🔍 Extracting clubs from players data...")
        
        clubs = set()
        for player in players_data:
            club = player.get('Club', '').strip()
            if club:
                clubs.add(club)
                
        club_records = [{'name': club} for club in sorted(clubs)]
        
        self.log(f"✅ Found {len(club_records)} unique clubs")
        return club_records
        
    def extract_series(self, players_data: List[Dict]) -> List[Dict]:
        """Extract unique series from players data"""
        self.log("🔍 Extracting series from players data...")
        
        series = set()
        for player in players_data:
            series_name = player.get('Series', '').strip()
            if series_name:
                series.add(series_name)
                
        series_records = [{'name': series_name} for series_name in sorted(series)]
        
        self.log(f"✅ Found {len(series_records)} unique series")
        return series_records
        
    def analyze_club_league_relationships(self, players_data: List[Dict]) -> List[Dict]:
        """Analyze which clubs belong to which leagues"""
        self.log("🔍 Analyzing club-league relationships...")
        
        club_league_map = {}
        for player in players_data:
            club = player.get('Club', '').strip()
            league = player.get('League', '').strip()
            
            if club and league:
                # Normalize the league ID
                normalized_league = normalize_league_id(league)
                if normalized_league:
                    if club not in club_league_map:
                        club_league_map[club] = set()
                    club_league_map[club].add(normalized_league)
                
        relationships = []
        for club, leagues in club_league_map.items():
            for league_id in leagues:
                relationships.append({
                    'club_name': club,
                    'league_id': league_id
                })
                
        self.log(f"✅ Found {len(relationships)} club-league relationships")
        return relationships
        
    def analyze_series_league_relationships(self, players_data: List[Dict]) -> List[Dict]:
        """Analyze which series belong to which leagues"""
        self.log("🔍 Analyzing series-league relationships...")
        
        series_league_map = {}
        for player in players_data:
            series_name = player.get('Series', '').strip()
            league = player.get('League', '').strip()
            
            if series_name and league:
                # Normalize the league ID
                normalized_league = normalize_league_id(league)
                if normalized_league:
                    if series_name not in series_league_map:
                        series_league_map[series_name] = set()
                    series_league_map[series_name].add(normalized_league)
                
        relationships = []
        for series_name, leagues in series_league_map.items():
            for league_id in leagues:
                relationships.append({
                    'series_name': series_name,
                    'league_id': league_id
                })
                
        self.log(f"✅ Found {len(relationships)} series-league relationships")
        return relationships
        
    def extract_teams(self, series_stats_data: List[Dict], schedules_data: List[Dict]) -> List[Dict]:
        """Extract unique teams from series stats and schedules data"""
        self.log("🔍 Extracting teams from JSON data...")
        
        teams = set()
        
        # Extract from series_stats.json
        for record in series_stats_data:
            series_name = record.get('series', '').strip()
            team_name = record.get('team', '').strip()
            league_id = normalize_league_id(record.get('league_id', '').strip())
            
            if team_name and series_name and league_id:
                # Parse team name to extract club
                club_name = self.parse_team_name_to_club(team_name, series_name)
                if club_name:
                    teams.add((club_name, series_name, league_id, team_name))
        
        # Extract from schedules.json (both home and away teams)
        for record in schedules_data:
            league_id = normalize_league_id(record.get('League', '').strip())
            home_team = record.get('home_team', '').strip()
            away_team = record.get('away_team', '').strip()
            
            for team_name in [home_team, away_team]:
                if team_name and league_id and team_name != 'BYE':
                    # Parse team name to extract club and series
                    club_name, series_name = self.parse_schedule_team_name(team_name)
                    if club_name and series_name:
                        teams.add((club_name, series_name, league_id, team_name))
        
        # Convert to list of dictionaries
        team_records = []
        for club_name, series_name, league_id, team_name in sorted(teams):
            team_records.append({
                'club_name': club_name,
                'series_name': series_name,
                'league_id': league_id,
                'team_name': team_name
            })
        
        self.log(f"✅ Found {len(team_records)} unique teams")
        return team_records
    
    def parse_team_name_to_club(self, team_name: str, series_name: str) -> str:
        """Parse team name from series_stats to extract club name"""
        # Examples: 
        # APTA_CHICAGO: "Tennaqua - 22" with series "Chicago 22" -> "Tennaqua"
        # NSTF: "Tennaqua S2B" with series "Series 2B" -> "Tennaqua"
        
        # Handle APTA_CHICAGO format: "Club - Suffix"
        if ' - ' in team_name:
            club_part = team_name.split(' - ')[0].strip()
            return club_part
        
        # Handle NSTF format: "Club SSuffix" (like "Tennaqua S2B")
        # Must be " S" followed by number or number+letter (not words like "Shore")
        import re
        if re.search(r' S\d', team_name):  # " S" followed by a digit
            parts = team_name.split(' S')
            if len(parts) >= 2:
                club_part = parts[0].strip()
                return club_part
        
        # Fallback: return the whole team name as club
        return team_name
    
    def parse_schedule_team_name(self, team_name: str) -> tuple:
        """Parse team name from schedules to extract club and series"""
        # Examples: 
        # APTA_CHICAGO: "Tennaqua - 22" -> ("Tennaqua", "Chicago 22")
        # NSTF: "Tennaqua S2B" -> ("Tennaqua", "Series 2B")
        
        # Handle APTA_CHICAGO format: "Club - Suffix"
        if ' - ' in team_name:
            parts = team_name.split(' - ')
            if len(parts) >= 2:
                club_name = parts[0].strip()
                series_suffix = parts[1].strip()
                
                # Map series suffix to full series name
                series_name = self.map_series_suffix_to_full_name(series_suffix)
                return club_name, series_name
        
        # Handle NSTF format: "Club SSuffix" (like "Tennaqua S2B")
        # Must be " S" followed by number or number+letter (not words like "Shore")
        import re
        if re.search(r' S\d', team_name):  # " S" followed by a digit
            parts = team_name.split(' S')
            if len(parts) >= 2:
                club_name = parts[0].strip()
                series_suffix = parts[1].strip()
                
                # Map series suffix to full series name (for NSTF, this becomes "Series 2B")
                series_name = self.map_series_suffix_to_full_name(f"S{series_suffix}")
                return club_name, series_name
        
        # Fallback for edge cases: treat entire name as club with default series
        return team_name, "Series A"
    
    def map_series_suffix_to_full_name(self, suffix: str) -> str:
        """Map series suffix to full series name"""
        # Examples: "22" -> "Chicago 22", "21 SW" -> "Chicago 21 SW", "S2B" -> "Series 2B"
        try:
            # If it's a pure number, assume it's a Chicago series
            series_num = int(suffix)
            return f"Chicago {series_num}"
        except ValueError:
            # If it's not a pure number, handle special cases
            if suffix.upper().startswith('S'):
                # NSTF format like "S2B" -> "Series 2B"
                return f"Series {suffix[1:]}"
            elif any(char.isdigit() for char in suffix):
                # If it contains numbers but isn't pure number (like "21 SW"), assume Chicago
                return f"Chicago {suffix}"
            
            # Default: assume it's already a series name
            return suffix
        
    def import_leagues(self, conn, leagues_data: List[Dict]):
        """Import leagues into database"""
        self.log("📥 Importing leagues...")
        
        cursor = conn.cursor()
        imported = 0
        
        for league in leagues_data:
            try:
                cursor.execute("""
                    INSERT INTO leagues (league_id, league_name, league_url, created_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (league_id) DO NOTHING
                """, (league['league_id'], league['league_name'], league['league_url']))
                
                if cursor.rowcount > 0:
                    imported += 1
                    
            except Exception as e:
                self.log(f"❌ Error importing league {league['league_id']}: {str(e)}", "ERROR")
                raise
                
        conn.commit()
        self.imported_counts['leagues'] = imported
        self.log(f"✅ Imported {imported} leagues")
        
    def import_clubs(self, conn, clubs_data: List[Dict]):
        """Import clubs into database"""
        self.log("📥 Importing clubs...")
        
        cursor = conn.cursor()
        imported = 0
        
        for club in clubs_data:
            try:
                cursor.execute("""
                    INSERT INTO clubs (name)
                    VALUES (%s)
                    ON CONFLICT (name) DO NOTHING
                """, (club['name'],))
                
                if cursor.rowcount > 0:
                    imported += 1
                    
            except Exception as e:
                self.log(f"❌ Error importing club {club['name']}: {str(e)}", "ERROR")
                raise
                
        conn.commit()
        self.imported_counts['clubs'] = imported
        self.log(f"✅ Imported {imported} clubs")
        
    def import_series(self, conn, series_data: List[Dict]):
        """Import series into database"""
        self.log("📥 Importing series...")
        
        cursor = conn.cursor()
        imported = 0
        
        for series in series_data:
            try:
                cursor.execute("""
                    INSERT INTO series (name)
                    VALUES (%s)
                    ON CONFLICT (name) DO NOTHING
                """, (series['name'],))
                
                if cursor.rowcount > 0:
                    imported += 1
                    
            except Exception as e:
                self.log(f"❌ Error importing series {series['name']}: {str(e)}", "ERROR")
                raise
                
        conn.commit()
        self.imported_counts['series'] = imported
        self.log(f"✅ Imported {imported} series")
        
    def import_club_leagues(self, conn, relationships: List[Dict]):
        """Import club-league relationships"""
        self.log("📥 Importing club-league relationships...")
        
        cursor = conn.cursor()
        imported = 0
        
        for rel in relationships:
            try:
                cursor.execute("""
                    INSERT INTO club_leagues (club_id, league_id, created_at)
                    SELECT c.id, l.id, CURRENT_TIMESTAMP
                    FROM clubs c, leagues l
                    WHERE c.name = %s AND l.league_id = %s
                    ON CONFLICT ON CONSTRAINT unique_club_league DO NOTHING
                """, (rel['club_name'], rel['league_id']))
                
                if cursor.rowcount > 0:
                    imported += 1
                    
            except Exception as e:
                self.log(f"❌ Error importing club-league relationship {rel['club_name']}-{rel['league_id']}: {str(e)}", "ERROR")
                raise
                
        conn.commit()
        self.imported_counts['club_leagues'] = imported
        self.log(f"✅ Imported {imported} club-league relationships")
        
    def import_series_leagues(self, conn, relationships: List[Dict]):
        """Import series-league relationships"""
        self.log("📥 Importing series-league relationships...")
        
        cursor = conn.cursor()
        imported = 0
        
        for rel in relationships:
            try:
                cursor.execute("""
                    INSERT INTO series_leagues (series_id, league_id, created_at)
                    SELECT s.id, l.id, CURRENT_TIMESTAMP
                    FROM series s, leagues l
                    WHERE s.name = %s AND l.league_id = %s
                    ON CONFLICT ON CONSTRAINT unique_series_league DO NOTHING
                """, (rel['series_name'], rel['league_id']))
                
                if cursor.rowcount > 0:
                    imported += 1
                    
            except Exception as e:
                self.log(f"❌ Error importing series-league relationship {rel['series_name']}-{rel['league_id']}: {str(e)}", "ERROR")
                raise
                
        conn.commit()
        self.imported_counts['series_leagues'] = imported
        self.log(f"✅ Imported {imported} series-league relationships")
        
    def import_teams(self, conn, teams_data: List[Dict]):
        """Import teams into database"""
        self.log("📥 Importing teams...")
        
        cursor = conn.cursor()
        imported = 0
        errors = 0
        
        for team in teams_data:
            try:
                club_name = team['club_name']
                series_name = team['series_name']
                league_id = team['league_id']
                team_name = team['team_name']
                
                # Create team alias for display (optional)
                team_alias = self.generate_team_alias(team_name, series_name)
                
                cursor.execute("""
                    INSERT INTO teams (club_id, series_id, league_id, team_name, team_alias, created_at)
                    SELECT c.id, s.id, l.id, %s, %s, CURRENT_TIMESTAMP
                    FROM clubs c, series s, leagues l
                    WHERE c.name = %s AND s.name = %s AND l.league_id = %s
                    ON CONFLICT (club_id, series_id, league_id) DO UPDATE SET
                        team_name = EXCLUDED.team_name,
                        team_alias = EXCLUDED.team_alias,
                        updated_at = CURRENT_TIMESTAMP
                """, (team_name, team_alias, club_name, series_name, league_id))
                
                if cursor.rowcount > 0:
                    imported += 1
                    
            except Exception as e:
                errors += 1
                if errors <= 10:
                    self.log(f"❌ Error importing team {team_name}: {str(e)}", "ERROR")
                    
                if errors > 50:
                    self.log(f"❌ Too many team import errors ({errors}), stopping", "ERROR")
                    raise Exception(f"Too many team import errors ({errors})")
                
        conn.commit()
        self.imported_counts['teams'] = imported
        self.log(f"✅ Imported {imported} teams ({errors} errors)")
        
    def generate_team_alias(self, team_name: str, series_name: str) -> str:
        """Generate a user-friendly team alias"""
        # Examples:
        # APTA_CHICAGO: "Tennaqua - 22" -> "Series 22"
        # NSTF: "Tennaqua S2B" -> "Series 2B"
        
        # Handle APTA_CHICAGO format: "Club - Suffix"
        if ' - ' in team_name:
            parts = team_name.split(' - ')
            if len(parts) >= 2:
                suffix = parts[1].strip()
                return f"Series {suffix}"
        
        # Handle NSTF format: "Club SSuffix"
        # Must be " S" followed by number or number+letter (not words like "Shore")
        import re
        if re.search(r' S\d', team_name):  # " S" followed by a digit
            parts = team_name.split(' S')
            if len(parts) >= 2:
                suffix = parts[1].strip()
                return f"Series {suffix}"
        
        # Fallback: use series name
        return series_name
        
    def import_players(self, conn, players_data: List[Dict]):
        """Import players data with enhanced conflict detection"""
        self.log("📥 Importing players with enhanced conflict detection...")
        
        cursor = conn.cursor()
        imported = 0
        updated = 0
        errors = 0
        player_id_tracker = {}  # Track multiple records per Player ID
        
        # First pass: analyze for potential conflicts
        self.log("🔍 Step 1: Analyzing potential conflicts...")
        conflicts_found = 0
        for player in players_data:
            player_id = player.get('Player ID', '').strip()
            league_id = normalize_league_id(player.get('League', '').strip())
            club_name = player.get('Club', '').strip()
            series_name = player.get('Series', '').strip()
            
            if player_id and league_id:
                key = f"{league_id}::{player_id}"
                if key not in player_id_tracker:
                    player_id_tracker[key] = []
                player_id_tracker[key].append({
                    'club': club_name,
                    'series': series_name,
                    'name': f"{player.get('First Name', '')} {player.get('Last Name', '')}"
                })
        
        # Log conflicts found
        for key, records in player_id_tracker.items():
            if len(records) > 1:
                conflicts_found += 1
                if conflicts_found <= 5:  # Log first 5 conflicts as examples
                    league, player_id = key.split("::")
                    self.log(f"🔍 CONFLICT DETECTED: Player ID {player_id} in {league}", "INFO")
                    for i, record in enumerate(records, 1):
                        self.log(f"   {i}. {record['name']} at {record['club']} / {record['series']}", "INFO")
        
        if conflicts_found > 0:
            self.log(f"📊 Found {conflicts_found} Player IDs with multiple club/series records", "INFO")
            self.log("✅ Enhanced constraint will allow all records to coexist", "INFO")
        
        # Second pass: import players
        self.log("📥 Step 2: Importing player records...")
        
        for player in players_data:
            try:
                # Extract and clean data
                tenniscores_player_id = player.get('Player ID', '').strip()
                first_name = player.get('First Name', '').strip()
                last_name = player.get('Last Name', '').strip()
                raw_league_id = player.get('League', '').strip()
                league_id = normalize_league_id(raw_league_id) if raw_league_id else ''
                club_name = player.get('Club', '').strip()
                series_name = player.get('Series', '').strip()
                
                # Parse PTI - handle both string and numeric types
                pti_value = player.get('PTI', '')
                pti = None
                if pti_value is not None and pti_value != '':
                    if isinstance(pti_value, (int, float)):
                        pti = float(pti_value)
                    else:
                        pti_str = str(pti_value).strip()
                        if pti_str and pti_str.upper() != 'N/A':
                            try:
                                pti = float(pti_str)
                            except ValueError:
                                pass
                
                # Parse wins/losses
                wins = self._parse_int(player.get('Wins', '0'))
                losses = self._parse_int(player.get('Losses', '0'))
                
                # Parse win percentage - handle both string and numeric types
                win_pct_value = player.get('Win %', '0.0%')
                win_percentage = 0.0
                if isinstance(win_pct_value, (int, float)):
                    win_percentage = float(win_pct_value)
                else:
                    try:
                        win_pct_str = str(win_pct_value).replace('%', '').strip()
                        win_percentage = float(win_pct_str)
                    except (ValueError, AttributeError):
                        pass
                
                # Captain status - handle different data types
                captain_value = player.get('Captain', '')
                captain_status = str(captain_value).strip() if captain_value is not None else ''
                
                if not all([tenniscores_player_id, first_name, last_name, league_id]):
                    self.log(f"⚠️  Skipping player with missing required data: {player}", "WARNING")
                    continue
                
                # Check if this exact combination already exists
                cursor.execute("""
                    SELECT p.id FROM players p
                    JOIN leagues l ON p.league_id = l.id
                    LEFT JOIN clubs c ON p.club_id = c.id
                    LEFT JOIN series s ON p.series_id = s.id
                    WHERE p.tenniscores_player_id = %s 
                    AND l.league_id = %s
                    AND COALESCE(c.name, '') = %s
                    AND COALESCE(s.name, '') = %s
                """, (tenniscores_player_id, league_id, club_name or '', series_name or ''))
                
                existing_player = cursor.fetchone()
                is_update = existing_player is not None
                
                cursor.execute("""
                    INSERT INTO players (
                        tenniscores_player_id, first_name, last_name, 
                        league_id, club_id, series_id, team_id, pti, wins, losses, 
                        win_percentage, captain_status, is_active, created_at
                    )
                    SELECT 
                        %s, %s, %s,
                        l.id, c.id, s.id, t.id, %s, %s, %s,
                        %s, %s, true, CURRENT_TIMESTAMP
                    FROM leagues l
                    LEFT JOIN clubs c ON c.name = %s
                    LEFT JOIN series s ON s.name = %s
                    LEFT JOIN teams t ON t.club_id = c.id AND t.series_id = s.id AND t.league_id = l.id
                    WHERE l.league_id = %s
                    ON CONFLICT ON CONSTRAINT unique_player_in_league_club_series DO UPDATE SET
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        team_id = EXCLUDED.team_id,
                        pti = EXCLUDED.pti,
                        wins = EXCLUDED.wins,
                        losses = EXCLUDED.losses,
                        win_percentage = EXCLUDED.win_percentage,
                        captain_status = EXCLUDED.captain_status,
                        is_active = EXCLUDED.is_active,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    tenniscores_player_id, first_name, last_name,
                    pti, wins, losses, win_percentage, captain_status,
                    club_name, series_name, league_id
                ))
                
                if is_update:
                    updated += 1
                else:
                    imported += 1
                
                if (imported + updated) % 1000 == 0:
                    self.log(f"   📊 Processed {imported + updated:,} players so far (New: {imported:,}, Updated: {updated:,})...")
                    conn.commit()  # Commit in batches
                    
            except Exception as e:
                errors += 1
                if errors <= 10:  # Only log first 10 errors
                    self.log(f"❌ Error importing player {player.get('Player ID', 'Unknown')}: {str(e)}", "ERROR")
                
                if errors > 100:  # Stop if too many errors
                    self.log(f"❌ Too many errors ({errors}), stopping player import", "ERROR")
                    raise Exception(f"Too many player import errors ({errors})")
                
        conn.commit()
        self.imported_counts['players'] = imported + updated
        self.log(f"✅ Player import complete: {imported:,} new, {updated:,} updated, {errors} errors")
        self.log(f"🎯 Conflict resolution: {conflicts_found} Player IDs now exist across multiple clubs/series")
        
    def import_career_stats(self, conn, player_history_data: List[Dict]):
        """Import career stats from player_history.json into players table career columns"""
        self.log("📥 Importing career stats...")
        
        cursor = conn.cursor()
        updated = 0
        not_found = 0
        errors = 0
        
        for player_data in player_history_data:
            try:
                # Extract career stats from JSON
                player_name = player_data.get('name', '')
                career_wins = player_data.get('wins', 0)
                career_losses = player_data.get('losses', 0) 
                tenniscores_id = player_data.get('player_id', '').strip()
                
                if not tenniscores_id:
                    continue
                
                # Calculate derived stats
                career_matches = career_wins + career_losses
                career_win_percentage = round((career_wins / career_matches) * 100, 2) if career_matches > 0 else 0.00
                
                # Find and update the player in the database
                cursor.execute("""
                    UPDATE players 
                    SET 
                        career_wins = %s,
                        career_losses = %s, 
                        career_matches = %s,
                        career_win_percentage = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE tenniscores_player_id = %s
                """, (career_wins, career_losses, career_matches, career_win_percentage, tenniscores_id))
                
                if cursor.rowcount > 0:
                    updated += 1
                    
                    # Log progress for significant players
                    if career_matches >= 20 and updated % 50 == 0:
                        self.log(f"   📊 Updated {updated:,} career stats so far...")
                else:
                    not_found += 1
                    
            except Exception as e:
                errors += 1
                if errors <= 10:
                    self.log(f"❌ Error updating career stats for {player_name}: {str(e)}", "ERROR")
                    
                if errors > 100:
                    self.log(f"❌ Too many career stats errors ({errors}), stopping", "ERROR")
                    raise Exception(f"Too many career stats import errors ({errors})")
                    
        conn.commit()
        self.imported_counts['career_stats'] = updated
        self.log(f"✅ Updated {updated:,} players with career stats ({not_found} not found, {errors} errors)")
        
    def import_player_history(self, conn, player_history_data: List[Dict]):
        """Import player history data"""
        self.log("📥 Importing player history...")
        
        cursor = conn.cursor()
        imported = 0
        errors = 0
        
        for player_record in player_history_data:
            try:
                tenniscores_player_id = player_record.get('player_id', '').strip()
                raw_league_id = player_record.get('league_id', '').strip()
                league_id = normalize_league_id(raw_league_id) if raw_league_id else ''
                series = player_record.get('series', '').strip()
                matches = player_record.get('matches', [])
                
                if not all([tenniscores_player_id, league_id]) or not matches:
                    continue
                
                # Get the database player ID
                cursor.execute("""
                    SELECT p.id, l.id 
                    FROM players p 
                    JOIN leagues l ON l.league_id = %s
                    WHERE p.tenniscores_player_id = %s AND p.league_id = l.id
                """, (league_id, tenniscores_player_id))
                
                result = cursor.fetchone()
                if not result:
                    continue
                    
                db_player_id, db_league_id = result
                
                # Import each match history record
                for match in matches:
                    try:
                        date_str = match.get('date', '').strip()
                        end_pti = match.get('end_pti')
                        match_series = match.get('series', series).strip()
                        
                        # Parse date
                        record_date = None
                        if date_str:
                            try:
                                record_date = datetime.strptime(date_str, '%m/%d/%Y').date()
                            except ValueError:
                                try:
                                    record_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                                except ValueError:
                                    pass
                        
                        if not record_date:
                            continue
                        
                        cursor.execute("""
                            INSERT INTO player_history (player_id, league_id, series, date, end_pti, created_at)
                            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        """, (db_player_id, db_league_id, match_series, record_date, end_pti))
                        
                        imported += 1
                        
                    except Exception as match_error:
                        errors += 1
                        if errors <= 10:
                            self.log(f"❌ Error importing match for player {tenniscores_player_id}: {str(match_error)}", "ERROR")
                    
                if imported % 1000 == 0 and imported > 0:
                    self.log(f"   📊 Imported {imported:,} player history records so far...")
                    conn.commit()
                    
            except Exception as e:
                errors += 1
                if errors <= 10:
                    self.log(f"❌ Error importing player history for {tenniscores_player_id}: {str(e)}", "ERROR")
                    
                if errors > 100:
                    self.log(f"❌ Too many player history errors ({errors}), stopping", "ERROR")
                    raise Exception(f"Too many player history import errors ({errors})")
                
        conn.commit()
        self.imported_counts['player_history'] = imported
        self.log(f"✅ Imported {imported:,} player history records ({errors} errors)")
        
    def import_match_history(self, conn, match_history_data: List[Dict]):
        """Import match history data into match_scores table"""
        self.log("📥 Importing match history...")
        
        cursor = conn.cursor()
        imported = 0
        errors = 0
        
        for record in match_history_data:
            try:
                # Extract data using the actual field names from the JSON
                match_date_str = (record.get('Date') or '').strip()
                home_team = (record.get('Home Team') or '').strip()
                away_team = (record.get('Away Team') or '').strip()
                scores = record.get('Scores') or ''
                winner = (record.get('Winner') or '').strip()
                raw_league_id = (record.get('league_id') or '').strip()
                league_id = normalize_league_id(raw_league_id) if raw_league_id else ''
                
                # Extract player IDs
                home_player_1_id = (record.get('Home Player 1 ID') or '').strip()
                home_player_2_id = (record.get('Home Player 2 ID') or '').strip()
                away_player_1_id = (record.get('Away Player 1 ID') or '').strip()
                away_player_2_id = (record.get('Away Player 2 ID') or '').strip()
                
                # Parse date (format appears to be DD-Mon-YY)
                match_date = None
                if match_date_str:
                    try:
                        # Try DD-Mon-YY format first
                        match_date = datetime.strptime(match_date_str, '%d-%b-%y').date()
                    except ValueError:
                        try:
                            match_date = datetime.strptime(match_date_str, '%m/%d/%Y').date()
                        except ValueError:
                            try:
                                match_date = datetime.strptime(match_date_str, '%Y-%m-%d').date()
                            except ValueError:
                                pass
                
                if not all([match_date, home_team, away_team]):
                    continue
                
                # Validate winner field - only allow 'home', 'away', or None
                if winner and winner.lower() not in ['home', 'away']:
                    winner = None  # Set to None for invalid values like 'unknown'
                
                # Get league database ID
                cursor.execute("SELECT id FROM leagues WHERE league_id = %s", (league_id,))
                league_row = cursor.fetchone()
                league_db_id = league_row[0] if league_row else None
                
                # Get team IDs from teams table
                home_team_id = None
                away_team_id = None
                
                if home_team and home_team != 'BYE':
                    cursor.execute("""
                        SELECT t.id FROM teams t
                        JOIN leagues l ON t.league_id = l.id
                        WHERE l.league_id = %s AND t.team_name = %s
                    """, (league_id, home_team))
                    home_team_row = cursor.fetchone()
                    home_team_id = home_team_row[0] if home_team_row else None
                
                if away_team and away_team != 'BYE':
                    cursor.execute("""
                        SELECT t.id FROM teams t
                        JOIN leagues l ON t.league_id = l.id
                        WHERE l.league_id = %s AND t.team_name = %s
                    """, (league_id, away_team))
                    away_team_row = cursor.fetchone()
                    away_team_id = away_team_row[0] if away_team_row else None
                
                cursor.execute("""
                    INSERT INTO match_scores (
                        match_date, home_team, away_team, home_team_id, away_team_id,
                        home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id, 
                        scores, winner, league_id, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """, (match_date, home_team, away_team, home_team_id, away_team_id,
                      home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id, 
                      str(scores), winner, league_db_id))
                
                imported += 1
                    
                if imported % 1000 == 0:
                    self.log(f"   📊 Imported {imported:,} match records so far...")
                    conn.commit()
                    
            except Exception as e:
                errors += 1
                if errors <= 10:
                    self.log(f"❌ Error importing match record: {str(e)}", "ERROR")
                    
                if errors > 100:
                    self.log(f"❌ Too many match history errors ({errors}), stopping", "ERROR")
                    raise Exception(f"Too many match history import errors ({errors})")
                
        conn.commit()
        self.imported_counts['match_scores'] = imported
        self.log(f"✅ Imported {imported:,} match history records ({errors} errors)")
        
    def import_series_stats(self, conn, series_stats_data: List[Dict]):
        """Import series stats data"""
        self.log("📥 Importing series stats...")
        
        cursor = conn.cursor()
        imported = 0
        errors = 0
        league_not_found_count = 0
        
        # Debug: Check what leagues exist in the database
        cursor.execute("SELECT league_id FROM leagues ORDER BY league_id")
        existing_leagues = [row[0] for row in cursor.fetchall()]
        self.log(f"🔍 Debug: Found {len(existing_leagues)} leagues in database: {existing_leagues}")
        
        for record in series_stats_data:
            try:
                series = record.get('series', '').strip()
                team = record.get('team', '').strip()
                raw_league_id = record.get('league_id', '').strip()
                league_id = normalize_league_id(raw_league_id) if raw_league_id else ''
                points = record.get('points', 0)
                
                # Extract match stats
                matches = record.get('matches', {})
                matches_won = matches.get('won', 0)
                matches_lost = matches.get('lost', 0)
                matches_tied = matches.get('tied', 0)
                
                # Extract line stats
                lines = record.get('lines', {})
                lines_won = lines.get('won', 0)
                lines_lost = lines.get('lost', 0)
                lines_for = lines.get('for', 0)
                lines_ret = lines.get('ret', 0)
                
                # Extract set stats
                sets = record.get('sets', {})
                sets_won = sets.get('won', 0)
                sets_lost = sets.get('lost', 0)
                
                # Extract game stats
                games = record.get('games', {})
                games_won = games.get('won', 0)
                games_lost = games.get('lost', 0)
                
                if not all([series, team, league_id]):
                    continue
                
                # Get league database ID with better error handling
                cursor.execute("SELECT id FROM leagues WHERE league_id = %s", (league_id,))
                league_row = cursor.fetchone()
                
                if not league_row:
                    league_not_found_count += 1
                    if league_not_found_count <= 5:  # Only log first 5 missing leagues
                        self.log(f"⚠️  League not found: {league_id} for team {team} (raw: {raw_league_id})", "WARNING")
                    continue
                    
                league_db_id = league_row[0]
                
                # Get team_id from teams table
                cursor.execute("""
                    SELECT t.id FROM teams t
                    JOIN leagues l ON t.league_id = l.id
                    JOIN series s ON t.series_id = s.id
                    WHERE l.league_id = %s AND s.name = %s AND t.team_name = %s
                """, (league_id, series, team))
                
                team_row = cursor.fetchone()
                team_db_id = team_row[0] if team_row else None
                
                cursor.execute("""
                    INSERT INTO series_stats (
                        series, team, team_id, points, matches_won, matches_lost, matches_tied,
                        lines_won, lines_lost, lines_for, lines_ret,
                        sets_won, sets_lost, games_won, games_lost,
                        league_id, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """, (
                    series, team, team_db_id, points, matches_won, matches_lost, matches_tied,
                    lines_won, lines_lost, lines_for, lines_ret,
                    sets_won, sets_lost, games_won, games_lost, league_db_id
                ))
                
                if cursor.rowcount > 0:
                    imported += 1
                    
                # Commit more frequently to prevent transaction rollback issues
                if imported % 100 == 0:
                    conn.commit()
                    
            except Exception as e:
                errors += 1
                if errors <= 10:
                    self.log(f"❌ Error importing series stats record: {str(e)}", "ERROR")
                    
                if errors > 100:
                    self.log(f"❌ Too many series stats errors ({errors}), stopping", "ERROR")
                    raise Exception(f"Too many series stats import errors ({errors})")
                
        conn.commit()
        self.imported_counts['series_stats'] = imported
        
        # Summary logging
        if league_not_found_count > 0:
            self.log(f"⚠️  {league_not_found_count} series stats records skipped due to missing leagues", "WARNING")
        
        self.log(f"✅ Imported {imported:,} series stats records ({errors} errors, {league_not_found_count} missing leagues)")
        
    def import_schedules(self, conn, schedules_data: List[Dict]):
        """Import schedules data"""
        self.log("📥 Importing schedules...")
        
        cursor = conn.cursor()
        imported = 0
        errors = 0
        
        for record in schedules_data:
            try:
                date_str = record.get('date', '').strip()
                time_str = record.get('time', '').strip()
                home_team = record.get('home_team', '').strip()
                away_team = record.get('away_team', '').strip()
                location = record.get('location', '').strip()
                raw_league_id = record.get('League', '').strip()
                league_id = normalize_league_id(raw_league_id) if raw_league_id else ''
                
                # Parse date
                match_date = None
                if date_str:
                    try:
                        match_date = datetime.strptime(date_str, '%m/%d/%Y').date()
                    except ValueError:
                        try:
                            match_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        except ValueError:
                            pass
                
                # Handle empty time fields - convert to None for PostgreSQL TIME column
                match_time = None
                if time_str:
                    match_time = time_str
                
                if not all([match_date, home_team, away_team]):
                    continue
                
                # Get league database ID
                cursor.execute("SELECT id FROM leagues WHERE league_id = %s", (league_id,))
                league_row = cursor.fetchone()
                league_db_id = league_row[0] if league_row else None
                
                # Get team IDs from teams table
                home_team_id = None
                away_team_id = None
                
                if home_team and home_team != 'BYE':
                    cursor.execute("""
                        SELECT t.id FROM teams t
                        JOIN leagues l ON t.league_id = l.id
                        WHERE l.league_id = %s AND t.team_name = %s
                    """, (league_id, home_team))
                    home_team_row = cursor.fetchone()
                    home_team_id = home_team_row[0] if home_team_row else None
                
                if away_team and away_team != 'BYE':
                    cursor.execute("""
                        SELECT t.id FROM teams t
                        JOIN leagues l ON t.league_id = l.id
                        WHERE l.league_id = %s AND t.team_name = %s
                    """, (league_id, away_team))
                    away_team_row = cursor.fetchone()
                    away_team_id = away_team_row[0] if away_team_row else None
                
                cursor.execute("""
                    INSERT INTO schedule (
                        match_date, match_time, home_team, away_team, home_team_id, away_team_id,
                        location, league_id, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """, (match_date, match_time, home_team, away_team, home_team_id, away_team_id, location, league_db_id))
                
                if cursor.rowcount > 0:
                    imported += 1
                    
                if imported % 1000 == 0:
                    self.log(f"   📊 Imported {imported:,} schedule records so far...")
                    conn.commit()
                    
            except Exception as e:
                errors += 1
                if errors <= 10:
                    self.log(f"❌ Error importing schedule record: {str(e)}", "ERROR")
                    
                if errors > 100:
                    self.log(f"❌ Too many schedule errors ({errors}), stopping", "ERROR")
                    raise Exception(f"Too many schedule import errors ({errors})")
                
        conn.commit()
        self.imported_counts['schedule'] = imported
        self.log(f"✅ Imported {imported:,} schedule records ({errors} errors)")
    

        
    def _parse_int(self, value: str) -> int:
        """Parse integer with error handling"""
        if not value or value.strip() == '':
            return 0
        try:
            return int(str(value).strip())
        except (ValueError, TypeError):
            return 0
            
    def print_summary(self):
        """Print import summary"""
        self.log("=" * 60)
        self.log("📊 IMPORT SUMMARY")
        self.log("=" * 60)
        
        total_imported = 0
        for table, count in self.imported_counts.items():
            self.log(f"   {table:<20}: {count:>10,} records")
            total_imported += count
            
        self.log("-" * 60)
        self.log(f"   {'TOTAL':<20}: {total_imported:>10,} records")
        
        if self.errors:
            self.log(f"\n⚠️  {len(self.errors)} errors encountered during import")
            
    def run(self):
        """Run the complete ETL process"""
        start_time = datetime.now()
        
        try:
            self.log("🚀 Starting Comprehensive JSON ETL Process")
            self.log("=" * 60)
            
            # Step 1: Load all JSON files
            self.log("📂 Step 1: Loading JSON files...")
            players_data = self.load_json_file('players.json')
            player_history_data = self.load_json_file('player_history.json')
            match_history_data = self.load_json_file('match_history.json')
            series_stats_data = self.load_json_file('series_stats.json')
            schedules_data = self.load_json_file('schedules.json')
            
            # Step 2: Extract reference data from players.json
            self.log("\n📋 Step 2: Extracting reference data...")
            leagues_data = self.extract_leagues(players_data)
            clubs_data = self.extract_clubs(players_data)
            series_data = self.extract_series(players_data)
            club_league_rels = self.analyze_club_league_relationships(players_data)
            series_league_rels = self.analyze_series_league_relationships(players_data)
            
            # Step 2b: Extract teams from series stats and schedules
            self.log("\n🏗️  Step 2b: Extracting teams...")
            teams_data = self.extract_teams(series_stats_data, schedules_data)
            
            # Step 3: Connect to database and import
            self.log("\n🗄️  Step 3: Connecting to database...")
            with get_db() as conn:
                try:
                    # Clear existing data
                    self.clear_target_tables(conn)
                    
                    # Import in correct order
                    self.log("\n📥 Step 4: Importing data in dependency order...")
                    
                    self.import_leagues(conn, leagues_data)
                    self.import_clubs(conn, clubs_data)
                    self.import_series(conn, series_data)
                    self.import_club_leagues(conn, club_league_rels)
                    self.import_series_leagues(conn, series_league_rels)
                    self.import_teams(conn, teams_data)  # NEW: Import teams before players
                    self.import_players(conn, players_data)
                    self.import_career_stats(conn, player_history_data)
                    self.import_player_history(conn, player_history_data)
                    self.import_match_history(conn, match_history_data)
                    self.import_series_stats(conn, series_stats_data)
                    self.import_schedules(conn, schedules_data)
                    
                    # Success!
                    self.log("\n✅ ETL process completed successfully!")
                    
                except Exception as e:
                    self.log(f"\n❌ ETL process failed: {str(e)}", "ERROR")
                    self.log("🔄 Rolling back all changes...", "WARNING")
                    conn.rollback()
                    raise
                    
        except Exception as e:
            self.log(f"\n💥 CRITICAL ERROR: {str(e)}", "ERROR")
            self.log(f"Traceback: {traceback.format_exc()}", "ERROR")
            return False
            
        finally:
            end_time = datetime.now()
            duration = end_time - start_time
            
            self.log(f"\n⏱️  Total execution time: {duration}")
            self.print_summary()
            
        return True

def main():
    """Main entry point"""
    etl = ComprehensiveETL()
    success = etl.run()
    
    if success:
        print("\n🎉 ETL process completed successfully!")
        return 0
    else:
        print("\n💥 ETL process failed!")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 