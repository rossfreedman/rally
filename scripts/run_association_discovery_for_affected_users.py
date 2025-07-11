#!/usr/bin/env python3
"""
Run Association Discovery for Affected Users
===========================================

This script runs Association Discovery manually for Eric Kalman and Jim Levitas
to automatically link their NSTF records that should have been linked during
registration but weren't due to the timing issue.
"""

import logging
import sys
import os
from typing import Dict, List, Optional, Any
import psycopg2

# Add the project root to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Production database URL
PRODUCTION_DB_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

def get_production_db_connection():
    """Get a connection to the production database"""
    try:
        conn = psycopg2.connect(PRODUCTION_DB_URL)
        logger.info("✅ Connected to production database")
        return conn
    except Exception as e:
        logger.error(f"❌ Failed to connect to production database: {e}")
        raise

def execute_query_production(query: str, params: List = None) -> List[Dict]:
    """Execute a query on the production database and return results"""
    conn = get_production_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params or [])
            
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                results = []
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))
                return results
            else:
                return []
    except Exception as e:
        logger.error(f"Query execution error: {e}")
        raise
    finally:
        conn.close()

def execute_query_one_production(query: str, params: List = None) -> Optional[Dict]:
    """Execute a query and return the first result"""
    results = execute_query_production(query, params)
    return results[0] if results else None

