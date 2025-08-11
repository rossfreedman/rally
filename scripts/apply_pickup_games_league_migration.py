#!/usr/bin/env python3
"""
Apply league_id column migration to pickup_games table
Designed to work with Railway environment variables
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

def apply_migration():
    """Apply the league_id column migration to pickup_games table"""
    print('🔧 Adding league_id column to pickup_games table...')
    
    # Get database connection details from environment
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        print('❌ DATABASE_URL environment variable not found')
        return False
    
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # Add league_id column to pickup_games table
        print('📝 Adding league_id column...')
        cursor.execute('''
            ALTER TABLE pickup_games 
            ADD COLUMN IF NOT EXISTS league_id INTEGER REFERENCES leagues(id) ON DELETE SET NULL
        ''')
        
        # Create index for performance
        print('📝 Creating index on league_id...')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_pickup_games_league_id ON pickup_games(league_id)
        ''')
        
        conn.commit()
        print('✅ Successfully added league_id column and index to pickup_games table')
        
        # Verify the column was added
        cursor.execute('''
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'pickup_games' AND column_name = 'league_id'
        ''')
        
        result = cursor.fetchone()
        if result:
            print(f'✅ Verified: league_id column exists with type {result["data_type"]}')
            
            # Check current pickup games count
            cursor.execute('SELECT COUNT(*) FROM pickup_games')
            count = cursor.fetchone()[0]
            print(f'📊 Current pickup games count: {count}')
            
            if count > 0:
                # Show sample of existing games
                cursor.execute('''
                    SELECT id, description, club_id, league_id 
                    FROM pickup_games 
                    ORDER BY created_at DESC 
                    LIMIT 3
                ''')
                
                games = cursor.fetchall()
                print('📋 Sample pickup games:')
                for game in games:
                    league_status = 'ALL LEAGUES' if game['league_id'] is None else f'League {game["league_id"]}'
                    club_status = 'ALL CLUBS' if game['club_id'] is None else f'Club {game["club_id"]}'
                    print(f'  - ID: {game["id"]}, "{game["description"][:30]}...", {club_status}, {league_status}')
            else:
                print('💡 No pickup games currently exist')
                
            cursor.close()
            conn.close()
            return True
        else:
            print('❌ Column not found after creation')
            cursor.close()
            conn.close()
            return False
            
    except Exception as e:
        print(f'❌ Error: {e}')
        return False

if __name__ == "__main__":
    success = apply_migration()
    sys.exit(0 if success else 1)
