#!/usr/bin/env python3
"""
Clear match_scores table on staging
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Get database URL from Railway environment
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    print("🔗 Connecting to staging database...")
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    cursor = conn.cursor()
    
    # Check current count
    cursor.execute('SELECT COUNT(*) as count FROM match_scores')
    count = cursor.fetchone()['count']
    print(f'📊 Current match_scores count: {count:,}')
    
    # Clear the table
    if count > 0:
        print('🧹 Clearing match_scores table...')
        cursor.execute('DELETE FROM match_scores')
        conn.commit()
        
        # Verify it's cleared
        cursor.execute('SELECT COUNT(*) as count FROM match_scores')
        new_count = cursor.fetchone()['count']
        print(f'✅ Match scores cleared. New count: {new_count}')
    else:
        print('ℹ️  Table already empty')
    
    conn.close()
else:
    print('❌ DATABASE_URL not found')
