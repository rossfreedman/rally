#!/usr/bin/env python3
"""Check players table schema"""

import psycopg2
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db_url
import re

def check_players_schema(db_type):
    """Check players table schema"""
    if db_type == 'railway':
        os.environ['SYNC_RAILWAY'] = 'true'
    else:
        os.environ.pop('SYNC_RAILWAY', None)
    
    url = get_db_url()
    pattern = r'postgresql://([^:]+):([^@]+)@([^/]+)/(.+)'
    match = re.match(pattern, url)
    user, password, host_port, database = match.groups()
    host, port = host_port.split(':')

    conn = psycopg2.connect(
        host=host, port=port, database=database, 
        user=user, password=password, sslmode='prefer'
    )

    cursor = conn.cursor()

    print(f"🔍 {db_type.upper()} PLAYERS TABLE SCHEMA")
    print("=" * 50)

    # Get column details
    cursor.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_name = 'players'
        ORDER BY ordinal_position
    """)
    
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col[0]}: {col[1]} ({'NULL' if col[2] == 'YES' else 'NOT NULL'}) {col[3] or ''}")
    
    # Check if phone column exists
    phone_exists = any(col[0] == 'phone' for col in columns)
    print(f"\n📞 phone column exists: {phone_exists}")
    
    conn.close()
    return phone_exists

if __name__ == "__main__":
    print("Checking both local and Railway players table schemas...\n")
    
    local_phone = check_players_schema('local')
    print()
    railway_phone = check_players_schema('railway')
    
    print(f"\n📊 SUMMARY:")
    print(f"Local has phone column: {local_phone}")
    print(f"Railway has phone column: {railway_phone}")
    
    if local_phone != railway_phone:
        print(f"⚠️  SCHEMA MISMATCH: Phone column exists in {'local' if local_phone else 'railway'} but not {'railway' if local_phone else 'local'}")
    else:
        print(f"✅ Schema is consistent between databases") 