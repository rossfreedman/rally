#!/usr/bin/env python3
"""
Migrate series table to include league_id for proper league isolation

This script:
1. Analyzes existing series-league relationships
2. Adds league_id column to series table
3. Migrates existing data based on majority league association
4. Handles conflicts by creating separate series records
5. Updates constraints for league isolation
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import execute_query, execute_query_one, execute_update
import json
from datetime import datetime

class SeriesLeagueMigration:
    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        self.migration_log = []
        self.conflicts = []
        self.new_series_created = 0
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        print(log_entry)
        self.migration_log.append(log_entry)
    
    def analyze_series_conflicts(self):
        """Analyze existing series and their league associations"""
        self.log("🔍 ANALYZING SERIES-LEAGUE CONFLICTS")
        
        # Find series that span multiple leagues
        conflict_query = """
            SELECT s.id, s.name, 
                   COUNT(DISTINCT p.league_id) as league_count,
                   STRING_AGG(DISTINCT l.league_name, ', ') as leagues,
                   STRING_AGG(DISTINCT p.league_id::text, ', ') as league_ids
            FROM series s 
            JOIN players p ON s.id = p.series_id 
            JOIN leagues l ON p.league_id = l.id 
            GROUP BY s.id, s.name 
            HAVING COUNT(DISTINCT p.league_id) > 1
            ORDER BY league_count DESC, s.name
        """
        
        conflicts = execute_query(conflict_query)
        self.log(f"Found {len(conflicts)} series with multi-league conflicts")
        
        for conflict in conflicts:
            self.log(f"  ❌ Series {conflict['id']} ({conflict['name']}) spans {conflict['league_count']} leagues: {conflict['leagues']}")
            self.conflicts.append(conflict)
        
        return conflicts
    
    def get_series_league_assignments(self):
        """Determine the primary league for each series based on majority players/teams"""
        self.log("📊 DETERMINING PRIMARY LEAGUE ASSIGNMENTS")
        
        assignment_query = """
            WITH series_league_counts AS (
                SELECT s.id as series_id, s.name as series_name,
                       p.league_id, l.league_name,
                       COUNT(DISTINCT p.tenniscores_player_id) as player_count,
                       COUNT(DISTINCT p.team_id) as team_count,
                       ROW_NUMBER() OVER (PARTITION BY s.id ORDER BY COUNT(DISTINCT p.tenniscores_player_id) DESC) as priority
                FROM series s 
                JOIN players p ON s.id = p.series_id 
                JOIN leagues l ON p.league_id = l.id 
                GROUP BY s.id, s.name, p.league_id, l.league_name
            )
            SELECT series_id, series_name, league_id, league_name, player_count, team_count
            FROM series_league_counts 
            WHERE priority = 1
            ORDER BY series_name
        """
        
        assignments = execute_query(assignment_query)
        self.log(f"Generated primary league assignments for {len(assignments)} series")
        
        return assignments
    
    def backup_series_table(self):
        """Create backup of series table before migration"""
        self.log("💾 CREATING BACKUP OF SERIES TABLE")
        
        if not self.dry_run:
            backup_query = """
                CREATE TABLE series_backup_migration AS 
                SELECT * FROM series
            """
            execute_update(backup_query)
            self.log("✅ Backup created: series_backup_migration")
        else:
            self.log("🔄 DRY RUN: Would create series_backup_migration table")
    
    def add_league_id_column(self):
        """Add league_id column to series table"""
        self.log("🔧 ADDING league_id COLUMN TO SERIES TABLE")
        
        if not self.dry_run:
            # Check if column already exists
            check_column = """
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'series' AND column_name = 'league_id'
            """
            existing = execute_query_one(check_column)
            
            if not existing:
                alter_query = "ALTER TABLE series ADD COLUMN league_id INTEGER"
                execute_update(alter_query)
                self.log("✅ Added league_id column to series table")
            else:
                self.log("ℹ️ league_id column already exists")
        else:
            self.log("🔄 DRY RUN: Would add league_id column")
    
    def migrate_series_data(self, assignments):
        """Update existing series with primary league_id"""
        self.log("📝 MIGRATING EXISTING SERIES DATA")
        
        for assignment in assignments:
            series_id = assignment['series_id']
            league_id = assignment['league_id']
            series_name = assignment['series_name']
            
            if not self.dry_run:
                update_query = "UPDATE series SET league_id = %s WHERE id = %s"
                execute_update(update_query, [league_id, series_id])
                self.log(f"✅ Updated series {series_id} ({series_name}) -> league {league_id}")
            else:
                self.log(f"🔄 DRY RUN: Would update series {series_id} ({series_name}) -> league {league_id}")
    
    def create_additional_series_for_conflicts(self):
        """Create separate series records for conflicting leagues"""
        self.log("🔀 CREATING ADDITIONAL SERIES FOR CONFLICTS")
        
        for conflict in self.conflicts:
            series_id = conflict['id']
            series_name = conflict['name']
            league_ids = [int(lid) for lid in conflict['league_ids'].split(', ')]
            
            # Skip the primary league (already handled)
            secondary_leagues = league_ids[1:]
            
            for league_id in secondary_leagues:
                # Get league name
                league_query = "SELECT league_name FROM leagues WHERE id = %s"
                league_result = execute_query_one(league_query, [league_id])
                league_name = league_result['league_name'] if league_result else f"League{league_id}"
                
                # Create new series with modified name
                new_series_name = f"{series_name} ({league_name})"
                
                if not self.dry_run:
                    # Create new series
                    insert_query = """
                        INSERT INTO series (name, display_name, league_id, updated_at)
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                        RETURNING id
                    """
                    new_series = execute_query_one(insert_query, [new_series_name, new_series_name, league_id])
                    new_series_id = new_series['id']
                    
                    # Update players to point to new series
                    update_players_query = """
                        UPDATE players SET series_id = %s 
                        WHERE series_id = %s AND league_id = %s
                    """
                    execute_update(update_players_query, [new_series_id, series_id, league_id])
                    
                    # Update teams to point to new series
                    update_teams_query = """
                        UPDATE teams SET series_id = %s 
                        WHERE series_id = %s AND league_id = %s
                    """
                    execute_update(update_teams_query, [new_series_id, series_id, league_id])
                    
                    self.new_series_created += 1
                    self.log(f"✅ Created new series {new_series_id} ({new_series_name}) for league {league_id}")
                else:
                    self.log(f"🔄 DRY RUN: Would create new series '{new_series_name}' for league {league_id}")
    
    def update_constraints(self):
        """Update database constraints for league isolation"""
        self.log("🔒 UPDATING DATABASE CONSTRAINTS")
        
        if not self.dry_run:
            # Add foreign key constraint
            fk_query = """
                ALTER TABLE series ADD CONSTRAINT series_league_id_fkey 
                FOREIGN KEY (league_id) REFERENCES leagues(id)
            """
            try:
                execute_update(fk_query)
                self.log("✅ Added foreign key constraint: series_league_id_fkey")
            except Exception as e:
                self.log(f"⚠️ Foreign key constraint may already exist: {e}", "WARNING")
            
            # Drop old unique constraint
            try:
                execute_update("ALTER TABLE series DROP CONSTRAINT series_name_key")
                self.log("✅ Dropped old unique constraint: series_name_key")
            except Exception as e:
                self.log(f"⚠️ Old constraint may not exist: {e}", "WARNING")
            
            # Add new composite unique constraint
            composite_constraint = """
                ALTER TABLE series ADD CONSTRAINT series_name_league_unique 
                UNIQUE (name, league_id)
            """
            try:
                execute_update(composite_constraint)
                self.log("✅ Added composite unique constraint: series_name_league_unique")
            except Exception as e:
                self.log(f"⚠️ Composite constraint may already exist: {e}", "WARNING")
        else:
            self.log("🔄 DRY RUN: Would update database constraints")
    
    def run_migration(self):
        """Run the complete migration process"""
        self.log("🚀 STARTING SERIES LEAGUE ISOLATION MIGRATION")
        self.log(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE MIGRATION'}")
        
        try:
            # Step 1: Analyze conflicts
            conflicts = self.analyze_series_conflicts()
            
            # Step 2: Get primary league assignments
            assignments = self.get_series_league_assignments()
            
            # Step 3: Backup series table
            self.backup_series_table()
            
            # Step 4: Add league_id column
            self.add_league_id_column()
            
            # Step 5: Migrate existing series data
            self.migrate_series_data(assignments)
            
            # Step 6: Create additional series for conflicts
            self.create_additional_series_for_conflicts()
            
            # Step 7: Update constraints
            self.update_constraints()
            
            # Summary
            self.log("✅ MIGRATION COMPLETED SUCCESSFULLY")
            self.log(f"📊 SUMMARY:")
            self.log(f"  - Series analyzed: {len(assignments)}")
            self.log(f"  - Conflicts resolved: {len(self.conflicts)}")
            self.log(f"  - New series created: {self.new_series_created}")
            
            return True
            
        except Exception as e:
            self.log(f"❌ MIGRATION FAILED: {e}", "ERROR")
            return False

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Migrate series table for league isolation")
    parser.add_argument("--live", action="store_true", help="Run live migration (default is dry run)")
    parser.add_argument("--log-file", help="Save migration log to file")
    
    args = parser.parse_args()
    
    # Run migration
    migration = SeriesLeagueMigration(dry_run=not args.live)
    success = migration.run_migration()
    
    # Save log if requested
    if args.log_file:
        with open(args.log_file, 'w') as f:
            f.write('\n'.join(migration.migration_log))
        print(f"📝 Migration log saved to: {args.log_file}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
