#!/usr/bin/env python3
"""
Check User-Player Associations on Railway

Usage:
    python scripts/check_user_associations_railway.py --email vforman@gmail.com
    python scripts/check_user_associations_railway.py --user-id 49
"""
import sys
import os
import argparse

# Add the parent directory to Python path to import from rally
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force Railway DB if needed
os.environ['RAILWAY_ENVIRONMENT'] = 'true'

# Check if we have Railway DATABASE_URL
railway_db_url = os.environ.get('DATABASE_PUBLIC_URL') or os.environ.get('DATABASE_URL')
if railway_db_url and 'railway' in railway_db_url.lower():
    print(f"🚂 Connecting to Railway database")
    os.environ['DATABASE_URL'] = railway_db_url
else:
    print("⚠️  Warning: No Railway DATABASE_URL found. Make sure to set DATABASE_URL or DATABASE_PUBLIC_URL")
    print("   Current DATABASE_URL:", os.environ.get('DATABASE_URL', 'Not set'))

from database_utils import execute_query_one, execute_query

def main():
    parser = argparse.ArgumentParser(description="Check user-player associations on Railway")
    parser.add_argument("--email", type=str, help="User email")
    parser.add_argument("--user-id", type=int, help="User ID")
    args = parser.parse_args()

    if not args.email and not args.user_id:
        print("You must provide either --email or --user-id")
        sys.exit(1)

    # 1. Get user info
    if args.user_id:
        user = execute_query_one("SELECT id, email, first_name, last_name FROM users WHERE id = %s", [args.user_id])
    else:
        user = execute_query_one("SELECT id, email, first_name, last_name FROM users WHERE email = %s", [args.email])

    if not user:
        print("❌ User not found.")
        sys.exit(1)

    print(f"👤 User: {user['first_name']} {user['last_name']} (ID: {user['id']}, Email: {user['email']})")

    # 2. Get all associations
    associations = execute_query("""
        SELECT upa.tenniscores_player_id, l.league_name, p.first_name, p.last_name, p.is_active, t.team_name
        FROM user_player_associations upa
        JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
        JOIN leagues l ON p.league_id = l.id
        LEFT JOIN teams t ON p.team_id = t.id
        WHERE upa.user_id = %s
        ORDER BY l.league_name
    """, [user['id']])

    if not associations:
        print("❌ No player associations found for this user.")
        sys.exit(0)

    print("\n🏆 Player Associations:")
    for assoc in associations:
        status = "✅ ACTIVE" if assoc['is_active'] else "❌ INACTIVE"
        print(f"  - {assoc['league_name']}: {assoc['first_name']} {assoc['last_name']} ({assoc['tenniscores_player_id']}) - {status}")
        if assoc['team_name']:
            print(f"      Team: {assoc['team_name']}")

if __name__ == "__main__":
    main() 