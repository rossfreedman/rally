#!/usr/bin/env python3
"""
Migrate Production Series Table for League Isolation
==================================================

Run series league isolation migration directly on production Railway.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import sys
from datetime import datetime

class ProductionSeriesMigration:
    def __init__(self):
        self.prod_url = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"
        self.migration_log = []
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        print(log_entry)
        self.migration_log.append(log_entry)
    
    def connect(self):
        """Connect to production database"""
        try:
            self.conn = psycopg2.connect(self.prod_url, cursor_factory=RealDictCursor)
            self.cursor = self.conn.cursor()
            self.log("✅ Connected to production database")
            return True
        except Exception as e:
            self.log(f"❌ Failed to connect: {e}", "ERROR")
            return False
    
    def check_current_state(self):
        """Check current state of series table"""
        self.log("🔍 Checking current series table state")
        
        # Check if league_id column exists
        self.cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'series' AND column_name = 'league_id'
        """)
        
        has_league_id = len(self.cursor.fetchall()) > 0
        
        # Check constraints
        self.cursor.execute("""
            SELECT conname 
            FROM pg_constraint 
            WHERE conrelid = 'series'::regclass AND conname = 'series_name_key'
        """)
        
        has_old_constraint = len(self.cursor.fetchall()) > 0
        
        # Count series
        self.cursor.execute("SELECT COUNT(*) as count FROM series")
        series_count = self.cursor.fetchone()['count']
        
        self.log(f"📊 Current state:")
        self.log(f"  - Series count: {series_count}")
        self.log(f"  - Has league_id column: {has_league_id}")
        self.log(f"  - Has old unique constraint: {has_old_constraint}")
        
        return {
            'has_league_id': has_league_id,
            'has_old_constraint': has_old_constraint,
            'series_count': series_count
        }
    
    def analyze_conflicts(self):
        """Analyze series-league conflicts"""
        self.log("🔍 Analyzing series-league conflicts")
        
        conflict_query = """
            SELECT s.id, s.name, 
                   COUNT(DISTINCT p.league_id) as league_count,
                   STRING_AGG(DISTINCT l.league_name, ', ') as leagues
            FROM series s 
            JOIN players p ON s.id = p.series_id 
            JOIN leagues l ON p.league_id = l.id 
            GROUP BY s.id, s.name 
            HAVING COUNT(DISTINCT p.league_id) > 1
            ORDER BY league_count DESC, s.name
        """
        
        self.cursor.execute(conflict_query)
        conflicts = self.cursor.fetchall()
        
        self.log(f"Found {len(conflicts)} series with multi-league conflicts")
        for conflict in conflicts:
            self.log(f"  ❌ Series {conflict['id']} ({conflict['name']}) spans {conflict['league_count']} leagues: {conflict['leagues']}")
        
        return conflicts
    
    def create_backup(self):
        """Create backup of series table"""
        self.log("💾 Creating backup of series table")
        
        try:
            self.cursor.execute("DROP TABLE IF EXISTS series_backup_production_migration")
            self.cursor.execute("CREATE TABLE series_backup_production_migration AS SELECT * FROM series")
            self.conn.commit()
            self.log("✅ Backup created: series_backup_production_migration")
        except Exception as e:
            self.log(f"❌ Backup failed: {e}", "ERROR")
            raise
    
    def add_league_id_column(self):
        """Add league_id column to series table"""
        self.log("🔧 Adding league_id column to series table")
        
        try:
            # Check if column already exists
            self.cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'series' AND column_name = 'league_id'
            """)
            
            if self.cursor.fetchall():
                self.log("ℹ️ league_id column already exists")
                return
            
            self.cursor.execute("ALTER TABLE series ADD COLUMN league_id INTEGER")
            self.conn.commit()
            self.log("✅ Added league_id column")
            
        except Exception as e:
            self.log(f"❌ Failed to add league_id column: {e}", "ERROR")
            raise
    
    def populate_league_ids(self):
        """Populate league_id for existing series"""
        self.log("📝 Populating league_id for existing series")
        
        # Get all series and their primary league associations
        league_assignment_query = """
            WITH series_league_counts AS (
                SELECT s.id as series_id, s.name as series_name,
                       p.league_id, l.league_name,
                       COUNT(*) as player_count,
                       ROW_NUMBER() OVER (PARTITION BY s.id ORDER BY COUNT(*) DESC) as rank
                FROM series s 
                JOIN players p ON s.id = p.series_id 
                JOIN leagues l ON p.league_id = l.id 
                GROUP BY s.id, s.name, p.league_id, l.league_name
            )
            SELECT series_id, series_name, league_id, league_name, player_count
            FROM series_league_counts 
            WHERE rank = 1
            ORDER BY series_name
        """
        
        self.cursor.execute(league_assignment_query)
        assignments = self.cursor.fetchall()
        
        self.log(f"Updating {len(assignments)} series with league assignments")
        
        for assignment in assignments:
            try:
                self.cursor.execute("""
                    UPDATE series 
                    SET league_id = %s 
                    WHERE id = %s
                """, (assignment['league_id'], assignment['series_id']))
                
                self.log(f"✅ Updated series {assignment['series_id']} ({assignment['series_name']}) -> league {assignment['league_id']}")
                
            except Exception as e:
                self.log(f"❌ Failed to update series {assignment['series_id']}: {e}", "ERROR")
        
        self.conn.commit()
        self.log("✅ League ID population completed")
    
    def create_conflict_series(self, conflicts):
        """Create additional series for conflicts"""
        if not conflicts:
            return
            
        self.log("🔀 Creating additional series for conflicts")
        
        for conflict in conflicts:
            # Get all leagues for this series
            self.cursor.execute("""
                SELECT DISTINCT p.league_id, l.league_name, COUNT(*) as player_count
                FROM players p 
                JOIN leagues l ON p.league_id = l.id 
                WHERE p.series_id = %s
                GROUP BY p.league_id, l.league_name
                ORDER BY player_count DESC
            """, (conflict['id'],))
            
            league_associations = self.cursor.fetchall()
            
            # Skip the primary league (already assigned), create for others
            for i, assoc in enumerate(league_associations[1:], 1):
                try:
                    new_name = f"{conflict['name']} ({assoc['league_name']})"
                    
                    self.cursor.execute("""
                        INSERT INTO series (name, display_name, league_id)
                        VALUES (%s, %s, %s)
                        RETURNING id
                    """, (new_name, new_name, assoc['league_id']))
                    
                    new_series_id = self.cursor.fetchone()['id']
                    self.log(f"✅ Created new series {new_series_id} ({new_name}) for league {assoc['league_id']}")
                    
                except Exception as e:
                    self.log(f"❌ Failed to create series for {conflict['name']}: {e}", "ERROR")
        
        self.conn.commit()
    
    def update_constraints(self):
        """Update database constraints"""
        self.log("🔒 Updating database constraints")
        
        try:
            # Add foreign key constraint
            try:
                self.cursor.execute("""
                    ALTER TABLE series 
                    ADD CONSTRAINT series_league_id_fkey 
                    FOREIGN KEY (league_id) REFERENCES leagues(id)
                """)
                self.log("✅ Added foreign key constraint: series_league_id_fkey")
            except Exception as e:
                if "already exists" in str(e):
                    self.log("ℹ️ Foreign key constraint already exists")
                else:
                    raise
            
            # Drop old unique constraint
            try:
                self.cursor.execute("ALTER TABLE series DROP CONSTRAINT series_name_key")
                self.log("✅ Dropped old unique constraint: series_name_key")
            except Exception as e:
                if "does not exist" in str(e):
                    self.log("ℹ️ Old unique constraint already removed")
                else:
                    raise
            
            # Add new composite unique constraint
            try:
                self.cursor.execute("""
                    ALTER TABLE series 
                    ADD CONSTRAINT series_name_league_unique 
                    UNIQUE (name, league_id)
                """)
                self.log("✅ Added composite unique constraint: series_name_league_unique")
            except Exception as e:
                if "already exists" in str(e):
                    self.log("ℹ️ Composite unique constraint already exists")
                else:
                    raise
            
            self.conn.commit()
            
        except Exception as e:
            self.log(f"❌ Constraint update failed: {e}", "ERROR")
            raise
    
    def verify_migration(self):
        """Verify migration success"""
        self.log("🔍 Verifying migration")
        
        # Check series with league_id
        self.cursor.execute("SELECT COUNT(*) as count FROM series WHERE league_id IS NOT NULL")
        with_league = self.cursor.fetchone()['count']
        
        self.cursor.execute("SELECT COUNT(*) as count FROM series")
        total = self.cursor.fetchone()['count']
        
        # Check for remaining conflicts
        self.cursor.execute("""
            SELECT COUNT(*) as count FROM (
                SELECT name, league_id, COUNT(*) 
                FROM series 
                WHERE league_id IS NOT NULL
                GROUP BY name, league_id 
                HAVING COUNT(*) > 1
            ) conflicts
        """)
        remaining_conflicts = self.cursor.fetchone()['count']
        
        self.log(f"📊 Migration verification:")
        self.log(f"  - Total series: {total}")
        self.log(f"  - Series with league_id: {with_league}")
        self.log(f"  - Remaining conflicts: {remaining_conflicts}")
        
        success = remaining_conflicts == 0 and with_league > 0
        if success:
            self.log("✅ Migration verification successful!")
        else:
            self.log("❌ Migration verification failed!", "ERROR")
        
        return success
    
    def run_migration(self):
        """Run the complete migration"""
        self.log("🚀 STARTING PRODUCTION SERIES MIGRATION")
        
        if not self.connect():
            return False
        
        try:
            # Check current state
            current_state = self.check_current_state()
            
            if current_state['has_league_id']:
                self.log("⚠️ Migration appears to already be completed")
                return True
            
            # Analyze conflicts
            conflicts = self.analyze_conflicts()
            
            # Create backup
            self.create_backup()
            
            # Add league_id column
            self.add_league_id_column()
            
            # Populate league IDs
            self.populate_league_ids()
            
            # Create additional series for conflicts
            self.create_conflict_series(conflicts)
            
            # Update constraints
            self.update_constraints()
            
            # Verify success
            success = self.verify_migration()
            
            if success:
                self.log("✅ PRODUCTION SERIES MIGRATION COMPLETED SUCCESSFULLY")
            else:
                self.log("❌ PRODUCTION SERIES MIGRATION FAILED", "ERROR")
            
            return success
            
        except Exception as e:
            self.log(f"❌ Migration failed with error: {e}", "ERROR")
            self.conn.rollback()
            return False
        finally:
            self.conn.close()

def main():
    print("🚀 PRODUCTION SERIES MIGRATION")
    print("=" * 50)
    
    migration = ProductionSeriesMigration()
    success = migration.run_migration()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
