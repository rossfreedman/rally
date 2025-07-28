#!/usr/bin/env python3
"""
ETL Integration Example - Enhanced Practice Time Protection
==========================================================

This file shows how to integrate the enhanced practice time protection
into the main import_all_jsons_to_database.py script.

Key Integration Points:
1. Pre-ETL safety validation
2. Enhanced backup during backup_user_data_and_team_mappings()
3. Improved restoration in restore_user_data_with_team_mappings()
4. Post-ETL health validation
"""

# Import the protection functions
from enhanced_practice_time_protection import (
    validate_etl_safety_preconditions,
    create_enhanced_practice_time_backup, 
    validate_team_id_preservation_post_etl,
    restore_practice_times_with_fallback,
    validate_practice_time_health,
    cleanup_enhanced_backup_tables
)

class EnhancedComprehensiveETL:
    """
    Example of how to enhance the ComprehensiveETL class with
    improved practice time protection
    """
    
    def __init__(self):
        self.practice_time_count_pre_etl = 0
        # ... existing initialization
        
    def run(self):
        """Enhanced ETL run method with practice time protection"""
        try:
            # ... existing setup code ...
            
            with self.get_managed_db_connection() as conn:
                cursor = conn.cursor()
                
                # ENHANCEMENT 1: Pre-ETL Safety Validation
                self.log("\n🛡️ Step 0: Pre-ETL Safety Validation...")
                is_safe, issues = validate_etl_safety_preconditions(cursor, self)
                
                if not is_safe:
                    self.log("🚨 ETL SAFETY ISSUES FOUND:", "ERROR")
                    for issue in issues:
                        self.log(f"   ❌ {issue}", "ERROR")
                    self.log("⚠️  ETL ABORTED - Fix these issues first!", "ERROR")
                    return False
                else:
                    self.log("✅ ETL safety validation passed")
                
                # Count practice times before ETL
                cursor.execute("SELECT COUNT(*) FROM schedule WHERE home_team ILIKE '%practice%'")
                self.practice_time_count_pre_etl = cursor.fetchone()[0]
                self.log(f"📊 Pre-ETL practice times: {self.practice_time_count_pre_etl}")
                
                # Ensure schema requirements
                self.ensure_schema_requirements(conn)

                # ENHANCEMENT 2: Enhanced backup (replaces existing backup_user_data_and_team_mappings)
                self.enhanced_backup_user_data_and_team_mappings(conn)

                # Import basic reference data first
                self.log("\n📥 Step 4: Importing basic reference data...")
                self.import_leagues(conn, leagues_data)
                self.import_clubs(conn, clubs_data)

                # ... existing import steps ...
                
                # ENHANCEMENT 3: Enhanced restoration (replaces existing restore_user_data_with_team_mappings)
                self.log("\n🔄 Step 7: Enhanced user data restoration...")
                self.enhanced_restore_user_data_with_team_mappings(conn)
                
                # ENHANCEMENT 4: Post-ETL Health Validation
                self.log("\n🔍 Step 8: Post-ETL Health Validation...")
                health_stats = validate_practice_time_health(
                    cursor, self.practice_time_count_pre_etl, self
                )
                
                if not health_stats["is_healthy"]:
                    self.log("🚨 CRITICAL: Practice time health check failed!", "ERROR")
                    self.log("🔧 This indicates practice times were lost during ETL", "ERROR")
                    return False
                else:
                    self.log("✅ Practice time health check passed")
                
                # Clean up backup tables
                cleanup_enhanced_backup_tables(cursor, self)
                
                # ... existing completion code ...
                
                return True
                
        except Exception as e:
            self.log(f"💥 ETL FAILED: {str(e)}", "ERROR")
            return False
    
    def enhanced_backup_user_data_and_team_mappings(self, conn):
        """Enhanced backup with practice time protection"""
        self.log("💾 Starting enhanced user data backup...")
        
        cursor = conn.cursor()
        
        # Existing polls backup (unchanged)
        self.log("📊 Backing up polls with team IDs...")
        cursor.execute("""
            DROP TABLE IF EXISTS polls_backup;
            CREATE TABLE polls_backup AS
            SELECT * FROM polls
        """)
        
        # Existing captain messages backup (unchanged)
        self.log("💬 Backing up captain messages with team IDs...")
        cursor.execute("""
            DROP TABLE IF EXISTS captain_messages_backup;
            CREATE TABLE captain_messages_backup AS
            SELECT * FROM captain_messages
        """)
        
        # ENHANCEMENT: Enhanced practice time backup (replaces simple backup)
        practice_backup_count = create_enhanced_practice_time_backup(cursor, self)
        
        # Existing user associations backup (unchanged)
        # ... existing backup code ...
        
        self.log(f"✅ Enhanced backup completed - {practice_backup_count} practice times backed up")
    
    def enhanced_restore_user_data_with_team_mappings(self, conn):
        """Enhanced restoration with fallback logic"""
        self.log("🔄 Starting enhanced user data restoration...")
        
        cursor = conn.cursor()
        
        # Existing polls restoration (unchanged)
        # ... existing polls restoration code ...
        
        # Existing captain messages restoration (unchanged)  
        # ... existing captain messages restoration code ...
        
        # ENHANCEMENT: Validate team ID preservation first
        preservation_success, preservation_stats = validate_team_id_preservation_post_etl(cursor, self)
        
        if preservation_success:
            self.log("✅ Team ID preservation successful - using direct restoration")
            # Use existing direct restoration method
            self._restore_practice_times(conn)
        else:
            self.log("⚠️  Team ID preservation failed - using enhanced fallback restoration")
            # Use enhanced fallback restoration
            restoration_stats = restore_practice_times_with_fallback(cursor, self, dry_run=False)
            self.log(f"✅ Fallback restoration: {restoration_stats['direct']} direct + {restoration_stats['fallback']} fallback = {restoration_stats['total']} total")
        
        # ... existing restoration code for other data types ...
        
        self.log("✅ Enhanced restoration completed")
    
    def clear_target_tables(self, conn):
        """Enhanced table clearing with safety checks"""
        self.log("🗑️  Clearing existing data from target tables...")

        # ENHANCEMENT: Enhanced backup before clearing (replaces existing backup)
        self.enhanced_backup_user_data_and_team_mappings(conn)

        # Existing table clearing logic (unchanged)
        tables_to_clear = [
            "schedule",  # No dependencies
            "series_stats",  # References leagues, teams
            # ... existing table list ...
        ]
        
        # ... existing clearing code ...
        
        self.log(f"✅ Target tables cleared with enhanced backup protection")


