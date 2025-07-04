#!/usr/bin/env python3
"""
Production Data Comparison Script for Ross Freedman Issue

This script helps compare what data exists between local and production environments
for the Ross Freedman login association issue.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def production_debugging_queries():
    """
    Generate SQL queries that can be run on production to debug the Ross Freedman issue
    """
    print("🔍 PRODUCTION DEBUGGING QUERIES FOR ROSS FREEDMAN")
    print("=" * 60)
    print("Run these queries on PRODUCTION to compare with local data:\n")
    
    queries = [
        {
            "title": "1. Check Ross Freedman Player Records",
            "query": """
-- Check all Ross Freedman player records in production
SELECT p.tenniscores_player_id, p.first_name, p.last_name, p.email,
       c.name as club_name, s.name as series_name, l.league_name,
       p.is_active, p.team_id, p.created_at
FROM players p
JOIN leagues l ON p.league_id = l.id
LEFT JOIN clubs c ON p.club_id = c.id
LEFT JOIN series s ON p.series_id = s.id
WHERE LOWER(TRIM(p.first_name)) = 'ross'
AND LOWER(TRIM(p.last_name)) = 'freedman'
ORDER BY l.league_name, p.created_at;
            """,
            "expected_local": "2 records: APTA Chicago + NSTF"
        },
        {
            "title": "2. Check User Account",
            "query": """
-- Check Ross Freedman user account
SELECT id, email, first_name, last_name, league_context, last_login, created_at
FROM users 
WHERE LOWER(email) LIKE '%rossfreedman%' 
   OR LOWER(email) LIKE '%ross.freedman%'
   OR LOWER(email) LIKE '%ross@%'
ORDER BY created_at;
            """,
            "expected_local": "User: rossfreedman@gmail.com, league_context: 4687"
        },
        {
            "title": "3. Check Current Associations",
            "query": """
-- Check current user-player associations for Ross
SELECT u.email, u.first_name, u.last_name,
       upa.tenniscores_player_id,
       p.first_name as player_first, p.last_name as player_last,
       c.name as club_name, s.name as series_name, l.league_name
FROM users u
JOIN user_player_associations upa ON u.id = upa.user_id
JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
JOIN leagues l ON p.league_id = l.id
LEFT JOIN clubs c ON p.club_id = c.id
LEFT JOIN series s ON p.series_id = s.id
WHERE LOWER(u.email) LIKE '%rossfreedman%'
   OR (LOWER(u.first_name) = 'ross' AND LOWER(u.last_name) = 'freedman')
ORDER BY l.league_name;
            """,
            "expected_local": "2 associations: APTA Chicago + NSTF"
        },
        {
            "title": "4. Check League Coverage",
            "query": """
-- Check what leagues exist in production
SELECT id, league_id, league_name, 
       (SELECT COUNT(*) FROM players p WHERE p.league_id = l.id AND p.is_active = true) as active_player_count
FROM leagues l
ORDER BY league_name;
            """,
            "expected_local": "4 leagues: APTA Chicago (6836), CITA (0), CNSWPL (2654), NSTF (808)"
        },
        {
            "title": "5. Check Email Matching Potential",
            "query": """
-- Check if any Ross Freedman records have email addresses
SELECT p.email, p.first_name, p.last_name, l.league_name,
       c.name as club_name, s.name as series_name
FROM players p
JOIN leagues l ON p.league_id = l.id
LEFT JOIN clubs c ON p.club_id = c.id
LEFT JOIN series s ON p.series_id = s.id
WHERE (LOWER(TRIM(p.first_name)) LIKE '%ross%' 
       AND LOWER(TRIM(p.last_name)) LIKE '%freedman%')
AND p.email IS NOT NULL
ORDER BY l.league_name;
            """,
            "expected_local": "No results - no email addresses found"
        },
        {
            "title": "6. Test Association Discovery Logic",
            "query": """
-- Simulate what association discovery would find for Ross Freedman
-- Strategy 1: Exact name match
SELECT 'exact_name' as strategy, p.tenniscores_player_id, p.first_name, p.last_name, 
       l.league_name, c.name as club_name, s.name as series_name
FROM players p
JOIN leagues l ON p.league_id = l.id
LEFT JOIN clubs c ON p.club_id = c.id
LEFT JOIN series s ON p.series_id = s.id
WHERE LOWER(TRIM(p.first_name)) = 'ross'
AND LOWER(TRIM(p.last_name)) = 'freedman'
AND p.is_active = true

UNION ALL

-- Strategy 2: Email match (if email provided)
SELECT 'email_match' as strategy, p.tenniscores_player_id, p.first_name, p.last_name,
       l.league_name, c.name as club_name, s.name as series_name
FROM players p
JOIN leagues l ON p.league_id = l.id
LEFT JOIN clubs c ON p.club_id = c.id
LEFT JOIN series s ON p.series_id = s.id
WHERE LOWER(TRIM(p.email)) = 'rossfreedman@gmail.com'
AND p.is_active = true

UNION ALL

-- Strategy 3: Name variations (Rob, Robert, Bob for Ross - currently none)
SELECT 'name_variation' as strategy, p.tenniscores_player_id, p.first_name, p.last_name,
       l.league_name, c.name as club_name, s.name as series_name
