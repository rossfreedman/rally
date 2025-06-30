#!/usr/bin/env python3
"""
Add Schema Fixes to ETL Script

This patches the ETL script to automatically fix schema issues
"""

import os
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
etl_file = os.path.join(project_root, "data", "etl", "database_import", "import_all_jsons_to_database.py")

# Schema fix code to add
schema_fix_code = '''
    def ensure_schema_requirements(self, conn):
        """Ensure required schema elements exist before import"""
        cursor = conn.cursor()
        
        try:
            # Create system_settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    id SERIAL PRIMARY KEY,
                    key VARCHAR(255) UNIQUE NOT NULL,
                    value TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Initialize session_version
            cursor.execute("""
                INSERT INTO system_settings (key, value, description) 
                VALUES ('session_version', '5', 'Current session version for cache busting')
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """)
            
            # Add logo_filename column to clubs
            cursor.execute("""
                ALTER TABLE clubs 
                ADD COLUMN IF NOT EXISTS logo_filename VARCHAR(255)
            """)
            
            conn.commit()
            self.log("✅ Schema requirements ensured")
            
        except Exception as e:
            self.log(f"⚠️ Schema fix error (non-critical): {e}", "WARNING")
'''

def main():
    print("🔧 Adding schema fixes to ETL script...")
    
    try:
        # Read the current ETL file
        with open(etl_file, 'r') as f:
            content = f.read()
        
        # Check if schema fix already exists
        if "ensure_schema_requirements" in content:
            print("✅ Schema fixes already present in ETL script")
            return
        
        # Add the schema fix method to the ComprehensiveETL class
        class_pattern = "class ComprehensiveETL:"
        if class_pattern in content:
            # Find a good place to insert - after __init__ method
            init_end = content.find("def log(self, message: str, level: str = \"INFO\"):")
            if init_end != -1:
                # Insert before the log method
                content = content[:init_end] + schema_fix_code + "\n\n    " + content[init_end:]
                
                # Also add call to ensure_schema_requirements in the run method
                run_method_start = content.find("def run(self):")
                if run_method_start != -1:
                    # Find where to insert the call - after database connection
                    with_get_db = content.find("with get_db() as conn:", run_method_start)
                    if with_get_db != -1:
                        try_block = content.find("try:", with_get_db)
                        if try_block != -1:
                            # Find end of try: line
                            line_end = content.find("\n", try_block)
                            schema_call = "\n                    # Ensure schema requirements\n                    self.ensure_schema_requirements(conn)\n"
                            content = content[:line_end] + schema_call + content[line_end:]
                
                # Write the modified content back
                with open(etl_file, 'w') as f:
                    f.write(content)
                
                print("✅ Schema fixes added to ETL script")
                print("🔄 Next ETL run will automatically fix schema issues")
                return True
            
    except Exception as e:
        print(f"❌ Error modifying ETL script: {e}")
        return False

if __name__ == "__main__":
    main() 