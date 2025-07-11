#!/usr/bin/env python3
"""
Check User Registration Dates
============================

This script checks when Eric, Jim, and Gregg registered to see if they registered
before or after the Association Discovery system was added on June 26, 2025.
"""

import logging
import sys
import os
from typing import Dict, List, Optional, Any
import psycopg2
from datetime import datetime
import pytz

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

def check_user_registration_dates():
    """Check when the test users registered"""
    
    print("🕐 Checking User Registration Dates")
    print("=" * 60)
    
    # Association Discovery was added on June 26, 2025 (make timezone-aware)
    central_tz = pytz.timezone('America/Chicago')
    association_discovery_date = central_tz.localize(datetime(2025, 6, 26, 8, 26, 2))
    print(f"📅 Association Discovery System Added: {association_discovery_date}")
    print()
    
    # Get user registration dates
    users = execute_query_production("""
        SELECT id, email, first_name, last_name, created_at
        FROM users
        WHERE id IN (938, 939, 944)
        ORDER BY created_at
    """)
    
    print(f"👥 User Registration Information:")
    print("-" * 60)
    
    for user in users:
        user_id = user['id']
        email = user['email']
        name = f"{user['first_name']} {user['last_name']}"
        created_at = user['created_at']
        
        # Convert to timezone-aware if needed
        if created_at.tzinfo is None:
            created_at = pytz.utc.localize(created_at)
        
        # Compare with association discovery date
        if created_at < association_discovery_date:
            timing = "⏰ BEFORE Association Discovery"
            explanation = "Registration predates Association Discovery system"
        else:
            timing = "🕐 AFTER Association Discovery"
            explanation = "Should have had Association Discovery during registration"
        
        print(f"User {user_id}: {name} ({email})")
        print(f"  Registered: {created_at}")
        print(f"  Timing: {timing}")
        print(f"  Explanation: {explanation}")
        print()
    
    # Check their current associations
    print(f"🔗 Current Association Status:")
    print("-" * 60)
    
    for user in users:
        user_id = user['id']
        name = f"{user['first_name']} {user['last_name']}"
        
        associations = execute_query_production("""
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
        
        print(f"User {user_id}: {name}")
        print(f"  Associations: {len(associations)}")
        for i, assoc in enumerate(associations):
            print(f"    [{i+1}] {assoc['league_id']}: {assoc['club_name']}, {assoc['series_name']}")
        print()
    
    # Summary
    print("📊 ANALYSIS:")
    print("-" * 60)
    
    users_before = [u for u in users if u['created_at'] < association_discovery_date]
    users_after = [u for u in users if u['created_at'] >= association_discovery_date]
    
    print(f"Users registered BEFORE Association Discovery: {len(users_before)}")
    for user in users_before:
        print(f"  • {user['first_name']} {user['last_name']} ({user['created_at']})")
    
    print(f"\nUsers registered AFTER Association Discovery: {len(users_after)}")
    for user in users_after:
        print(f"  • {user['first_name']} {user['last_name']} ({user['created_at']})")
    
    print(f"\n🔍 CONCLUSION:")
    if users_before:
        print("Users who registered BEFORE Association Discovery system:")
        print("  → This explains why they had to manually link their NSTF records")
        print("  → Association Discovery wasn't available during their registration")
        print("  → They got their APTA association through normal registration")
        print("  → They had to manually link NSTF via settings page")
    
    if users_after:
        print("Users who registered AFTER Association Discovery system:")
        print("  → These users should have had automatic association discovery")
        print("  → If they still had issues, there might be a bug in the system")

if __name__ == "__main__":
    check_user_registration_dates() 