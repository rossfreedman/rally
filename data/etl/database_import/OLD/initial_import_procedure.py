#!/usr/bin/env python3
"""
Initial Import Procedure for Modernized ETL
===========================================

This script handles the initial migration to the modernized ETL system:

Step 3.1: Clear existing match scores (INITIAL IMPORT ONLY)
Step 3.2: Run the updated import with tenniscores_match_id
Step 3.3: Re-run the import to verify upsert functionality

⚠️ WARNING: This script will DELETE all existing match scores!
Only run this for the initial migration to the modernized ETL system.
"""

import os
import sys
import time

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
sys.path.insert(0, project_root)

from database_config import get_db
from modernized_import_filterable import ModernizedETLImporter


def clear_existing_match_scores():
    """Clear all existing match scores for initial import"""
    print("🗑️  Clearing existing match scores...")
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Count existing records
            cursor.execute("SELECT COUNT(*) FROM match_scores")
            existing_count = cursor.fetchone()[0]
            
            print(f"📊 Found {existing_count:,} existing match score records")
            
            if existing_count == 0:
                print("✅ No existing match scores to clear")
                return True
            
            # Confirm deletion
            print(f"\n⚠️  WARNING: This will DELETE all {existing_count:,} match score records!")
            confirm = input("Are you sure you want to proceed? Type 'DELETE' to confirm: ").strip()
            
            if confirm != 'DELETE':
                print("❌ Operation cancelled")
                return False
            
            # Delete all match scores
            print("🗑️  Deleting all match scores...")
            cursor.execute("DELETE FROM match_scores")
            deleted_count = cursor.rowcount
            conn.commit()
            
            print(f"✅ Deleted {deleted_count:,} match score records")
            
            cursor.close()
            
            return True
        
    except Exception as e:
        print(f"❌ Failed to clear match scores: {str(e)}")
        return False


def run_initial_import():
    """Run the initial import with modernized ETL"""
    print("\n🚀 Running initial import with modernized ETL...")
    
    try:
        # Create importer instance
        importer = ModernizedETLImporter()
        
        # Override user prompts for automated initial import
        print("📋 Using automated configuration for initial import:")
        print("   League: All leagues")
        print("   Series: All series") 
        print("   Data Types: Match scores only")
        
        filters = {
            'league': None,  # All leagues
            'series': None,  # All series
            'data_types': ['match_scores']
        }
        
        # Connect to database
        with get_db() as conn:
            importer.log("✅ Connected to database")
            
            start_time = time.time()
            
            # Load and import match data
            match_data = importer.load_json_data('match_scores')
            if match_data:
                importer.import_match_scores_with_upsert(conn, match_data, filters)
            
            # Final summary
            end_time = time.time()
            duration = end_time - start_time
            
            importer.log(f"\n🎉 Initial Import Complete! ({duration:.1f}s)")
            for data_type, count in importer.imported_counts.items():
                if count > 0:
                    importer.log(f"   {data_type}: {count:,} records")
        
        importer.log("🔌 Database connection closed")
        
        return True
        
    except Exception as e:
        print(f"❌ Initial import failed: {str(e)}")
        return False


def verify_upsert_functionality():
    """Re-run the import to verify upsert functionality"""
    print("\n🔄 Re-running import to verify upsert functionality...")
    
    try:
        # Get current record count
        with get_db() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM match_scores")
            count_before = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM match_scores WHERE tenniscores_match_id IS NOT NULL")
            count_with_match_id = cursor.fetchone()[0]
            
            print(f"📊 Before re-import: {count_before:,} total records, {count_with_match_id:,} with tenniscores_match_id")
            
            cursor.close()
        
        # Run import again
        importer = ModernizedETLImporter()
        
        filters = {
            'league': None,
            'series': None,
            'data_types': ['match_scores']
        }
        
        with get_db() as conn:
            start_time = time.time()
            
            match_data = importer.load_json_data('match_scores')
            if match_data:
                importer.import_match_scores_with_upsert(conn, match_data, filters)
            
            # Check results after re-import
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM match_scores")
            count_after = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM match_scores WHERE tenniscores_match_id IS NOT NULL")
            count_with_match_id_after = cursor.fetchone()[0]
            
            print(f"\n📊 After re-import: {count_after:,} total records, {count_with_match_id_after:,} with tenniscores_match_id")
            
            # Verify no duplicates were created
            if count_before == count_after:
                print("✅ UPSERT SUCCESS: No duplicate records created!")
            else:
                print(f"⚠️  Record count changed: {count_before} → {count_after}")
                print("   This might indicate new records were added or there's an issue with upsert logic")
            
            cursor.close()
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ Upsert verification complete ({duration:.1f}s)")
        
        return count_before == count_after
        
    except Exception as e:
        print(f"❌ Upsert verification failed: {str(e)}")
        return False


def main():
    """Main procedure for initial ETL migration"""
    print("=" * 80)
    print("🚀 INITIAL IMPORT PROCEDURE - MODERNIZED ETL MIGRATION")
    print("=" * 80)
    
    print("\nThis procedure will:")
    print("1. Clear all existing match scores (ONE-TIME ONLY)")
    print("2. Import match data using the new ETL with tenniscores_match_id")
    print("3. Re-run the import to verify upsert functionality")
    
    print(f"\n⚠️  WARNING: This is a ONE-TIME migration procedure!")
    print("⚠️  All existing match scores will be DELETED and re-imported!")
    
    proceed = input("\nProceed with initial migration? (y/N): ").strip().lower()
    if proceed != 'y':
        print("❌ Migration cancelled")
        return
    
    # Step 3.1: Clear existing match scores
    print("\n" + "="*60)
    print("STEP 3.1: CLEAR EXISTING MATCH SCORES")
    print("="*60)
    
    if not clear_existing_match_scores():
        print("❌ Failed to clear existing match scores. Aborting.")
        return
    
    # Step 3.2: Run initial import
    print("\n" + "="*60)
    print("STEP 3.2: RUN INITIAL IMPORT WITH MODERNIZED ETL")
    print("="*60)
    
    if not run_initial_import():
        print("❌ Initial import failed. Check errors above.")
        return
    
    # Step 3.3: Verify upsert functionality
    print("\n" + "="*60)
    print("STEP 3.3: VERIFY UPSERT FUNCTIONALITY")
    print("="*60)
    
    if not verify_upsert_functionality():
        print("⚠️  Upsert verification had issues. Check results above.")
    
    print("\n" + "="*80)
    print("🎉 INITIAL MIGRATION COMPLETE!")
    print("="*80)
    
    print("\n✅ Your Rally ETL system has been successfully modernized!")
    print("\nNext steps:")
    print("• Use: python data/etl/database_import/modernized_import_filterable.py")
    print("• Filter by specific leagues, series, and data types")
    print("• Benefit from incremental upserts instead of full overwrites")
    print("• Rally application continues working exactly as before")


if __name__ == "__main__":
    main() 