FROM players p
JOIN leagues l ON p.league_id = l.id
LEFT JOIN clubs c ON p.club_id = c.id
LEFT JOIN series s ON p.series_id = s.id
WHERE LOWER(TRIM(p.first_name)) IN ('rob', 'robert', 'bob')  -- No variations for Ross currently
AND LOWER(TRIM(p.last_name)) = 'freedman'
AND p.is_active = true

ORDER BY strategy, league_name;
            """,
            "expected_local": "2 exact matches, 0 email matches, 0 name variations"
        }
    ]
    
    for i, query_info in enumerate(queries, 1):
        print(f"{'='*60}")
        print(f"{query_info['title']}")
        print(f"{'='*60}")
        print(f"Expected from local: {query_info['expected_local']}")
        print(f"\nSQL Query:")
        print(query_info['query'])
        print("\n")

def analyze_potential_fixes():
    """Analyze potential fixes for the Ross association issue"""
    print("🔧 POTENTIAL FIXES FOR ROSS FREEDMAN ASSOCIATION ISSUE")
    print("=" * 60)
    
    fixes = [
        {
            "issue": "Missing Name Variations for 'Ross'",
            "description": "The association discovery service doesn't recognize 'Ross' as having nickname variations",
            "fix": "Add 'Ross' name variations to the AssociationDiscoveryService._get_name_variations method",
            "code": """
# In app/services/association_discovery_service.py, add to name_variations_map:
"ross": ["rob", "robert"],  # If Ross is a nickname for Robert
"robert": ["rob", "bob", "bobby", "ross"],  # Add ross as Robert variation
            """,
            "risk": "Low - only affects name matching"
        },
        {
            "issue": "Missing Email Addresses in Player Records",
            "description": "Ross Freedman player records have no email addresses, preventing email-based matching",
            "fix": "Update player records with correct email addresses if available",
            "code": """
-- Update player records with email (if known)
UPDATE players 
SET email = 'rossfreedman@gmail.com' 
WHERE tenniscores_player_id IN ('nndz-WkMrK3didjlnUT09', 'nndz-WlNhd3hMYi9nQT09');
            """,
            "risk": "Medium - requires knowing correct email addresses"
        },
        {
            "issue": "Data Sync Issues Between Environments",
            "description": "Production might be missing player records that exist in local/staging",
            "fix": "Sync missing player data from local to production, or re-run ETL import",
            "code": "Run ETL import to ensure all player data is synchronized",
            "risk": "High - could affect other data"
        },
        {
            "issue": "Case Sensitivity in Login",
            "description": "User types 'ross freedman' (lowercase) but system expects exact case matching",
            "fix": "Ensure all name matching is case-insensitive (already implemented)",
            "code": "Already using LOWER(TRIM(p.first_name)) in queries",
            "risk": "None - already implemented"
        }
    ]
    
    for i, fix in enumerate(fixes, 1):
        print(f"{i}. {fix['issue']}")
        print(f"   Description: {fix['description']}")
        print(f"   Fix: {fix['fix']}")
        print(f"   Risk Level: {fix['risk']}")
        if 'code' in fix:
            print(f"   Code:")
            print(f"   {fix['code']}")
        print()

def test_local_association_discovery():
    """Test association discovery with the known user"""
    print("🧪 TESTING LOCAL ASSOCIATION DISCOVERY")
    print("=" * 60)
    
    try:
        from app.services.association_discovery_service import AssociationDiscoveryService
        
        # Test with the known user
        result = AssociationDiscoveryService.discover_missing_associations(43, "rossfreedman@gmail.com")
        
        print("Test Results:")
        print(f"  Success: {result.get('success')}")
        print(f"  Existing associations: {result.get('existing_associations')}")
        print(f"  New associations created: {result.get('associations_created')}")
        print(f"  Summary: {result.get('summary')}")
        
        if result.get('new_associations'):
            print("  New associations details:")
            for assoc in result['new_associations']:
                print(f"    - {assoc['league_name']}: {assoc['tenniscores_player_id']} (confidence: {assoc['confidence']}%)")
        
        # Test the potential player finding logic directly
        print("\nTesting _find_potential_players directly:")
        potential_players = AssociationDiscoveryService._find_potential_players(
            "Ross", "Freedman", "rossfreedman@gmail.com"
        )
        
        print(f"  Found {len(potential_players)} potential players:")
        for player in potential_players:
            print(f"    - {player['league_name']}: {player['first_name']} {player['last_name']}")
            print(f"      Player ID: {player['tenniscores_player_id']}")
            print(f"      Match Type: {player['match_type']}")
            print(f"      Confidence: {player['confidence']}%")
        
    except Exception as e:
        print(f"Error testing association discovery: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

def main():
    """Main function"""
    print("Ross Freedman Production Debugging Guide\n")
    
    production_debugging_queries()
    analyze_potential_fixes()
    test_local_association_discovery()
    
    print("🎯 NEXT STEPS:")
    print("=" * 60)
    print("1. Run the SQL queries above on PRODUCTION environment")
    print("2. Compare results with local data shown in the queries")
    print("3. Look for missing player records or associations in production")
    print("4. Consider implementing the fixes based on what you find")
    print("5. Test login behavior after any fixes")

if __name__ == "__main__":
    main() 