#!/usr/bin/env python3

"""
Re-associate All Users After Database Import
===========================================

This script fixes user-player associations that get broken after database imports.
It uses the AssociationDiscoveryService to find and re-create missing associations
for all users in the system.

Usage:
    python scripts/re_associate_all_users.py [--dry-run] [--specific-user EMAIL]
"""

import sys
import os
import argparse
from datetime import datetime

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.association_discovery_service import AssociationDiscoveryService
from database_utils import execute_query, execute_update


def check_association_system_health():
    """Check the current state of the association system"""
    print("🏥 CHECKING ASSOCIATION SYSTEM HEALTH")
    print("=" * 50)
    
    # Check total users
    users = execute_query("SELECT COUNT(*) as count FROM users")
    user_count = users[0]['count'] if users else 0
    print(f"👥 Total users in system: {user_count:,}")
    
    # Check total players
    players = execute_query("SELECT COUNT(*) as count FROM players WHERE is_active = true")
    player_count = players[0]['count'] if players else 0
    print(f"🎾 Total active players: {player_count:,}")
    
    # Check current associations
    associations = execute_query("SELECT COUNT(*) as count FROM user_player_associations")
    assoc_count = associations[0]['count'] if associations else 0
    print(f"🔗 Current associations: {assoc_count:,}")
    
    # Check users without associations
    users_without_assoc = execute_query("""
        SELECT COUNT(*) as count
        FROM users u
        LEFT JOIN user_player_associations upa ON u.id = upa.user_id
        WHERE upa.user_id IS NULL
    """)
    unassociated_count = users_without_assoc[0]['count'] if users_without_assoc else 0
    print(f"❌ Users without associations: {unassociated_count:,}")
    
    # Check users with minimal associations (0-1)
    users_minimal = execute_query("""
        SELECT COUNT(*) as count
        FROM (
            SELECT u.id, COUNT(upa.tenniscores_player_id) as assoc_count
            FROM users u
            LEFT JOIN user_player_associations upa ON u.id = upa.user_id
            GROUP BY u.id
            HAVING COUNT(upa.tenniscores_player_id) <= 1
        ) minimal
    """)
    minimal_count = users_minimal[0]['count'] if users_minimal else 0
    print(f"⚠️  Users with ≤1 associations: {minimal_count:,}")
    
    # Calculate health score
    health_score = ((user_count - unassociated_count) / max(user_count, 1)) * 100
    print(f"\n💊 HEALTH SCORE: {health_score:.1f}%")
    
    if health_score < 50:
        print("🚨 CRITICAL: System health is below 50% - immediate re-association needed")
    elif health_score < 80:
        print("⚠️  WARNING: System health is below 80% - re-association recommended")
    else:
        print("✅ GOOD: System health is above 80%")
    
    return {
        "user_count": user_count,
        "player_count": player_count,
        "assoc_count": assoc_count,
        "unassociated_count": unassociated_count,
        "minimal_count": minimal_count,
        "health_score": health_score
    }


def clear_broken_associations(dry_run=False):
    """Clear any broken associations (associations pointing to non-existent players)"""
    print("\n🧹 CHECKING FOR BROKEN ASSOCIATIONS")
    print("=" * 50)
    
    # Find associations pointing to non-existent players
    broken_associations = execute_query("""
        SELECT upa.user_id, upa.tenniscores_player_id, u.email, u.first_name, u.last_name
        FROM user_player_associations upa
        JOIN users u ON upa.user_id = u.id
        LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
        WHERE p.tenniscores_player_id IS NULL
    """)
    
    if broken_associations:
        print(f"🔍 Found {len(broken_associations)} broken associations:")
        for assoc in broken_associations:
            print(f"   - {assoc['first_name']} {assoc['last_name']} ({assoc['email']}) → {assoc['tenniscores_player_id']}")
        
        if not dry_run:
            print("🗑️  Removing broken associations...")
            for assoc in broken_associations:
                execute_update("""
                    DELETE FROM user_player_associations 
                    WHERE user_id = %s AND tenniscores_player_id = %s
                """, [assoc['user_id'], assoc['tenniscores_player_id']])
            print(f"✅ Removed {len(broken_associations)} broken associations")
        else:
            print("[DRY RUN] Would remove broken associations")
    else:
        print("✅ No broken associations found")
    
    return len(broken_associations)


