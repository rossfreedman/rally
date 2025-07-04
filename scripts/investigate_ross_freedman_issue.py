#!/usr/bin/env python3
"""
Investigation script for Ross Freedman login association issue

This script investigates why Ross Freedman gets different league associations
between local/staging vs production environments.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one, execute_update
from app.services.association_discovery_service import AssociationDiscoveryService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def investigate_ross_freedman_data():
    """Investigate what player data exists for Ross Freedman"""
    print("🔍 INVESTIGATING ROSS FREEDMAN LOGIN ASSOCIATION ISSUE")
    print("=" * 60)
    
    # Test cases to check
    test_cases = [
        {"first_name": "Ross", "last_name": "Freedman"},
        {"first_name": "ross", "last_name": "freedman"},  # lowercase version
        {"first_name": "Ross", "last_name": "freedman"},  # mixed case
    ]
    
    for i, case in enumerate(test_cases, 1):
        first_name = case["first_name"]
        last_name = case["last_name"]
        
        print(f"\n{i}. CHECKING: {first_name} {last_name}")
        print("-" * 40)
        
        # Check exact matches
        exact_matches = execute_query("""
            SELECT p.tenniscores_player_id, p.first_name, p.last_name, p.email,
                   c.name as club_name, s.name as series_name, l.league_name,
                   p.is_active, p.team_id
            FROM players p
            JOIN leagues l ON p.league_id = l.id
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE LOWER(TRIM(p.first_name)) = LOWER(TRIM(%s))
            AND LOWER(TRIM(p.last_name)) = LOWER(TRIM(%s))
            ORDER BY l.league_name, c.name, s.name
        """, [first_name, last_name])
        
        if exact_matches:
            print(f"   ✅ Found {len(exact_matches)} exact matches:")
            for match in exact_matches:
                status = "ACTIVE" if match['is_active'] else "INACTIVE"
                email = match['email'] or "NO EMAIL"
                print(f"      - {match['first_name']} {match['last_name']} ({status})")
                print(f"        League: {match['league_name']}")
                print(f"        Club: {match['club_name'] or 'NO CLUB'}")
                print(f"        Series: {match['series_name'] or 'NO SERIES'}")
                print(f"        Email: {email}")
                print(f"        Player ID: {match['tenniscores_player_id']}")
                print(f"        Team ID: {match['team_id']}")
                print()
        else:
            print("   ❌ No exact matches found")
            
        # Check case-insensitive partial matches
        partial_matches = execute_query("""
            SELECT p.tenniscores_player_id, p.first_name, p.last_name, p.email,
                   c.name as club_name, s.name as series_name, l.league_name,
                   p.is_active
            FROM players p
            JOIN leagues l ON p.league_id = l.id
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE (LOWER(TRIM(p.first_name)) LIKE LOWER(TRIM(%s)) 
                   OR LOWER(TRIM(p.last_name)) LIKE LOWER(TRIM(%s)))
            ORDER BY l.league_name, c.name, s.name
        """, [f"%{first_name}%", f"%{last_name}%"])
        
        if partial_matches:
            print(f"   📋 Found {len(partial_matches)} partial matches:")
            for match in partial_matches[:10]:  # Limit to first 10
                status = "ACTIVE" if match['is_active'] else "INACTIVE"
                print(f"      - {match['first_name']} {match['last_name']} ({status})")
                print(f"        League: {match['league_name']}, Club: {match['club_name'] or 'NO CLUB'}")
        
    # Check what leagues exist in the database
    print(f"\n4. AVAILABLE LEAGUES IN DATABASE:")
    print("-" * 40)
    leagues = execute_query("""
        SELECT id, league_id, league_name, 
               (SELECT COUNT(*) FROM players p WHERE p.league_id = l.id AND p.is_active = true) as active_player_count
        FROM leagues l
        ORDER BY league_name
    """)
    
    for league in leagues:
        print(f"   - {league['league_name']} (ID: {league['league_id']}, DB_ID: {league['id']}, Players: {league['active_player_count']})")

def test_association_discovery():
    """Test the association discovery service for a specific user"""
    print(f"\n5. TESTING ASSOCIATION DISCOVERY")
    print("-" * 40)
    
    # Check if user exists
    user_emails = [
        "ross@glenbrookracquetclub.com",
        "rossfreedman@gmail.com", 
        "ross.freedman@gmail.com",
        "rossfreedman@glenbrookracquetclub.com"
    ]
    
    # Also check what email addresses exist in the players table for Ross Freedman
    print("   Checking email addresses in players table for Ross Freedman...")
    email_matches = execute_query("""
        SELECT DISTINCT p.email, p.first_name, p.last_name, l.league_name,
               c.name as club_name, s.name as series_name
        FROM players p
        JOIN leagues l ON p.league_id = l.id
        LEFT JOIN clubs c ON p.club_id = c.id
        LEFT JOIN series s ON p.series_id = s.id
        WHERE (LOWER(TRIM(p.first_name)) LIKE '%ross%' 
               AND LOWER(TRIM(p.last_name)) LIKE '%freedman%')
        AND p.email IS NOT NULL
        ORDER BY l.league_name
    """)
    
    if email_matches:
        print(f"   Found {len(email_matches)} players with emails:")
        for match in email_matches:
            print(f"     - {match['first_name']} {match['last_name']}: {match['email']}")
            print(f"       League: {match['league_name']}, Club: {match['club_name']}")
    else:
        print("   No email addresses found for Ross Freedman in players table")
    
    for email in user_emails:
        user_record = execute_query_one("""
            SELECT id, email, first_name, last_name, league_context
            FROM users 
            WHERE LOWER(email) = LOWER(%s)
        """, [email])
        
        if user_record:
            print(f"   ✅ Found user: {user_record['first_name']} {user_record['last_name']} ({email})")
            print(f"      User ID: {user_record['id']}")
            print(f"      League Context: {user_record['league_context']}")
            
            # Check existing associations
            associations = execute_query("""
                SELECT upa.tenniscores_player_id,
                       p.first_name, p.last_name, 
                       c.name as club_name, s.name as series_name, l.league_name
                FROM user_player_associations upa
                JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                JOIN leagues l ON p.league_id = l.id
                LEFT JOIN clubs c ON p.club_id = c.id
                LEFT JOIN series s ON p.series_id = s.id
                WHERE upa.user_id = %s
                ORDER BY l.league_name
            """, [user_record['id']])
            
            print(f"      Current associations: {len(associations)}")
            for assoc in associations:
                print(f"        - {assoc['league_name']}: {assoc['first_name']} {assoc['last_name']} ({assoc['club_name']}, {assoc['series_name']})")
            
            # Test discovery service
            print(f"      Running association discovery...")
            discovery_result = AssociationDiscoveryService.discover_missing_associations(
                user_record['id'], email
            )
            
            if discovery_result.get("success"):
                print(f"      Discovery result: {discovery_result['summary']}")
                if discovery_result.get("associations_created", 0) > 0:
                    print(f"      New associations found:")
                    for new_assoc in discovery_result.get("new_associations", []):
                        print(f"        + {new_assoc['league_name']}: {new_assoc['tenniscores_player_id']} (confidence: {new_assoc['confidence']}%)")
                else:
                    print(f"      No new associations needed")
            else:
                print(f"      Discovery failed: {discovery_result.get('error', 'Unknown error')}")
                
            return user_record['id']
        else:
            print(f"   ❌ User not found: {email}")
    
    return None

def check_name_variations():
    """Check what name variations are supported"""
    print(f"\n6. CHECKING NAME VARIATION SUPPORT")
    print("-" * 40)
    
    # Import the name variations
    from utils.database_player_lookup import get_name_variations
    from app.services.association_discovery_service import AssociationDiscoveryService
    
    test_names = ["Ross", "ross", "Rob", "Robert", "Bob"]
    
    for name in test_names:
        variations = get_name_variations(name)
        print(f"   {name} -> {variations}")
    
    # Test the association discovery name variations
    try:
        # Note: _get_name_variations is a private method, but we can access it for testing
        assoc_variations = AssociationDiscoveryService._get_name_variations("Ross")
        print(f"   Association service 'Ross' -> {assoc_variations}")
        
        # Also test variations for common names
        rob_variations = AssociationDiscoveryService._get_name_variations("Rob")
        print(f"   Association service 'Rob' -> {rob_variations}")
        
        robert_variations = AssociationDiscoveryService._get_name_variations("Robert")
        print(f"   Association service 'Robert' -> {robert_variations}")
    except Exception as e:
        print(f"   Association service name variations failed: {e}")

def main():
    """Main investigation function"""
    print("Starting Ross Freedman investigation...\n")
    
    try:
        investigate_ross_freedman_data()
        user_id = test_association_discovery()
        check_name_variations()
        
        print(f"\n✅ INVESTIGATION COMPLETE")
        print("=" * 60)
        print("SUMMARY:")
        print("- Check the player records found above")
        print("- Compare with production environment data")
        print("- Look for differences in league coverage or data quality")
        print("- Check if association discovery is finding the right matches")
        
        if user_id:
            print(f"- User ID {user_id} can be used for further testing")
            
    except Exception as e:
        print(f"❌ Investigation failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    main() 