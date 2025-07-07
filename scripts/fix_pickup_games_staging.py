#!/usr/bin/env python3

"""
Fix pickup games tables on staging if they're missing
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one, execute_update

def fix_pickup_games_staging():
    """Fix pickup games tables on staging"""
    
    print("=== Fixing Pickup Games Tables on Staging ===")
    
    # Check if we're on staging
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
    if railway_env != "staging":
        print(f"❌ This script only runs on staging. Current environment: {railway_env}")
        return False
    
    try:
        # Check if pickup_games table exists
        table_check = execute_query_one("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'pickup_games'
            )
        """)
        
        pickup_games_exists = table_check["exists"] if table_check else False
        print(f"pickup_games table exists: {pickup_games_exists}")
        
        # Check if pickup_game_participants table exists
        participants_check = execute_query_one("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'pickup_game_participants'
            )
        """)
        
        participants_exists = participants_check["exists"] if participants_check else False
        print(f"pickup_game_participants table exists: {participants_exists}")
        
        if pickup_games_exists and participants_exists:
            print("✅ Both tables already exist - no fix needed")
            return True
        
        # Create pickup_games table if missing
        if not pickup_games_exists:
            print("📝 Creating pickup_games table...")
            
            create_pickup_games_sql = """
                CREATE TABLE pickup_games (
                    id SERIAL PRIMARY KEY,
                    description TEXT NOT NULL,
                    game_date DATE NOT NULL,
                    game_time TIME NOT NULL,
                    players_requested INTEGER NOT NULL CHECK (players_requested > 0),
                    players_committed INTEGER DEFAULT 0,
                    pti_low DECIMAL(5,2) DEFAULT -30,
                    pti_high DECIMAL(5,2) DEFAULT 100,
                    series_low INTEGER REFERENCES series(id),
                    series_high INTEGER REFERENCES series(id), 
                    club_only BOOLEAN DEFAULT FALSE,
                    creator_user_id INTEGER NOT NULL REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """
            
            execute_update(create_pickup_games_sql, [])
            print("✅ pickup_games table created")
        
        # Create pickup_game_participants table if missing
        if not participants_exists:
            print("📝 Creating pickup_game_participants table...")
            
            create_participants_sql = """
                CREATE TABLE pickup_game_participants (
                    id SERIAL PRIMARY KEY,
                    pickup_game_id INTEGER NOT NULL REFERENCES pickup_games(id) ON DELETE CASCADE,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(pickup_game_id, user_id)
                );
            """
            
            execute_update(create_participants_sql, [])
            print("✅ pickup_game_participants table created")
        
        # Verify tables were created successfully
        final_check = execute_query_one("""
            SELECT 
                (SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'pickup_games')) as pg_exists,
                (SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'pickup_game_participants')) as pgp_exists
        """)
        
        if final_check and final_check["pg_exists"] and final_check["pgp_exists"]:
            print("✅ All pickup games tables successfully created/verified")
            print("🎯 The pickup games page should now work on staging")
            return True
        else:
            print("❌ Failed to create tables properly")
            return False
        
    except Exception as e:
        print(f"❌ Error fixing pickup games tables: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = fix_pickup_games_staging()
    if success:
        print("\n🎉 Pickup games fix completed successfully!")
        print("👉 Visit https://rally-staging.up.railway.app/mobile/pickup-games to test")
    else:
        print("\n💥 Fix failed - check the error messages above") 