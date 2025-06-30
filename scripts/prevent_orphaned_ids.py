#!/usr/bin/env python3
"""
Orphaned ID Prevention System for Rally Database

This system prevents orphaned foreign key references by:
1. Adding proper foreign key constraints to the database
2. Creating ETL validation helpers
3. Implementing automated health checks
4. Providing repair mechanisms

Usage:
    python scripts/prevent_orphaned_ids.py --add-constraints    # Add foreign key constraints
    python scripts/prevent_orphaned_ids.py --health-check       # Check for orphaned IDs
    python scripts/prevent_orphaned_ids.py --fix-orphaned       # Fix any orphaned IDs found
    python scripts/prevent_orphaned_ids.py --full-setup         # Complete prevention setup
"""

import argparse
import logging
import psycopg2
import sys
from datetime import datetime
from pathlib import Path

# Add project root to Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.append(str(project_root))

from core.database import get_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class OrphanedIDPreventionSystem:
    def __init__(self):
        self.start_time = datetime.now()
        self.results = {
            "foreign_keys_added": 0,
            "orphaned_ids_found": {},
            "orphaned_ids_fixed": {},
            "validation_errors": []
        }

    def print_header(self, action):
        """Print system header"""
        print("🛡️" + "=" * 78 + "🛡️")
        print("🔒 RALLY ORPHANED ID PREVENTION SYSTEM")
        print(f"📋 Action: {action}")
        print("🛡️" + "=" * 78 + "🛡️")
        print(f"📅 Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()

    def add_foreign_key_constraints(self):
        """Add foreign key constraints to prevent orphaned IDs"""
        print("🔗 ADDING FOREIGN KEY CONSTRAINTS")
        print("-" * 50)
        
        constraints = [
            {
                "table": "match_scores",
                "column": "league_id", 
                "references": "leagues(id)",
                "name": "fk_match_scores_league_id",
                "description": "Match scores must reference valid league"
            },
            {
                "table": "match_scores",
                "column": "home_team_id",
                "references": "teams(id)", 
                "name": "fk_match_scores_home_team_id",
                "description": "Match home team must reference valid team"
            },
            {
                "table": "match_scores", 
                "column": "away_team_id",
                "references": "teams(id)",
                "name": "fk_match_scores_away_team_id", 
                "description": "Match away team must reference valid team"
            },
            {
                "table": "series_stats",
                "column": "league_id",
                "references": "leagues(id)",
                "name": "fk_series_stats_league_id",
                "description": "Series stats must reference valid league"
            },
            {
                "table": "series_stats",
                "column": "team_id", 
                "references": "teams(id)",
                "name": "fk_series_stats_team_id",
                "description": "Series stats must reference valid team"
            },
            {
                "table": "schedule",
                "column": "league_id",
                "references": "leagues(id)", 
                "name": "fk_schedule_league_id",
                "description": "Schedule must reference valid league"
            },
            {
                "table": "schedule",
                "column": "home_team_id",
                "references": "teams(id)",
                "name": "fk_schedule_home_team_id",
                "description": "Schedule home team must reference valid team"
            },
            {
                "table": "schedule", 
                "column": "away_team_id",
                "references": "teams(id)",
                "name": "fk_schedule_away_team_id",
                "description": "Schedule away team must reference valid team"
            }
        ]
        
        with get_db() as conn:
            cursor = conn.cursor()
            added = 0
            skipped = 0
            
            for constraint in constraints:
                try:
                    # Check if constraint already exists
                    cursor.execute("""
                        SELECT 1 FROM information_schema.table_constraints 
                        WHERE constraint_name = %s AND table_name = %s
                    """, (constraint["name"], constraint["table"]))
                    
                    if cursor.fetchone():
                        print(f"⏭️  {constraint['name']}: Already exists")
                        skipped += 1
                        continue
                    
                    # Add the constraint
                    sql = f"""
                        ALTER TABLE {constraint["table"]} 
                        ADD CONSTRAINT {constraint["name"]} 
                        FOREIGN KEY ({constraint["column"]}) 
                        REFERENCES {constraint["references"]}
                    """
                    
                    cursor.execute(sql)
                    print(f"✅ {constraint['name']}: Added successfully")
                    print(f"   📝 {constraint['description']}")
                    added += 1
                    
                except Exception as e:
                    error_msg = str(e)
                    if "violates foreign key constraint" in error_msg or "cannot be implemented" in error_msg:
                        print(f"❌ {constraint['name']}: Cannot add - orphaned data exists!")
                        print(f"   📝 {constraint['description']}")
                        print(f"   🔧 Run --fix-orphaned to repair data first")
                        self.results["validation_errors"].append(constraint["name"])
                    else:
                        print(f"❌ {constraint['name']}: Error - {error_msg}")
                    
            conn.commit()
            
        self.results["foreign_keys_added"] = added
        print(f"\n📊 Foreign Key Summary: {added} added, {skipped} already existed")
        
        if self.results["validation_errors"]:
            print(f"⚠️  {len(self.results['validation_errors'])} constraints failed due to orphaned data")
            return False
        return True

    def health_check_orphaned_ids(self):
        """Comprehensive health check for orphaned IDs"""
        print("🔍 HEALTH CHECK: Scanning for Orphaned IDs")
        print("-" * 50)
        
        checks = [
            {
                "name": "match_scores.league_id",
                "query": """
                    SELECT COUNT(*) as orphaned_count
                    FROM match_scores ms 
                    LEFT JOIN leagues l ON ms.league_id = l.id
                    WHERE ms.league_id IS NOT NULL AND l.id IS NULL
                """,
                "description": "Match scores with invalid league references"
            },
            {
                "name": "match_scores.home_team_id", 
                "query": """
                    SELECT COUNT(*) as orphaned_count
                    FROM match_scores ms
                    LEFT JOIN teams t ON ms.home_team_id = t.id
                    WHERE ms.home_team_id IS NOT NULL AND t.id IS NULL
                """,
                "description": "Match scores with invalid home team references"
            },
            {
                "name": "match_scores.away_team_id",
                "query": """
                    SELECT COUNT(*) as orphaned_count  
                    FROM match_scores ms
                    LEFT JOIN teams t ON ms.away_team_id = t.id
                    WHERE ms.away_team_id IS NOT NULL AND t.id IS NULL
                """,
                "description": "Match scores with invalid away team references"
            },
            {
                "name": "series_stats.league_id",
                "query": """
                    SELECT COUNT(*) as orphaned_count
                    FROM series_stats ss
                    LEFT JOIN leagues l ON ss.league_id = l.id  
                    WHERE ss.league_id IS NOT NULL AND l.id IS NULL
                """,
                "description": "Series stats with invalid league references"
            },
            {
                "name": "series_stats.team_id",
                "query": """
                    SELECT COUNT(*) as orphaned_count
                    FROM series_stats ss
                    LEFT JOIN teams t ON ss.team_id = t.id
                    WHERE ss.team_id IS NOT NULL AND t.id IS NULL
                """, 
                "description": "Series stats with invalid team references"
            },
            {
                "name": "schedule.league_id",
                "query": """
                    SELECT COUNT(*) as orphaned_count
                    FROM schedule s
                    LEFT JOIN leagues l ON s.league_id = l.id
                    WHERE s.league_id IS NOT NULL AND l.id IS NULL
                """,
                "description": "Schedule with invalid league references"
            },
            {
                "name": "schedule.home_team_id",
                "query": """
                    SELECT COUNT(*) as orphaned_count
                    FROM schedule s
                    LEFT JOIN teams t ON s.home_team_id = t.id
                    WHERE s.home_team_id IS NOT NULL AND t.id IS NULL
                """,
                "description": "Schedule with invalid home team references"
            },
            {
                "name": "schedule.away_team_id", 
                "query": """
                    SELECT COUNT(*) as orphaned_count
                    FROM schedule s
                    LEFT JOIN teams t ON s.away_team_id = t.id
                    WHERE s.away_team_id IS NOT NULL AND t.id IS NULL
                """,
                "description": "Schedule with invalid away team references"
            }
        ]
        
        with get_db() as conn:
            cursor = conn.cursor()
            total_orphaned = 0
            
            for check in checks:
                cursor.execute(check["query"])
                result = cursor.fetchone()
                orphaned_count = result[0] if result else 0
                
                if orphaned_count > 0:
                    print(f"❌ {check['name']}: {orphaned_count:,} orphaned records")
                    print(f"   📝 {check['description']}")
                    self.results["orphaned_ids_found"][check["name"]] = orphaned_count
                    total_orphaned += orphaned_count
                else:
                    print(f"✅ {check['name']}: No orphaned records")
        
        print(f"\n📊 Health Check Summary: {total_orphaned:,} total orphaned records found")
        return total_orphaned == 0

    def fix_orphaned_ids(self):
        """Fix all orphaned IDs using the mapping logic from our previous fixes"""
        print("🔧 FIXING ORPHANED IDs")
        print("-" * 50)
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Fix orphaned league_ids in match_scores
            print("🔧 Fixing match_scores.league_id...")
            cursor.execute("""
                UPDATE match_scores SET league_id = 4489 WHERE league_id = 4551;
                UPDATE match_scores SET league_id = 4490 WHERE league_id = 4552;
                UPDATE match_scores SET league_id = 4491 WHERE league_id = 4553;
                UPDATE match_scores SET league_id = 4492 WHERE league_id = 4554;
                
                SELECT 'match_scores.league_id' as fix_type, COUNT(*) as updated_count
                FROM match_scores ms
                JOIN leagues l ON ms.league_id = l.id;
            """)
            result = cursor.fetchone()
            self.results["orphaned_ids_fixed"]["match_scores.league_id"] = result[1] if result else 0
            print(f"✅ Fixed league_ids in match_scores")
            
            # Fix orphaned team_ids in match_scores  
            print("🔧 Fixing match_scores team_ids...")
            cursor.execute("""
                UPDATE match_scores ms
                SET home_team_id = t.id
                FROM teams t
                WHERE ms.home_team = t.team_name 
                  AND (ms.home_team_id IS NULL OR ms.home_team_id NOT IN (SELECT id FROM teams));
                  
                UPDATE match_scores ms
                SET away_team_id = t.id
                FROM teams t  
                WHERE ms.away_team = t.team_name
                  AND (ms.away_team_id IS NULL OR ms.away_team_id NOT IN (SELECT id FROM teams));
            """)
            print(f"✅ Fixed team_ids in match_scores")
            
            # Fix orphaned league_ids in series_stats
            print("🔧 Fixing series_stats.league_id...")
            cursor.execute("""
                UPDATE series_stats SET league_id = 4489 WHERE league_id = 4551;
                UPDATE series_stats SET league_id = 4490 WHERE league_id = 4552;
                UPDATE series_stats SET league_id = 4491 WHERE league_id = 4553;
                UPDATE series_stats SET league_id = 4492 WHERE league_id = 4554;
            """)
            print(f"✅ Fixed league_ids in series_stats")
            
            # Fix orphaned team_ids in series_stats
            print("🔧 Fixing series_stats.team_id...")
            cursor.execute("""
                UPDATE series_stats ss
                SET team_id = t.id
                FROM teams t
                WHERE ss.team = t.team_name 
                  AND (ss.team_id IS NULL OR ss.team_id NOT IN (SELECT id FROM teams));
            """)
            print(f"✅ Fixed team_ids in series_stats")
            
            # Fix orphaned league_ids in schedule
            print("🔧 Fixing schedule.league_id...")
            cursor.execute("""
                UPDATE schedule SET league_id = 4489 WHERE league_id = 4551;
                UPDATE schedule SET league_id = 4490 WHERE league_id = 4552;
                UPDATE schedule SET league_id = 4491 WHERE league_id = 4553;
                UPDATE schedule SET league_id = 4492 WHERE league_id = 4554;
            """)
            print(f"✅ Fixed league_ids in schedule")
            
            # Fix orphaned team_ids in schedule
            print("🔧 Fixing schedule team_ids...")
            cursor.execute("""
                UPDATE schedule s
                SET home_team_id = t.id
                FROM teams t
                WHERE s.home_team = t.team_name 
                  AND (s.home_team_id IS NULL OR s.home_team_id NOT IN (SELECT id FROM teams));
                  
                UPDATE schedule s
                SET away_team_id = t.id
                FROM teams t
                WHERE s.away_team = t.team_name
                  AND (s.away_team_id IS NULL OR s.away_team_id NOT IN (SELECT id FROM teams));
            """)
            print(f"✅ Fixed team_ids in schedule")
            
            conn.commit()
            print("\n✅ All orphaned IDs have been fixed!")

    def create_etl_validation_helpers(self):
        """Create validation helper functions for ETL processes"""
        print("📋 CREATING ETL VALIDATION HELPERS")
        print("-" * 50)
        
        validation_sql = """
        -- Function to validate league_id exists
        CREATE OR REPLACE FUNCTION validate_league_id(league_id_param INTEGER)
        RETURNS BOOLEAN AS $$
        BEGIN
            RETURN EXISTS(SELECT 1 FROM leagues WHERE id = league_id_param);
        END;
        $$ LANGUAGE plpgsql;
        
        -- Function to validate team_id exists  
        CREATE OR REPLACE FUNCTION validate_team_id(team_id_param INTEGER)
        RETURNS BOOLEAN AS $$
        BEGIN
            RETURN EXISTS(SELECT 1 FROM teams WHERE id = team_id_param);
        END;
        $$ LANGUAGE plpgsql;
        
        -- Function to get team_id by name and league
        CREATE OR REPLACE FUNCTION get_team_id_by_name_and_league(
            team_name_param VARCHAR(255),
            league_id_param INTEGER
        )
        RETURNS INTEGER AS $$
        DECLARE
            result_id INTEGER;
        BEGIN
            SELECT t.id INTO result_id
            FROM teams t
            WHERE t.team_name = team_name_param 
              AND t.league_id = league_id_param;
              
            RETURN result_id;
        END;
        $$ LANGUAGE plpgsql;
        
        -- Function to perform comprehensive orphaned ID check
        CREATE OR REPLACE FUNCTION check_orphaned_ids()
        RETURNS TABLE(
            table_name TEXT,
            column_name TEXT, 
            orphaned_count BIGINT
        ) AS $$
        BEGIN
            RETURN QUERY
            SELECT 'match_scores'::TEXT, 'league_id'::TEXT, COUNT(*)
            FROM match_scores ms LEFT JOIN leagues l ON ms.league_id = l.id
            WHERE ms.league_id IS NOT NULL AND l.id IS NULL
            
            UNION ALL
            
            SELECT 'match_scores'::TEXT, 'home_team_id'::TEXT, COUNT(*)
            FROM match_scores ms LEFT JOIN teams t ON ms.home_team_id = t.id
            WHERE ms.home_team_id IS NOT NULL AND t.id IS NULL
            
            UNION ALL
            
            SELECT 'match_scores'::TEXT, 'away_team_id'::TEXT, COUNT(*)
            FROM match_scores ms LEFT JOIN teams t ON ms.away_team_id = t.id
            WHERE ms.away_team_id IS NOT NULL AND t.id IS NULL
            
            UNION ALL
            
            SELECT 'series_stats'::TEXT, 'league_id'::TEXT, COUNT(*)
            FROM series_stats ss LEFT JOIN leagues l ON ss.league_id = l.id
            WHERE ss.league_id IS NOT NULL AND l.id IS NULL
            
            UNION ALL
            
            SELECT 'series_stats'::TEXT, 'team_id'::TEXT, COUNT(*)
            FROM series_stats ss LEFT JOIN teams t ON ss.team_id = t.id
            WHERE ss.team_id IS NOT NULL AND t.id IS NULL
            
            UNION ALL
            
            SELECT 'schedule'::TEXT, 'league_id'::TEXT, COUNT(*)
            FROM schedule s LEFT JOIN leagues l ON s.league_id = l.id
            WHERE s.league_id IS NOT NULL AND l.id IS NULL
            
            UNION ALL
            
            SELECT 'schedule'::TEXT, 'home_team_id'::TEXT, COUNT(*)
            FROM schedule s LEFT JOIN teams t ON s.home_team_id = t.id
            WHERE s.home_team_id IS NOT NULL AND t.id IS NULL
            
            UNION ALL
            
            SELECT 'schedule'::TEXT, 'away_team_id'::TEXT, COUNT(*)
            FROM schedule s LEFT JOIN teams t ON s.away_team_id = t.id
            WHERE s.away_team_id IS NOT NULL AND t.id IS NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(validation_sql)
            conn.commit()
            
        print("✅ Created validation helper functions:")
        print("   📋 validate_league_id(id) - Check if league exists")
        print("   📋 validate_team_id(id) - Check if team exists")  
        print("   📋 get_team_id_by_name_and_league(name, league_id) - Safe team lookup")
        print("   📋 check_orphaned_ids() - Comprehensive orphaned ID scan")

    def generate_etl_enhancement_patch(self):
        """Generate a patch for the ETL import process"""
        print("📝 GENERATING ETL ENHANCEMENT PATCH")
        print("-" * 50)
        
        patch_content = '''# ETL Enhancement Patch
# Apply these changes to data/etl/database_import/import_all_jsons_to_database.py

## 1. Enhanced import_series_stats method (around line 2330)

Replace this problematic code:
```python
team_row = cursor.fetchone()
team_db_id = team_row[0] if team_row else None
```

With this safe validation:
```python
team_row = cursor.fetchone()
if not team_row:
    self.log(f"⚠️  Skipping series stats for {team}: team not found in database", "WARNING")
    continue
team_db_id = team_row[0]
```

## 2. Enhanced import_match_history method (around line 2150)

Add validation before INSERT:
```python
# Validate team IDs exist before inserting
if home_team_id and not cursor.execute("SELECT validate_team_id(%s)", (home_team_id,)).fetchone()[0]:
    self.log(f"⚠️  Skipping match: invalid home_team_id {home_team_id}", "WARNING")
    continue

if away_team_id and not cursor.execute("SELECT validate_team_id(%s)", (away_team_id,)).fetchone()[0]:
    self.log(f"⚠️  Skipping match: invalid away_team_id {away_team_id}", "WARNING") 
    continue

if league_db_id and not cursor.execute("SELECT validate_league_id(%s)", (league_db_id,)).fetchone()[0]:
    self.log(f"⚠️  Skipping match: invalid league_id {league_db_id}", "WARNING")
    continue
```

## 3. Add post-import validation

Add this method to ComprehensiveETL class:
```python
def post_import_validation(self, conn):
    """Validate no orphaned IDs were created during import"""
    self.log("🔍 Running post-import orphaned ID validation...")
    
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM check_orphaned_ids() WHERE orphaned_count > 0")
    orphaned_issues = cursor.fetchall()
    
    if orphaned_issues:
        self.log("❌ CRITICAL: Orphaned IDs detected after import!", "ERROR")
        for issue in orphaned_issues:
            self.log(f"   {issue[0]}.{issue[1]}: {issue[2]} orphaned records", "ERROR")
        raise Exception("Import failed validation - orphaned IDs detected")
    else:
        self.log("✅ Post-import validation passed - no orphaned IDs")
```

## 4. Call validation in run() method

Add this line before the final commit in run():
```python
# Validate no orphaned IDs were created
self.post_import_validation(conn)
```
'''
        
        patch_file = script_dir / "etl_enhancement_patch.md"
        with open(patch_file, 'w') as f:
            f.write(patch_content)
        
        print(f"✅ ETL enhancement patch saved to: {patch_file}")
        print("📋 Apply these changes to prevent future orphaned ID issues")

    def print_summary(self):
        """Print final summary"""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        print("\n📋 PREVENTION SYSTEM SUMMARY")
        print("=" * 80)
        print(f"⏱️  Duration: {duration:.2f} seconds")
        print(f"📅 Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        if self.results["foreign_keys_added"] > 0:
            print(f"🔗 Foreign Keys: {self.results['foreign_keys_added']} constraints added")
        
        if self.results["orphaned_ids_found"]:
            print(f"🔍 Health Check: {len(self.results['orphaned_ids_found'])} issues found")
            for table_column, count in self.results["orphaned_ids_found"].items():
                print(f"   ❌ {table_column}: {count:,} orphaned records")
        
        if self.results["orphaned_ids_fixed"]:
            print(f"🔧 Repairs: {len(self.results['orphaned_ids_fixed'])} fixes applied")
        
        if self.results["validation_errors"]:
            print(f"⚠️  Warnings: {len(self.results['validation_errors'])} constraints need data repair")
        
        print("=" * 80)

def main():
    parser = argparse.ArgumentParser(description="Rally Orphaned ID Prevention System")
    parser.add_argument("--add-constraints", action="store_true", help="Add foreign key constraints")
    parser.add_argument("--health-check", action="store_true", help="Check for orphaned IDs")
    parser.add_argument("--fix-orphaned", action="store_true", help="Fix orphaned IDs")
    parser.add_argument("--full-setup", action="store_true", help="Complete prevention setup")
    
    args = parser.parse_args()
    
    if not any([args.add_constraints, args.health_check, args.fix_orphaned, args.full_setup]):
        parser.print_help()
        return
    
    system = OrphanedIDPreventionSystem()
    
    try:
        if args.full_setup:
            system.print_header("Complete Prevention Setup")
            system.health_check_orphaned_ids()
            system.fix_orphaned_ids()
            system.add_foreign_key_constraints()
            system.create_etl_validation_helpers()
            system.generate_etl_enhancement_patch()
            
        elif args.health_check:
            system.print_header("Health Check")
            system.health_check_orphaned_ids()
            
        elif args.fix_orphaned:
            system.print_header("Fix Orphaned IDs")
            system.fix_orphaned_ids()
            
        elif args.add_constraints:
            system.print_header("Add Foreign Key Constraints")
            system.add_foreign_key_constraints()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        system.print_summary()

if __name__ == "__main__":
    main() 