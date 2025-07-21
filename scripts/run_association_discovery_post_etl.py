#!/usr/bin/env python3
"""
Post-ETL Association Discovery Script
===================================

This script runs comprehensive association discovery after ETL imports.
It can handle users with incomplete registration data more thoroughly
than the limited discovery run during ETL.

Usage:
    python scripts/run_association_discovery_post_etl.py
    python scripts/run_association_discovery_post_etl.py --limit 200
    python scripts/run_association_discovery_post_etl.py --all
    python scripts/run_association_discovery_post_etl.py --user-email user@example.com
"""

import argparse
import logging
import sys
import os
from datetime import datetime

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from app.services.association_discovery_service import AssociationDiscoveryService

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f'logs/association_discovery_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )

def run_discovery_for_single_user(email: str):
    """Run discovery for a single user by email"""
    print(f"🔍 Running association discovery for user: {email}")
    
    from database_utils import execute_query_one
    
    # Get user info
    user_info = execute_query_one("""
        SELECT id, email, first_name, last_name 
        FROM users 
        WHERE email = %s
    """, [email])
    
    if not user_info:
        print(f"❌ User not found: {email}")
        return False
    
    # Run discovery
    result = AssociationDiscoveryService.discover_missing_associations(
        user_info['id'], user_info['email']
    )
    
    if result.get("success"):
        associations_created = result.get("associations_created", 0)
        if associations_created > 0:
            print(f"✅ Created {associations_created} associations for {email}")
            for assoc in result.get("new_associations", []):
                print(f"   • {assoc['league_name']} - {assoc['club_name']} ({assoc['series_name']})")
        else:
            print(f"ℹ️  No new associations found for {email}")
        return True
    else:
        print(f"❌ Discovery failed for {email}: {result.get('error', 'Unknown error')}")
        return False

def run_batch_discovery(limit: int):
    """Run discovery for a batch of users"""
    print(f"🔍 Running association discovery for up to {limit} users...")
    print("=" * 60)
    
    start_time = datetime.now()
    
    # Run discovery
    result = AssociationDiscoveryService.discover_for_all_users(limit=limit)
    
    # Print results
    print("\n📊 DISCOVERY RESULTS")
    print("=" * 60)
    print(f"Users processed: {result.get('users_processed', 0)}")
    print(f"Users with new associations: {result.get('users_with_new_associations', 0)}")
    print(f"Total associations created: {result.get('total_associations_created', 0)}")
    print(f"Errors: {len(result.get('errors', []))}")
    
    # Show successful associations
    if result.get('details'):
        print("\n✅ SUCCESSFUL ASSOCIATIONS:")
        for detail in result['details']:
            print(f"   • {detail['name']} ({detail['email']}): {detail['new_associations']} associations")
    
    # Show first 5 errors if any
    errors = result.get('errors', [])
    if errors:
        print(f"\n⚠️  ERRORS (showing first 5 of {len(errors)}):")
        for i, error in enumerate(errors[:5]):
            print(f"   {i+1}. {error}")
        if len(errors) > 5:
            print(f"   ... and {len(errors) - 5} more errors")
    
    duration = datetime.now() - start_time
    print(f"\n⏱️  Completed in {duration.total_seconds():.1f} seconds")
    
    return result.get('total_associations_created', 0) > 0

def main():
    parser = argparse.ArgumentParser(description='Run association discovery after ETL')
    parser.add_argument('--limit', type=int, default=100, 
                       help='Maximum number of users to process (default: 100)')
    parser.add_argument('--all', action='store_true',
                       help='Process all users (no limit)')
    parser.add_argument('--user-email', type=str,
                       help='Run discovery for a specific user email')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    print("🚀 POST-ETL ASSOCIATION DISCOVERY")
    print("=" * 60)
    print(f"Started at: {datetime.now()}")
    print("=" * 60)
    
    try:
        if args.user_email:
            # Single user mode
            success = run_discovery_for_single_user(args.user_email)
            return 0 if success else 1
        else:
            # Batch mode
            limit = None if args.all else args.limit
            if limit is None:
                print("🔄 Processing ALL users (this may take a while)...")
                limit = 10000  # Large number to process all
            
            success = run_batch_discovery(limit)
            
            if success:
                print("\n🎉 Association discovery completed successfully!")
                print("💡 Users with new associations should now have proper league contexts")
                return 0
            else:
                print("\n⚠️  Association discovery completed with some issues")
                print("💡 Check logs for details on failed matches")
                return 0  # Not a failure - just no associations found
                
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {str(e)}")
        logging.error(f"Association discovery failed: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 