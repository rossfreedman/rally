#!/usr/bin/env python3
"""
Trigger APTA import on staging environment via web interface.
This script triggers the import process on staging using the admin API.
"""

import requests
import json
import time
import sys
from datetime import datetime

def trigger_staging_import():
    """Trigger the import process on staging via the admin API."""
    
    staging_url = "https://rally-staging.up.railway.app"
    import_endpoint = f"{staging_url}/api/admin/etl/import"
    
    print("🚀 TRIGGERING STAGING IMPORT")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Staging URL: {staging_url}")
    print(f"Import endpoint: {import_endpoint}")
    print()
    
    try:
        # First, check if staging is accessible
        print("📡 Checking staging connectivity...")
        health_response = requests.get(f"{staging_url}/health", timeout=30)
        if health_response.status_code == 200:
            print("✅ Staging is accessible")
        else:
            print(f"⚠️  Staging health check returned {health_response.status_code}")
    except Exception as e:
        print(f"❌ Cannot reach staging: {e}")
        return False
    
    print()
    print("🔧 Triggering import process...")
    print("   Note: This will start the full ETL import process on staging.")
    print("   The process may take several minutes to complete.")
    print()
    
    try:
        # Trigger the import
        response = requests.post(import_endpoint, timeout=30)
        
        if response.status_code == 200:
            print("✅ Import process started successfully!")
            print("   The import is running in the background on staging.")
            print()
            print("📊 Next steps:")
            print("1. Wait 5-10 minutes for the import to complete")
            print("2. Check staging database for any players not in JSON")
            print("3. Remove any unwanted players from staging")
            print("4. Run complete validation to ensure staging matches local")
            return True
        elif response.status_code == 409:
            print("⚠️  Import process is already running on staging")
            print("   Please wait for the current import to complete.")
            return True
        else:
            print(f"❌ Failed to trigger import. Status code: {response.status_code}")
            if response.text:
                print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error triggering import: {e}")
        return False

def main():
    success = trigger_staging_import()
    
    if success:
        print("\n🎉 STAGING IMPORT TRIGGERED!")
        print("=" * 50)
        print("The import process is now running on staging.")
        print("You can monitor the progress by checking the staging logs.")
        print()
        print("Next steps:")
        print("1. Wait for import to complete (5-10 minutes)")
        print("2. Run validation script to check staging database")
        print("3. Clean up any unwanted players if needed")
    else:
        print("\n❌ FAILED TO TRIGGER STAGING IMPORT")
        print("=" * 50)
        print("Please check the error messages above and try again.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
