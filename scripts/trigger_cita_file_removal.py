#!/usr/bin/env python3
"""
Trigger CITA File Removal on Production
======================================

Makes an HTTP request to trigger CITA file removal on production Railway deployment.
"""

import requests
import json
import sys
import getpass
from datetime import datetime

def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")

def trigger_cita_removal(dry_run=False, base_url="https://rally-production.up.railway.app"):
    """Trigger CITA file removal via HTTP request to admin endpoint"""
    
    log("🔍 CITA File Removal Trigger")
    log("=" * 50)
    
    if dry_run:
        log("🔄 DRY RUN MODE: Triggering file removal analysis")
    else:
        log("🚀 LIVE MODE: Triggering actual file removal")
    
    # Get admin credentials
    print("\n🔐 Admin login required:")
    email = input("Email: ")
    password = getpass.getpass("Password: ")
    
    session = requests.Session()
    
    try:
        # Login first
        log("🔑 Logging in to admin panel...")
        login_data = {
            "email": email,
            "password": password
        }
        
        login_response = session.post(f"{base_url}/api/login", json=login_data)
        login_response.raise_for_status()
        
        login_result = login_response.json()
        if not login_result.get("success"):
            log(f"❌ Login failed: {login_result.get('message', 'Unknown error')}", "ERROR")
            return False
        
        log("✅ Successfully logged in")
        
        # Trigger CITA file removal
        log("🗑️ Triggering CITA file removal...")
        removal_data = {
            "dry_run": dry_run
        }
        
        removal_response = session.post(f"{base_url}/api/admin/remove-cita-files", json=removal_data)
        removal_response.raise_for_status()
        
        result = removal_response.json()
        
        # Process results
        if result.get("success"):
            log("✅ CITA file removal completed successfully")
            log(f"📊 Results:")
            log(f"  - Dry run: {result.get('dry_run')}")
            log(f"  - Files removed: {len(result.get('removed_files', []))}")
            log(f"  - Directories removed: {len(result.get('removed_dirs', []))}")
            
            if result.get('removed_files'):
                log("📄 Files removed:")
                for file_path in result['removed_files']:
                    log(f"  - {file_path}")
            
            if result.get('removed_dirs'):
                log("📂 Directories removed:")
                for dir_path in result['removed_dirs']:
                    log(f"  - {dir_path}")
        else:
            log("❌ CITA file removal failed", "ERROR")
            log(f"Error: {result.get('error', 'Unknown error')}")
        
        return result.get("success", False)
        
    except requests.exceptions.RequestException as e:
        log(f"❌ HTTP request failed: {e}", "ERROR")
        return False
    except Exception as e:
        log(f"❌ Unexpected error: {e}", "ERROR")
        return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Trigger CITA file removal on production')
    parser.add_argument('--dry-run', action='store_true', help='Trigger dry-run analysis')
    args = parser.parse_args()
    
    success = trigger_cita_removal(dry_run=args.dry_run)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
