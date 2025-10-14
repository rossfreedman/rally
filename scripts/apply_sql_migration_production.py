#!/usr/bin/env python3
"""
Apply SQL Migration Directly to Production
===========================================

This script applies the food and videos table changes directly to production.
"""

import psycopg2

def main():
    print("=" * 70)
    print("🚀 Applying Database Changes to PRODUCTION")
    print("=" * 70)
    print()
    print("⚠️  WARNING: This will modify the PRODUCTION database!")
    print()
    
    # Confirm execution
    response = input("🔄 Apply changes to PRODUCTION database? [y/N]: ").strip().lower()
    if response not in ['y', 'yes']:
        print("❌ Migration cancelled")
        return False
    
    # Double confirmation for production
    response2 = input("⚠️  Are you ABSOLUTELY SURE? Type 'PRODUCTION' to confirm: ").strip()
    if response2 != 'PRODUCTION':
        print("❌ Migration cancelled - confirmation failed")
        return False
    
    try:
        # Connect to production
        print("🔌 Connecting to production database...")
        conn = psycopg2.connect('postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway')
        conn.autocommit = False
        cur = conn.cursor()
        
        print("✅ Connected successfully to PRODUCTION")
        print()
        
        # ============================================================================
        # STEP 1: Update Food Table
        # ============================================================================
        print("📊 Step 1: Updating food table...")
        
        # Add mens_food and womens_food columns
        cur.execute("""
            ALTER TABLE food 
            ADD COLUMN IF NOT EXISTS mens_food TEXT,
            ADD COLUMN IF NOT EXISTS womens_food TEXT;
        """)
        
        # Make food_text nullable
        cur.execute("""
            ALTER TABLE food 
            ALTER COLUMN food_text DROP NOT NULL;
        """)
        
        # Migrate existing data
        cur.execute("""
            UPDATE food 
            SET mens_food = food_text 
            WHERE mens_food IS NULL AND food_text IS NOT NULL;
        """)
        
        print("   ✅ Food table updated")
        print()
        
        # ============================================================================
        # STEP 2: Create Videos Table
        # ============================================================================
        print("🎥 Step 2: Creating videos table...")
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                url TEXT NOT NULL,
                players TEXT,
                date DATE,
                team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        
        # Add indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_videos_team_id ON videos(team_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_videos_date ON videos(date DESC);")
        
        print("   ✅ Videos table created")
        print()
        
        # ============================================================================
        # STEP 3: Update Alembic Version
        # ============================================================================
        print("📋 Step 3: Updating alembic version...")
        
        cur.execute("UPDATE alembic_version SET version_num = '20251012_food_videos';")
        
        print("   ✅ Alembic version updated")
        print()
        
        # ============================================================================
        # STEP 4: Verify Changes
        # ============================================================================
        print("🔍 Step 4: Verifying changes...")
        print()
        
        # Check food columns
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name='food' 
            AND column_name IN ('mens_food', 'womens_food', 'food_text') 
            ORDER BY column_name
        """)
        cols = cur.fetchall()
        print("   Food table columns:")
        for col_name, data_type, is_nullable in cols:
            print(f"      - {col_name}: {data_type} (nullable: {is_nullable})")
        print()
        
        # Check videos table
        cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'videos')")
        videos_exists = cur.fetchone()[0]
        print(f"   Videos table exists: {videos_exists}")
        
        if videos_exists:
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='videos' 
                ORDER BY ordinal_position
            """)
            vcols = cur.fetchall()
            print(f"   Videos table has {len(vcols)} columns")
        print()
        
        # Check alembic version
        cur.execute("SELECT version_num FROM alembic_version")
        version = cur.fetchone()[0]
        print(f"   Alembic version: {version}")
        print()
        
        # Commit all changes
        conn.commit()
        print("✅ All changes committed to PRODUCTION database")
        
        cur.close()
        conn.close()
        
        return True
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print()
    success = main()
    print()
    
    if success:
        print("=" * 70)
        print("✅ SUCCESS - All database changes applied to PRODUCTION!")
        print("=" * 70)
        print()
        print("📝 Summary:")
        print("   ✅ Food table: Added mens_food and womens_food columns")
        print("   ✅ Food table: Made food_text nullable")
        print("   ✅ Food table: Migrated existing data to mens_food")
        print("   ✅ Videos table: Created with all columns and indexes")
        print("   ✅ Alembic version: Updated to 20251012_food_videos")
        print()
        print("🎯 Next Steps:")
        print("   1. Test food notifications on production")
        print("   2. Test team videos feature")
        print("   3. Monitor for any issues")
        print()
    else:
        print("=" * 70)
        print("❌ FAILED - Migration did not complete")
        print("=" * 70)