def re_associate_all_users(dry_run=False, specific_user_email=None):
    """Re-associate all users using the discovery service"""
    print(f"\n🔗 RE-ASSOCIATING {'SPECIFIC USER' if specific_user_email else 'ALL USERS'}")
    print("=" * 50)
    
    if specific_user_email:
        # Process specific user
        user_query = execute_query("""
            SELECT id, email, first_name, last_name
            FROM users
            WHERE LOWER(email) = LOWER(%s)
        """, [specific_user_email])
        
        if not user_query:
            print(f"❌ User not found: {specific_user_email}")
            return {"users_processed": 0, "errors": ["User not found"]}
        
        users_to_process = user_query
        print(f"🎯 Processing user: {user_query[0]['first_name']} {user_query[0]['last_name']} ({user_query[0]['email']})")
    
    else:
        # Get all users
        users_to_process = execute_query("""
            SELECT id, email, first_name, last_name
            FROM users
            WHERE first_name IS NOT NULL 
            AND last_name IS NOT NULL
            ORDER BY created_at DESC
        """)
        print(f"🎯 Processing {len(users_to_process)} users")
    
    if dry_run:
        print("[DRY RUN] Would run association discovery for users")
        return {"users_processed": len(users_to_process), "dry_run": True}
    
    # Process users in batches
    batch_size = 50
    total_processed = 0
    total_with_new_associations = 0
    total_associations_created = 0
    all_errors = []
    details = []
    
    for i in range(0, len(users_to_process), batch_size):
        batch = users_to_process[i:i + batch_size]
        print(f"\n📦 Processing batch {i//batch_size + 1} ({len(batch)} users)...")
        
        for user in batch:
            try:
                # Run discovery for this user
                result = AssociationDiscoveryService.discover_missing_associations(
                    user['id'], user['email']
                )
                
                total_processed += 1
                
                if result.get("success"):
                    associations_created = result.get("associations_created", 0)
                    if associations_created > 0:
                        total_with_new_associations += 1
                        total_associations_created += associations_created
                        
                        print(f"   ✅ {user['first_name']} {user['last_name']}: +{associations_created} associations")
                        
                        details.append({
                            "user_id": user['id'],
                            "email": user['email'],
                            "name": f"{user['first_name']} {user['last_name']}",
                            "new_associations": associations_created,
                            "associations_details": result.get("new_associations", [])
                        })
                    else:
                        print(f"   ℹ️  {user['first_name']} {user['last_name']}: No new associations needed")
                        
                    # Log any errors from the discovery
                    if result.get("errors"):
                        all_errors.extend([f"User {user['id']}: {error}" for error in result["errors"]])
                
                else:
                    error_msg = f"User {user['id']}: {result.get('error', 'Unknown error')}"
                    all_errors.append(error_msg)
                    print(f"   ❌ {user['first_name']} {user['last_name']}: {result.get('error', 'Unknown error')}")
                
            except Exception as e:
                error_msg = f"User {user['id']}: {str(e)}"
                all_errors.append(error_msg)
                print(f"   💥 {user['first_name']} {user['last_name']}: {str(e)}")
        
        # Progress update
        print(f"   📊 Batch complete: {total_with_new_associations}/{total_processed} users gained associations")
    
    return {
        "users_processed": total_processed,
        "users_with_new_associations": total_with_new_associations,
        "total_associations_created": total_associations_created,
        "errors": all_errors,
        "details": details
    }


def main():
    parser = argparse.ArgumentParser(description="Re-associate all users after database import")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be done without making changes")
    parser.add_argument("--specific-user", type=str,
                       help="Process only this specific user (by email)")
    parser.add_argument("--skip-health-check", action="store_true",
                       help="Skip the initial health check")
    
    args = parser.parse_args()
    
    print("🔗 RALLY USER RE-ASSOCIATION SYSTEM")
    print("=" * 50)
    print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if args.dry_run:
        print("🚫 DRY RUN MODE - No changes will be made")
    
    try:
        # Step 1: Health check
        if not args.skip_health_check:
            health_data = check_association_system_health()
            
            if health_data["health_score"] > 90 and not args.specific_user:
                print("\n✅ System health is excellent (>90%). Re-association may not be needed.")
                response = input("Continue anyway? (y/N): ")
                if response.lower() != 'y':
                    print("Exiting.")
                    return
        
        # Step 2: Clear broken associations
        broken_count = clear_broken_associations(dry_run=args.dry_run)
        
        # Step 3: Re-associate users
        results = re_associate_all_users(
            dry_run=args.dry_run, 
            specific_user_email=args.specific_user
        )
        
        # Step 4: Final summary
        print("\n" + "=" * 50)
        print("📊 FINAL RESULTS")
        print("=" * 50)
        
        if results.get("dry_run"):
            print("🚫 DRY RUN COMPLETED - No actual changes made")
        else:
            print(f"👥 Users processed: {results['users_processed']}")
            print(f"✅ Users with new associations: {results['users_with_new_associations']}")
            print(f"🔗 Total associations created: {results['total_associations_created']}")
            print(f"🗑️  Broken associations removed: {broken_count}")
            
            if results['details']:
                print(f"\n🎯 SUCCESS STORIES ({len(results['details'])} users):")
                for detail in results['details'][:10]:  # Show first 10
                    print(f"   ✅ {detail['name']} ({detail['email']})")
                    print(f"      Added {detail['new_associations']} associations:")
                    for assoc in detail['associations_details']:
                        print(f"        - {assoc['league_name']}: {assoc['club_name']} / {assoc['series_name']}")
                
                if len(results['details']) > 10:
                    print(f"   ... and {len(results['details']) - 10} more users")
            
            if results['errors']:
                print(f"\n⚠️  ERRORS ({len(results['errors'])} total):")
                for error in results['errors'][:5]:  # Show first 5 errors
                    print(f"   - {error}")
                if len(results['errors']) > 5:
                    print(f"   ... and {len(results['errors']) - 5} more errors")
            
            # Calculate impact
            if results['users_processed'] > 0:
                success_rate = (results['users_with_new_associations'] / results['users_processed']) * 100
                print(f"\n🎯 SUCCESS RATE: {success_rate:.1f}% of users gained new associations")
                
                if results['total_associations_created'] > 0:
                    print(f"🚀 IMPACT: Fixed {results['total_associations_created']} missing league connections!")
                    print("✅ Users should now be able to access all their league teams properly")
                else:
                    print("ℹ️  No missing associations found - system was already healthy")
        
        # Step 5: Final health check
        if not args.dry_run and not args.skip_health_check:
            print("\n" + "=" * 50)
            print("🏥 POST-PROCESSING HEALTH CHECK")
            print("=" * 50)
            final_health = check_association_system_health()
            
            if final_health["health_score"] > health_data.get("health_score", 0):
                improvement = final_health["health_score"] - health_data.get("health_score", 0)
                print(f"📈 IMPROVEMENT: +{improvement:.1f}% health score")
            
        print(f"\n🏁 Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 