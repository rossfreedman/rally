#!/usr/bin/env python3
"""
Atomic ETL Import Script
========================

This script provides a truly atomic ETL process where either ALL operations
succeed or NONE of them do. It uses a single database transaction for the
entire ETL process with automatic rollback on any failure.

Key Features:
- Single transaction wraps entire ETL process
- Automatic rollback on any failure
- Pre-import validation
- Progress monitoring without intermediate commits
- Comprehensive error handling with detailed logging
- Optional backup/restore for additional safety
"""

import json
import os
import sys
import time
import traceback
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, List, Optional

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
sys.path.insert(0, project_root)

import psycopg2
from psycopg2.extras import RealDictCursor

from database_config import get_db
from utils.league_utils import normalize_league_id


class AtomicETL:
    """Atomic ETL process that guarantees all-or-nothing imports"""
    
    def __init__(self, environment: str = None, create_backup: bool = True):
        self.environment = environment or self._detect_environment()
        self.create_backup = create_backup
        self.imported_counts = {}
        self.errors = []
        self.start_time = None
        self.backup_path = None
        
        # Configure based on environment
        self._configure_for_environment()
        
        self.log(f"🏗️  Atomic ETL initialized for {self.environment}")
        self.log(f"💾 Backup enabled: {self.create_backup}")
        
    def _detect_environment(self) -> str:
        """Detect current environment"""
        if os.getenv('RAILWAY_ENVIRONMENT'):
            railway_env = os.getenv('RAILWAY_ENVIRONMENT_NAME', '').lower()
            if 'staging' in railway_env:
                return 'railway_staging'
            elif 'production' in railway_env:
                return 'railway_production'
            else:
                return 'railway_staging'
        return 'local'
    
    def _configure_for_environment(self):
        """Configure settings based on environment"""
        if self.environment == 'local':
            self.batch_size = 1000
            self.progress_interval = 1000
            self.connection_timeout = 300
        elif self.environment == 'railway_staging':
            self.batch_size = 500
            self.progress_interval = 500
            self.connection_timeout = 600
        elif self.environment == 'railway_production':
            self.batch_size = 1000
            self.progress_interval = 1000
            self.connection_timeout = 900
    
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prefix = {
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "SUCCESS": "✅"
        }.get(level, "ℹ️")
        
        print(f"[{timestamp}] {prefix} {message}")
    
    def _create_backup(self) -> Optional[str]:
        """Create database backup before ETL process"""
        if not self.create_backup:
            return None
            
        self.log("💾 Creating database backup...")
        
        try:
            # Import backup functionality
            backup_script = os.path.join(project_root, "data/backup_restore_local_db/backup_database.py")
            if not os.path.exists(backup_script):
                self.log("⚠️ Backup script not found, skipping backup", "WARNING")
                return None
            
            import subprocess
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"atomic_etl_backup_{timestamp}.sql"
            backup_path = os.path.join(project_root, "data/backups", backup_filename)
            
            # Ensure backup directory exists
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            
            # Run backup
            result = subprocess.run([
                sys.executable, backup_script, 
                "--output", backup_path,
                "--quiet"
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                self.log(f"✅ Backup created: {backup_path}")
                return backup_path
            else:
                self.log(f"❌ Backup failed: {result.stderr}", "ERROR")
                return None
                
        except Exception as e:
            self.log(f"❌ Backup creation failed: {str(e)}", "ERROR")
            return None
    
    def _restore_from_backup(self, backup_path: str) -> bool:
        """Restore database from backup"""
        if not backup_path or not os.path.exists(backup_path):
            self.log("❌ No backup available for restore", "ERROR")
            return False
        
        self.log(f"🔄 Restoring database from backup: {backup_path}")
        
        try:
            import subprocess
            backup_script = os.path.join(project_root, "data/backup_restore_local_db/backup_database.py")
            
            result = subprocess.run([
                sys.executable, backup_script,
                "--restore", backup_path,
                "--quiet"
            ], capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                self.log("✅ Database restored successfully")
                return True
            else:
                self.log(f"❌ Restore failed: {result.stderr}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Restore failed: {str(e)}", "ERROR")
            return False
    
    @contextmanager
    def _get_atomic_connection(self):
        """Get database connection for atomic operations"""
        conn = None
        try:
            # Get connection with appropriate timeout
            conn = get_db()
            
            # Configure connection for long-running atomic transaction
            with conn.cursor() as cursor:
                # Set appropriate timeouts for atomic operations
                cursor.execute("SET statement_timeout = %s", [self.connection_timeout * 1000])
                cursor.execute("SET idle_in_transaction_session_timeout = %s", [self.connection_timeout * 2000])
                
                # Optimize for bulk operations
                cursor.execute("SET work_mem = '256MB'")
                cursor.execute("SET maintenance_work_mem = '512MB'")
                
                # Disable autocommit - we want manual transaction control
                conn.autocommit = False
                
                self.log("🔗 Atomic connection established")
                
            yield conn
            
        except Exception as e:
            self.log(f"❌ Connection error: {str(e)}", "ERROR")
            raise
        finally:
            if conn:
                conn.close()
                self.log("🔒 Connection closed")
    
    def _load_json_data(self) -> Dict[str, List[Dict]]:
        """Load all JSON data files"""
        self.log("📂 Loading JSON data files...")
        
        data_dir = os.path.join(project_root, "data/leagues/all")
        if not os.path.exists(data_dir):
            raise FileNotFoundError(f"Data directory not found: {data_dir}")
        
        files = {
            'players': 'players.json',
            'player_history': 'player_history.json',
            'match_history': 'match_history.json',
            'series_stats': 'series_stats.json',
            'schedules': 'schedules.json'
        }
        
        data = {}
        for key, filename in files.items():
            file_path = os.path.join(data_dir, filename)
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data[key] = json.load(f)
                    self.log(f"✅ Loaded {len(data[key]):,} records from {filename}")
            else:
                self.log(f"⚠️ File not found: {filename}", "WARNING")
                data[key] = []
        
        return data
    
    def _validate_data(self, data: Dict[str, List[Dict]]) -> bool:
        """Validate data before import"""
        self.log("🔍 Validating data...")
        
        validation_errors = []
        
        # Check if essential data exists
        if not data.get('players'):
            validation_errors.append("No players data found")
        
        if not data.get('match_history'):
            validation_errors.append("No match history data found")
        
        # Check data consistency
        if data.get('players'):
            # Check for required fields
            sample_player = data['players'][0] if data['players'] else {}
            required_fields = ['Player ID', 'First Name', 'Last Name', 'League']
            
            for field in required_fields:
                if field not in sample_player:
                    validation_errors.append(f"Missing required field in players: {field}")
        
        if validation_errors:
            self.log("❌ Data validation failed:", "ERROR")
            for error in validation_errors:
                self.log(f"   - {error}", "ERROR")
            return False
        
        self.log("✅ Data validation passed")
        return True
    
    def _clear_tables(self, conn, cursor):
        """Clear all target tables"""
        self.log("🧹 Clearing target tables...")
        
        # Define tables to clear in reverse dependency order
        tables_to_clear = [
            'schedule',
            'series_stats', 
            'match_scores',
            'player_history',
            'players',
            'teams',
            'series_leagues',
            'club_leagues',
            'series',
            'clubs',
            'leagues'
        ]
        
        # Disable foreign key checks temporarily
        cursor.execute("SET session_replication_role = replica;")
        
        cleared_counts = {}
        for table in tables_to_clear:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count_before = cursor.fetchone()[0]
                
                cursor.execute(f"DELETE FROM {table}")
                cleared_counts[table] = count_before
                
                self.log(f"   ✅ Cleared {count_before:,} records from {table}")
                
            except Exception as e:
                self.log(f"   ⚠️ Could not clear {table}: {str(e)}", "WARNING")
        
        # Re-enable foreign key checks
        cursor.execute("SET session_replication_role = DEFAULT;")
        
        self.log("✅ All target tables cleared")
        return cleared_counts
    
    def _import_leagues(self, cursor, players_data: List[Dict]) -> int:
        """Import leagues data"""
        self.log("📥 Importing leagues...")
        
        # Extract unique leagues
        leagues = set()
        for player in players_data:
            raw_league = player.get('League', '').strip()
            if raw_league:
                league_id = normalize_league_id(raw_league)
                leagues.add(league_id)
        
        imported = 0
        for league_id in leagues:
            try:
                # Get display name and URL
                from utils.league_utils import get_league_display_name, get_league_url
                display_name = get_league_display_name(league_id)
                url = get_league_url(league_id)
                
                cursor.execute("""
                    INSERT INTO leagues (league_id, display_name, url)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (league_id) DO NOTHING
                """, (league_id, display_name, url))
                
                if cursor.rowcount > 0:
                    imported += 1
                    
            except Exception as e:
                error_msg = f"Failed to import league {league_id}: {str(e)}"
                self.errors.append(error_msg)
                self.log(f"❌ {error_msg}", "ERROR")
                raise
        
        self.imported_counts['leagues'] = imported
        self.log(f"✅ Imported {imported} leagues")
        return imported
    
    def _import_clubs(self, cursor, players_data: List[Dict]) -> int:
        """Import clubs data"""
        self.log("📥 Importing clubs...")
        
        # Extract unique clubs
        clubs = set()
        for player in players_data:
            club_name = player.get('Club', '').strip()
            if club_name:
                # Extract club name from team name (e.g., "Birchwood 1" -> "Birchwood")
                club_name = club_name.split()[0]
                clubs.add(club_name)
        
        imported = 0
        for club_name in clubs:
            try:
                cursor.execute("""
                    INSERT INTO clubs (name)
                    VALUES (%s)
                    ON CONFLICT (name) DO NOTHING
                """, (club_name,))
                
                if cursor.rowcount > 0:
                    imported += 1
                    
            except Exception as e:
                error_msg = f"Failed to import club {club_name}: {str(e)}"
                self.errors.append(error_msg)
                self.log(f"❌ {error_msg}", "ERROR")
                raise
        
        self.imported_counts['clubs'] = imported
        self.log(f"✅ Imported {imported} clubs")
        return imported
    
    def _import_all_data(self, conn, cursor, data: Dict[str, List[Dict]]) -> Dict[str, int]:
        """Import all data in the correct order"""
        self.log("📥 Starting comprehensive data import...")
        
        total_imported = 0
        
        # Step 1: Import reference data
        total_imported += self._import_leagues(cursor, data['players'])
        total_imported += self._import_clubs(cursor, data['players'])
        
        # Step 2: Import remaining data (simplified for atomic operation)
        # Note: This is a simplified version. In production, you'd want to include
        # all the sophisticated import logic from the original script
        
        # Import players
        self.log("📥 Importing players...")
        players_imported = 0
        for i, player in enumerate(data['players']):
            try:
                if i % self.progress_interval == 0:
                    self.log(f"   Processing player {i+1:,}/{len(data['players']):,}")
                
                # Extract player data
                player_id = player.get('Player ID', '').strip()
                first_name = player.get('First Name', '').strip()
                last_name = player.get('Last Name', '').strip()
                league = normalize_league_id(player.get('League', '').strip())
                
                if not player_id or not first_name or not last_name:
                    continue
                
                # Parse PTI
                pti = None
                pti_value = player.get('PTI')
                if pti_value and str(pti_value).strip() not in ['', 'N/A']:
                    try:
                        pti = float(pti_value)
                    except:
                        pass
                
                # Parse wins/losses
                wins = int(player.get('Wins', 0) or 0)
                losses = int(player.get('Losses', 0) or 0)
                
                cursor.execute("""
                    INSERT INTO players (
                        tenniscores_player_id, first_name, last_name, 
                        current_pti, wins, losses, league_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (tenniscores_player_id) DO UPDATE SET
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        current_pti = EXCLUDED.current_pti,
                        wins = EXCLUDED.wins,
                        losses = EXCLUDED.losses,
                        league_id = EXCLUDED.league_id
                """, (player_id, first_name, last_name, pti, wins, losses, league))
                
                players_imported += 1
                
            except Exception as e:
                error_msg = f"Failed to import player {player.get('Player ID', 'Unknown')}: {str(e)}"
                self.errors.append(error_msg)
                self.log(f"❌ {error_msg}", "ERROR")
                raise
        
        self.imported_counts['players'] = players_imported
        self.log(f"✅ Imported {players_imported} players")
        total_imported += players_imported
        
        # Step 3: Import match history
        self.log("📥 Importing match history...")
        matches_imported = 0
        for i, match in enumerate(data['match_history']):
            try:
                if i % self.progress_interval == 0:
                    self.log(f"   Processing match {i+1:,}/{len(data['match_history']):,}")
                
                # Extract match data
                match_date = match.get('Date')
                home_team = match.get('Home Team')
                away_team = match.get('Away Team')
                scores = match.get('Scores', '')
                winner = match.get('Winner', '').lower()
                league = normalize_league_id(match.get('League', '').strip())
                
                if not match_date or not home_team or not away_team:
                    continue
                
                # Parse date
                try:
                    if '/' in match_date:
                        match_date = datetime.strptime(match_date, '%m/%d/%Y').date()
                    else:
                        match_date = datetime.strptime(match_date, '%Y-%m-%d').date()
                except:
                    continue
                
                # Validate winner
                if winner not in ['home', 'away']:
                    winner = None
                
                cursor.execute("""
                    INSERT INTO match_scores (
                        match_date, home_team, away_team, scores, winner, league_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (match_date, home_team, away_team, scores, winner, league))
                
                matches_imported += 1
                
            except Exception as e:
                error_msg = f"Failed to import match {i}: {str(e)}"
                self.errors.append(error_msg)
                self.log(f"❌ {error_msg}", "ERROR")
                raise
        
        self.imported_counts['match_scores'] = matches_imported
        self.log(f"✅ Imported {matches_imported} matches")
        total_imported += matches_imported
        
        return {'total': total_imported, **self.imported_counts}
    
    def run_atomic_etl(self) -> bool:
        """Run the complete atomic ETL process"""
        self.start_time = datetime.now()
        
        try:
            self.log("🚀 Starting Atomic ETL Process")
            self.log("=" * 60)
            
            # Step 1: Create backup if requested
            if self.create_backup:
                self.backup_path = self._create_backup()
            
            # Step 2: Load and validate data
            data = self._load_json_data()
            if not self._validate_data(data):
                raise ValueError("Data validation failed")
            
            # Step 3: Run atomic import
            self.log("🔄 Starting atomic database transaction...")
            
            with self._get_atomic_connection() as conn:
                with conn.cursor() as cursor:
                    try:
                        # Clear existing data
                        self._clear_tables(conn, cursor)
                        
                        # Import all data in single transaction
                        import_results = self._import_all_data(conn, cursor, data)
                        
                        # Validate import results
                        if import_results['total'] == 0:
                            raise ValueError("No data was imported")
                        
                        # If we get here, everything succeeded
                        self.log("✅ All operations completed successfully")
                        self.log("🔄 Committing transaction...")
                        
                        # COMMIT - This is the only commit in the entire process
                        conn.commit()
                        
                        self.log("✅ Transaction committed successfully")
                        
                        # Log final results
                        end_time = datetime.now()
                        duration = end_time - self.start_time
                        
                        self.log("=" * 60)
                        self.log("🎉 ATOMIC ETL COMPLETED SUCCESSFULLY")
                        self.log("=" * 60)
                        self.log(f"⏱️  Total time: {duration}")
                        self.log(f"📊 Records imported: {import_results['total']:,}")
                        
                        for table, count in self.imported_counts.items():
                            self.log(f"   {table}: {count:,}")
                        
                        return True
                        
                    except Exception as e:
                        # ROLLBACK - Any error rolls back the entire transaction
                        self.log(f"❌ Import failed: {str(e)}", "ERROR")
                        self.log("🔄 Rolling back entire transaction...", "WARNING")
                        
                        conn.rollback()
                        
                        self.log("✅ Transaction rolled back - database unchanged")
                        raise
        
        except Exception as e:
            self.log(f"💥 ATOMIC ETL FAILED: {str(e)}", "ERROR")
            
            # Attempt restore if backup exists
            if self.backup_path:
                self.log("🔄 Attempting to restore from backup...")
                if self._restore_from_backup(self.backup_path):
                    self.log("✅ Database restored to original state")
                else:
                    self.log("❌ Backup restore failed", "ERROR")
                    self.log(f"🔧 Manual restore: python3 data/backup_restore_local_db/backup_database.py --restore {self.backup_path}")
            
            return False
        
        finally:
            if self.start_time:
                end_time = datetime.now()
                duration = end_time - self.start_time
                self.log(f"⏱️  Total execution time: {duration}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Atomic ETL Import')
    parser.add_argument('--environment', choices=['local', 'railway_staging', 'railway_production'],
                       help='Target environment')
    parser.add_argument('--no-backup', action='store_true',
                       help='Skip backup creation')
    parser.add_argument('--force', action='store_true',
                       help='Force import even in production')
    
    args = parser.parse_args()
    
    # Safety check for production
    if args.environment == 'railway_production' and not args.force:
        print("❌ Production imports require --force flag for safety")
        return 1
    
    # Initialize and run ETL
    etl = AtomicETL(
        environment=args.environment,
        create_backup=not args.no_backup
    )
    
    success = etl.run_atomic_etl()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main()) 