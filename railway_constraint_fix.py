#!/usr/bin/env python3
"""
Direct Railway constraint fix - no environment variables needed
Just deploy this and run it once to fix the database constraints
"""

import os
import sys

# Prevent Flask startup
os.environ['CRON_JOB_MODE'] = 'true'
os.environ['FLASK_APP'] = ''
os.environ['FLASK_ENV'] = 'production'

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("🔧 Railway Database Constraint Fixer - Direct Mode")
print("="*60)

try:
    from scripts.fix_missing_database_constraints import DatabaseConstraintFixer
    
    fixer = DatabaseConstraintFixer()
    success = fixer.fix_all_constraints()
    
    if success:
        print("\n🎉 SUCCESS: Railway database constraints fixed!")
        print("💡 ETL imports should now work properly")
        print("💡 You can now delete this script and run normal ETL")
    else:
        print("\n❌ FAILURE: Some constraints could not be created")
        
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n🏁 Constraint fix script completed")