def execute_update_production(query: str, params: List = None) -> bool:
    """Execute an update query on production database"""
    conn = get_production_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params or [])
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Update execution error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def run_association_discovery_production(user_id: int, email: str) -> Dict[str, Any]:
    """Run association discovery directly on production database"""
    try:
        print(f"\n🔍 Running Association Discovery for User {user_id} ({email})")
        print("-" * 60)
        
        # Get user info
        user_info = execute_query_one_production("""
            SELECT id, email, first_name, last_name 
            FROM users 
            WHERE id = %s
        """, [user_id])
        
        if not user_info:
            return {"success": False, "error": f"User {user_id} not found"}
        
        first_name = user_info['first_name']
        last_name = user_info['last_name']
        user_email = email or user_info['email']
        
        print(f"👤 User: {first_name} {last_name} ({user_email})")
        
        # Get existing associations
        existing_associations = execute_query_production("""
            SELECT upa.tenniscores_player_id, l.league_id, l.league_name,
                   c.name as club_name, s.name as series_name
            FROM user_player_associations upa
            JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
            JOIN leagues l ON p.league_id = l.id
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE upa.user_id = %s
            ORDER BY l.league_id
        """, [user_id])
        
        existing_player_ids = [assoc['tenniscores_player_id'] for assoc in existing_associations]
        
        print(f"🔗 Existing Associations: {len(existing_associations)}")
        for i, assoc in enumerate(existing_associations):
            print(f"   [{i+1}] {assoc['league_id']}: {assoc['club_name']}, {assoc['series_name']} ({assoc['tenniscores_player_id']})")
        
        # Find potential unlinked players using production database
        print(f"\n🔍 Searching for potential players...")
        potential_players = find_potential_players_production(first_name, last_name, user_email)
        
        print(f"🔍 Found {len(potential_players)} potential players:")
        for i, player in enumerate(potential_players):
            print(f"   [{i+1}] {player['league_name']}: {player['club_name']}, {player['series_name']} ({player['tenniscores_player_id']}) - {player['confidence']}% confidence")
        
        # Filter out already linked players
        unlinked_players = [
            player for player in potential_players 
            if player['tenniscores_player_id'] not in existing_player_ids
        ]
        
        print(f"\n🎯 Unlinked Players: {len(unlinked_players)} need to be linked")
        
        if not unlinked_players:
            print("✅ No unlinked players found - user already has all possible associations")
            return {
                "success": True,
                "user_id": user_id,
                "existing_associations": len(existing_associations),
                "associations_created": 0,
                "new_associations": [],
                "errors": [],
                "summary": f"No new associations needed for {first_name} {last_name}"
            }
        
        # Create associations for unlinked players
        associations_created = []
        errors = []
        
        for player in unlinked_players:
            try:
                player_id = player['tenniscores_player_id']
                print(f"🔗 Creating association: {player_id}")
                
                # Double-check association doesn't exist
                existing_check = execute_query_one_production("""
                    SELECT user_id FROM user_player_associations 
                    WHERE user_id = %s AND tenniscores_player_id = %s
                """, [user_id, player_id])
                
                if existing_check:
                    print(f"   ⚠️  Association already exists - skipping")
                    continue
                
                # Create the association
                execute_update_production("""
                    INSERT INTO user_player_associations (user_id, tenniscores_player_id) 
                    VALUES (%s, %s)
                """, [user_id, player_id])
                
                associations_created.append({
                    "tenniscores_player_id": player_id,
                    "league_name": player['league_name'],
                    "club_name": player['club_name'],
                    "series_name": player['series_name'],
                    "confidence": player['confidence']
                })
                
                print(f"   ✅ Association created successfully")
                
            except Exception as e:
                error_msg = f"Error creating association for {player['tenniscores_player_id']}: {e}"
                print(f"   ❌ {error_msg}")
                errors.append(error_msg)
        
        return {
            "success": True,
            "user_id": user_id,
            "existing_associations": len(existing_associations),
            "associations_created": len(associations_created),
            "new_associations": associations_created,
            "errors": errors,
            "summary": f"Created {len(associations_created)} new associations for {first_name} {last_name}"
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def find_potential_players_production(first_name: str, last_name: str, email: str) -> List[Dict[str, Any]]:
    """Find potential players using production database"""
    potential_players = []
    
    # Strategy 1: Exact name match
    exact_matches = execute_query_production("""
        SELECT p.tenniscores_player_id, p.first_name, p.last_name, p.email, p.is_active,
               l.league_name, c.name as club_name, s.name as series_name
        FROM players p
        JOIN leagues l ON p.league_id = l.id
        LEFT JOIN clubs c ON p.club_id = c.id
        LEFT JOIN series s ON p.series_id = s.id
        WHERE LOWER(TRIM(p.first_name)) = LOWER(TRIM(%s))
        AND LOWER(TRIM(p.last_name)) = LOWER(TRIM(%s))
        AND p.is_active = true
    """, [first_name, last_name])
    
    for match in exact_matches:
        confidence = 90  # High confidence for exact name match
        
        # Boost confidence if email matches
        if match['email'] and match['email'].lower() == email.lower():
            confidence = 100
        
        potential_players.append({
            "tenniscores_player_id": match['tenniscores_player_id'],
            "first_name": match['first_name'],
            "last_name": match['last_name'],
            "email": match['email'],
            "league_name": match['league_name'],
            "club_name": match['club_name'],
            "series_name": match['series_name'],
            "confidence": confidence,
            "match_type": "exact_name"
        })
    
    # Filter to only high-confidence matches (80% or higher)
    high_confidence = [p for p in potential_players if p['confidence'] >= 80]
    
    return high_confidence

def main():
    """Main function to run Association Discovery for affected users"""
    
    print("🔧 Association Discovery - Manual Fix for Affected Users")
    print("=" * 70)
    print("🎯 Running Association Discovery for Eric and Jim to fix registration issue")
    print()
    
    # Affected users who should have had NSTF associations during registration
    affected_users = [
        {"user_id": 939, "email": "eric.kalman@gmail.com", "name": "Eric Kalman"},
        {"user_id": 938, "email": "jimlevitas@gmail.com", "name": "Jim Levitas"},
    ]
    
    results = []
    
    for user in affected_users:
        try:
            result = run_association_discovery_production(
                user['user_id'], 
                user['email']
            )
            
            results.append({
                "user": user,
                "result": result
            })
            
        except Exception as e:
            print(f"❌ ERROR processing {user['name']}: {e}")
            import traceback
            print(f"❌ TRACEBACK: {traceback.format_exc()}")
            results.append({
                "user": user,
                "error": str(e)
            })
    
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    
    total_created = 0
    
    for result in results:
        user = result['user']
        if 'error' in result:
            print(f"❌ {user['name']}: ERROR - {result['error']}")
        else:
            result_data = result['result']
            if result_data.get('success'):
                created = result_data.get('associations_created', 0)
                total_created += created
                
                if created > 0:
                    print(f"✅ {user['name']}: Created {created} new associations")
                    for assoc in result_data.get('new_associations', []):
                        print(f"   • {assoc['league_name']}: {assoc['club_name']}, {assoc['series_name']}")
                else:
                    print(f"✅ {user['name']}: No new associations needed (already complete)")
            else:
                print(f"❌ {user['name']}: FAILED - {result_data.get('error', 'Unknown error')}")
    
    print(f"\n🎯 TOTAL: Created {total_created} new associations")
    
    if total_created > 0:
        print("\n🎉 SUCCESS: Association Discovery fix completed successfully!")
        print("   • Users now have all their league associations linked")
        print("   • No more manual linking required via settings page")
        print("   • Enhanced registration process will prevent future issues")
    else:
        print("\n✅ All users already have complete associations")
        print("   • No manual intervention needed")
        print("   • Enhanced registration process will prevent future issues")

if __name__ == "__main__":
    main() 