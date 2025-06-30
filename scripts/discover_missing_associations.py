#!/usr/bin/env python3

"""
Discover Missing Player Associations

This maintenance script finds and creates missing user-player associations
across the entire user base. It's designed to catch cases like Victor's
where users have player records in multiple leagues but only some are linked.

Usage:
    python scripts/discover_missing_associations.py [--limit N] [--dry-run] [--user-id ID]
"""

import sys
import os
import argparse
from datetime import datetime

# Add the parent directory to Python path to import from rally
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.association_discovery_service import AssociationDiscoveryService

def main():
    parser = argparse.ArgumentParser(description="Discover and create missing player associations")
    parser.add_argument("--limit", type=int, default=100, 
                       help="Maximum number of users to process (default: 100)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be done without making changes")
    parser.add_argument("--user-id", type=int,
                       help="Process only this specific user ID")
    
    args = parser.parse_args()
    
    print("🔍 RALLY ASSOCIATION DISCOVERY")
    print("=" * 50)
    print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if args.dry_run:
        print("🚫 DRY RUN MODE - No changes will be made")
    
    if args.user_id:
        print(f"🎯 Target: Single user (ID: {args.user_id})")
        
        # Process single user
        try:
            if args.dry_run:
                print("   [DRY RUN] Would discover associations for user")
                return
                
            result = AssociationDiscoveryService.discover_missing_associations(args.user_id)
            
            if result.get("success"):
                print(f"✅ User {args.user_id}: {result['summary']}")
                
                if result.get("associations_created", 0) > 0:
                    print("   📋 New associations:")
                    for assoc in result.get("new_associations", []):
                        print(f"      - {assoc['league_name']}: {assoc['tenniscores_player_id']}")
                else:
                    print("   ℹ️  No new associations needed")
                    
                if result.get("errors"):
                    print("   ⚠️  Errors:")
                    for error in result["errors"]:
                        print(f"      - {error}")
            else:
                print(f"❌ User {args.user_id}: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Error processing user {args.user_id}: {e}")
    
    else:
        print(f"🎯 Target: Up to {args.limit} users with missing associations")
        
        # Process multiple users
        try:
            if args.dry_run:
                print("   [DRY RUN] Would discover associations for multiple users")
                return
                
            results = AssociationDiscoveryService.discover_for_all_users(limit=args.limit)
            
            print()
            print("📊 DISCOVERY RESULTS:")
            print(f"   Users processed: {results['users_processed']}")
            print(f"   Users with new associations: {results['users_with_new_associations']}")
            print(f"   Total associations created: {results['total_associations_created']}")
            
            if results['details']:
                print()
                print("📋 USERS WITH NEW ASSOCIATIONS:")
                for detail in results['details']:
                    print(f"   ✅ {detail['name']} ({detail['email']})")
                    print(f"      Added {detail['new_associations']} associations:")
                    for assoc in detail['associations_details']:
                        print(f"        - {assoc['league_name']}: {assoc['tenniscores_player_id']}")
            
            if results['errors']:
                print()
                print("⚠️  ERRORS:")
                for error in results['errors']:
                    print(f"   - {error}")
            
            # Summary
            success_rate = (results['users_with_new_associations'] / max(results['users_processed'], 1)) * 100
            print()
            print(f"🎯 Success Rate: {success_rate:.1f}% of users gained new associations")
            
            if results['total_associations_created'] > 0:
                print(f"🚀 Impact: Fixed {results['total_associations_created']} missing league connections!")
            else:
                print("ℹ️  No missing associations found - all users are properly linked")
                
        except Exception as e:
            print(f"❌ Error during bulk discovery: {e}")
    
    print()
    print(f"🏁 Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main() 