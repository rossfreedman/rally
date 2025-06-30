#!/usr/bin/env python3
"""
Deploy Club Logo Fix to Railway
===============================

This script fixes club logo issues on Railway by ensuring the logos are properly set.
Can be run to push logo fixes from local to Railway.

Usage:
    python scripts/deploy_club_logo_fix.py
"""

import sys
import os

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

def main():
    """Main deployment function"""
    print("🚀 Club Logo Fix Deployment")
    print("=" * 50)
    
    # Step 1: Commit current admin changes
    print("\n1️⃣ Committing current changes...")
    os.system("git add .")
    os.system('git commit -m "Admin impersonation improvements - allow users without player context"')
    
    # Step 2: Push to Railway
    print("\n2️⃣ Deploying to Railway...")
    os.system("git push origin main")
    
    # Step 3: Clone club logo data to Railway
    print("\n3️⃣ Fixing club logos on Railway...")
    print("📋 Running club logo fix on Railway database...")
    
    # Use the existing clone functionality to push logo data
    try:
        from data.etl.clone.clone_local_to_railway_PROD_auto import clone_local_to_railway_auto
        
        # Clone only the clubs table to fix logos
        clone_result = clone_local_to_railway_auto(
            tables_to_clone=['clubs'],
            verify_differences=True,
            skip_confirmation=False
        )
        
        if clone_result:
            print("✅ Club logos successfully updated on Railway!")
        else:
            print("❌ Failed to update club logos on Railway")
            
    except Exception as e:
        print(f"❌ Error during logo fix: {e}")
        print("\n🔧 Manual fix needed:")
        print("   1. SSH into Railway")
        print("   2. Run: python scripts/fix_club_logos.py")
        return False
    
    print("\n🎉 Deployment complete!")
    print("🔍 Test the logo switching at: https://www.lovetorally.com/mobile")
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1) 