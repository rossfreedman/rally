#!/usr/bin/env python3
"""Diagnose Railway database and application state"""

import psycopg2
import sys
import os
import subprocess
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db_url
import re

def check_database_content():
    """Check actual data content to see if migrations ran"""
    os.environ['SYNC_RAILWAY'] = 'true'
    
    # Get Railway connection details  
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

    print("🔍 RAILWAY DATABASE CONTENT ANALYSIS")
    print("=" * 60)

    # Check alembic_version table
    cursor.execute("SELECT version_num FROM alembic_version")
    version = cursor.fetchone()
    print(f'📋 alembic_version table: {version[0] if version else "None"}')

    # Check key table row counts that should exist if migrations ran
    tables_to_check = [
        'users', 'players', 'match_scores', 'schedule', 
        'series_stats', 'player_availability', 'player_history'
    ]
    
    print(f'\n📊 TABLE ROW COUNTS:')
    for table in tables_to_check:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f'   {table}: {count:,} rows')
        except Exception as e:
            print(f'   {table}: ❌ Error - {e}')

    # Check if specific schema elements exist that came from migrations
    print(f'\n🔍 SCHEMA VERIFICATION:')
    
    # Check if users table has the clean schema (no deprecated foreign keys)
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name IN ('league_id', 'club_id', 'series_id', 'tenniscores_player_id')
    """)
    deprecated_cols = cursor.fetchall()
    if deprecated_cols:
        print(f'   ❌ users table still has deprecated columns: {[col[0] for col in deprecated_cols]}')
    else:
        print(f'   ✅ users table has clean schema (no deprecated foreign keys)')

    # Check match_scores structure
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'match_scores'
        ORDER BY ordinal_position
    """)
    match_columns = [col[0] for col in cursor.fetchall()]
    print(f'   match_scores columns: {match_columns}')

    conn.close()

def check_railway_deployment():
    """Check Railway deployment status"""
    print(f'\n🚂 RAILWAY DEPLOYMENT STATUS')
    print("=" * 60)
    
    try:
        # Check if railway CLI is available
        result = subprocess.run(['railway', 'status'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(f'✅ Railway CLI Status:')
            print(result.stdout)
        else:
            print(f'❌ Railway CLI Error:')
            print(result.stderr)
            
    except FileNotFoundError:
        print(f'⚠️  Railway CLI not found - install with: npm install -g @railway/cli')
    except subprocess.TimeoutExpired:
        print(f'⏰ Railway CLI timeout - network issues?')
    except Exception as e:
        print(f'❌ Railway CLI error: {e}')

def fix_alembic_version():
    """Fix alembic version table if needed"""
    print(f'\n🛠️  ALEMBIC VERSION FIX')
    print("=" * 60)
    
    os.environ['SYNC_RAILWAY'] = 'true'
    
    # Get Railway connection details  
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

    # Check actual schema state vs what should be there
    cursor.execute("SELECT COUNT(*) FROM match_scores")
    match_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    
    if match_count > 0 and user_count > 0:
        print(f'📊 Data exists (users: {user_count}, matches: {match_count})')
        print(f'🔧 Updating alembic_version to reflect actual state...')
        
        # Update to correct version
        cursor.execute("UPDATE alembic_version SET version_num = '995937af9e55'")
        conn.commit()
        print(f'✅ Updated alembic_version to 995937af9e55')
    else:
        print(f'❌ Data missing - migrations need to run')
        print(f'🔧 Setting alembic_version to allow migration from add_team_polls_001')
    
    conn.close()

if __name__ == "__main__":
    check_database_content()
    check_railway_deployment()
    fix_alembic_version() 