# Example integration patch for existing ETL script
INTEGRATION_INSTRUCTIONS = """
🔧 How to integrate enhanced practice time protection:

1. **Add import statement** at the top of import_all_jsons_to_database.py:
   ```python
   from enhanced_practice_time_protection import (
       validate_etl_safety_preconditions,
       create_enhanced_practice_time_backup, 
       validate_team_id_preservation_post_etl,
       restore_practice_times_with_fallback,
       validate_practice_time_health,
       cleanup_enhanced_backup_tables
   )
   ```

2. **Enhance the run() method** by adding safety validation:
   ```python
   # Add after database connection but before clearing tables
   is_safe, issues = validate_etl_safety_preconditions(cursor, self)
   if not is_safe:
       self.log("🚨 ETL SAFETY ISSUES - ABORTING", "ERROR")
       return False
   ```

3. **Replace practice time backup** in backup_user_data_and_team_mappings():
   ```python
   # Replace existing practice time backup with:
   practice_backup_count = create_enhanced_practice_time_backup(cursor, self)
   ```

4. **Enhance restoration** in restore_user_data_with_team_mappings():
   ```python
   # Add team ID preservation validation
   preservation_success, stats = validate_team_id_preservation_post_etl(cursor, self)
   
   if not preservation_success:
       # Use fallback restoration
       restore_practice_times_with_fallback(cursor, self, dry_run=False)
   ```

5. **Add health validation** at the end of run():
   ```python
   # Before final success message
   health_stats = validate_practice_time_health(cursor, pre_etl_count, self)
   if not health_stats["is_healthy"]:
       self.log("🚨 CRITICAL: Practice time health check failed!", "ERROR")
       return False
   ```

6. **Add cleanup** after successful ETL:
   ```python
   cleanup_enhanced_backup_tables(cursor, self)
   ```

This integration provides:
✅ Pre-ETL safety validation
✅ Enhanced backup with metadata  
✅ Team ID preservation detection
✅ Robust fallback restoration
✅ Post-ETL health validation
✅ Automatic cleanup
"""

if __name__ == "__main__":
    print(INTEGRATION_INSTRUCTIONS) 