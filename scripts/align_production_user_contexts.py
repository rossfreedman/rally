#!/usr/bin/env python3
"""
Align Production user_contexts Schema
====================================

Align production user_contexts table schema to match local/staging (5 columns).
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import sys
from datetime import datetime

class UserContextsSchemaAlignment:
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
    
    def check_current_schema(self):
        """Check current user_contexts schema"""
        self.log("🔍 Checking current user_contexts schema")
        
        self.cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'user_contexts'
            ORDER BY ordinal_position
        """)
        
        columns = self.cursor.fetchall()
        self.log(f"📊 Current schema ({len(columns)} columns):")
        
        column_names = []
        for col in columns:
            nullable = "NULL" if col['is_nullable'] == "YES" else "NOT NULL"
            self.log(f"  - {col['column_name']}: {col['data_type']} ({nullable})")
            column_names.append(col['column_name'])
        
        return column_names
    
    def create_backup(self):
        """Create backup of user_contexts table"""
        self.log("💾 Creating backup of user_contexts table")
        
        try:
            self.cursor.execute("DROP TABLE IF EXISTS user_contexts_backup_production")
            self.cursor.execute("CREATE TABLE user_contexts_backup_production AS SELECT * FROM user_contexts")
            self.conn.commit()
            self.log("✅ Backup created: user_contexts_backup_production")
        except Exception as e:
            self.log(f"❌ Backup failed: {e}", "ERROR")
            raise
    
    def check_data_integrity(self):
        """Check data that would be preserved"""
        self.log("🔍 Checking data integrity for migration")
        
        # Count total records
        self.cursor.execute("SELECT COUNT(*) as count FROM user_contexts")
        total_records = self.cursor.fetchone()['count']
        
        # Check key fields that will be preserved
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(user_id) as with_user_id,
                COUNT(league_id) as with_league_id,
                COUNT(team_id) as with_team_id,
                COUNT(series_id) as with_series_id
            FROM user_contexts
        """)
        
        data_check = self.cursor.fetchone()
        
        self.log(f"📊 Data preservation check:")
        self.log(f"  - Total records: {total_records}")
        self.log(f"  - Records with user_id: {data_check['with_user_id']}")
        self.log(f"  - Records with league_id: {data_check['with_league_id']}")
        self.log(f"  - Records with team_id: {data_check['with_team_id']}")
        self.log(f"  - Records with series_id: {data_check['with_series_id']}")
        
        return data_check
    
    def create_new_schema_table(self):
        """Create new user_contexts table with aligned schema"""
        self.log("🔧 Creating new user_contexts table with aligned schema")
        
        try:
            # Rename existing table
            self.cursor.execute("ALTER TABLE user_contexts RENAME TO user_contexts_old_schema")
            self.log("✅ Renamed existing table to user_contexts_old_schema")
            
            # Create new table with 5-column schema (matching local/staging)
            create_sql = """
                CREATE TABLE user_contexts (
                    user_id INTEGER NOT NULL,
                    league_id INTEGER,
                    team_id INTEGER,
                    series_id INTEGER,
                    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    
                    CONSTRAINT user_contexts_new_pkey PRIMARY KEY (user_id),
                    CONSTRAINT fk_user_contexts_user_new FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    CONSTRAINT fk_user_contexts_league_new FOREIGN KEY (league_id) REFERENCES leagues(id) ON DELETE SET NULL,
                    CONSTRAINT fk_user_contexts_team_new FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE SET NULL,
                    CONSTRAINT user_contexts_series_id_fkey_new FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET NULL
                );
            """
            
            self.cursor.execute(create_sql)
            self.log("✅ Created new user_contexts table with 5-column schema")
            
            # Migrate data from old table to new table
            migrate_sql = """
                INSERT INTO user_contexts (user_id, league_id, team_id, series_id, last_updated)
                SELECT 
                    user_id, 
                    league_id, 
                    team_id, 
                    series_id,
                    COALESCE(updated_at, created_at, NOW())
                FROM user_contexts_old_schema
                ON CONFLICT (user_id) DO UPDATE SET
                    league_id = EXCLUDED.league_id,
                    team_id = EXCLUDED.team_id,
                    series_id = EXCLUDED.series_id,
                    last_updated = EXCLUDED.last_updated
            """
            
            self.cursor.execute(migrate_sql)
            migrated_count = self.cursor.rowcount
            self.log(f"✅ Migrated {migrated_count} records to new schema")
            
            self.conn.commit()
            
        except Exception as e:
            self.log(f"❌ Schema migration failed: {e}", "ERROR")
            self.conn.rollback()
            raise
    
    def grant_permissions(self):
        """Grant proper permissions to new table"""
        self.log("🔐 Granting permissions to new user_contexts table")
        
        try:
            permission_sqls = [
                "GRANT SELECT ON user_contexts TO PUBLIC;",
                "GRANT INSERT ON user_contexts TO PUBLIC;", 
                "GRANT UPDATE ON user_contexts TO PUBLIC;",
                "GRANT DELETE ON user_contexts TO PUBLIC;"
            ]
            
            for sql in permission_sqls:
                self.cursor.execute(sql)
                
            self.conn.commit()
            self.log("✅ Permissions granted")
            
        except Exception as e:
            self.log(f"❌ Permission grant failed: {e}", "ERROR")
            raise
    
    def verify_migration(self):
        """Verify schema migration success"""
        self.log("🔍 Verifying schema migration")
        
        # Check new schema
        self.cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'user_contexts'
            ORDER BY ordinal_position
        """)
        
        new_columns = self.cursor.fetchall()
        self.log(f"📊 New schema ({len(new_columns)} columns):")
        for col in new_columns:
            nullable = "NULL" if col['is_nullable'] == "YES" else "NOT NULL"
            self.log(f"  ✅ {col['column_name']}: {col['data_type']} ({nullable})")
        
        # Check data count
        self.cursor.execute("SELECT COUNT(*) as count FROM user_contexts")
        new_count = self.cursor.fetchone()['count']
        
        self.cursor.execute("SELECT COUNT(*) as count FROM user_contexts_old_schema")
        old_count = self.cursor.fetchone()['count']
        
        self.log(f"📊 Data verification:")
        self.log(f"  - Old table records: {old_count}")
        self.log(f"  - New table records: {new_count}")
        
        # Test basic functionality
        try:
            self.cursor.execute("SELECT COUNT(*) FROM user_contexts WHERE user_id IS NOT NULL")
            test_count = self.cursor.fetchone()['count']
            self.log(f"  - Test query successful: {test_count} valid records")
            
            success = len(new_columns) == 5 and new_count == old_count
            if success:
                self.log("✅ Schema migration verification successful!")
            else:
                self.log("❌ Schema migration verification failed!", "ERROR")
            
            return success
            
        except Exception as e:
            self.log(f"❌ Verification test failed: {e}", "ERROR")
            return False
    
    def run_migration(self):
        """Run the complete schema alignment"""
        self.log("🚀 STARTING USER_CONTEXTS SCHEMA ALIGNMENT")
        
        if not self.connect():
            return False
        
        try:
            # Check current schema
            current_columns = self.check_current_schema()
            
            if len(current_columns) == 5:
                self.log("✅ Schema already aligned (5 columns)")
                return True
            
            # Check data integrity
            data_check = self.check_data_integrity()
            
            # Create backup
            self.create_backup()
            
            # Create new schema table and migrate data
            self.create_new_schema_table()
            
            # Grant permissions
            self.grant_permissions()
            
            # Verify migration
            success = self.verify_migration()
            
            if success:
                self.log("✅ USER_CONTEXTS SCHEMA ALIGNMENT COMPLETED SUCCESSFULLY")
            else:
                self.log("❌ USER_CONTEXTS SCHEMA ALIGNMENT FAILED", "ERROR")
            
            return success
            
        except Exception as e:
            self.log(f"❌ Schema alignment failed with error: {e}", "ERROR")
            self.conn.rollback()
            return False
        finally:
            self.conn.close()

def main():
    print("🚀 PRODUCTION USER_CONTEXTS SCHEMA ALIGNMENT")
    print("=" * 50)
    
    migration = UserContextsSchemaAlignment()
    success = migration.run_migration()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
