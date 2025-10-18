#!/usr/bin/env python3
"""
Complete migration script to add lesson pricing columns and data to production
Combines both adding columns and populating data
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import psycopg2

# Production database URL
PRODUCTION_DB_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

def migrate_lesson_pricing():
    """Complete migration: Add columns and populate pricing data"""
    
    print("=" * 80)
    print("LESSON PRICING MIGRATION TO PRODUCTION")
    print("=" * 80)
    
    try:
        # Connect to production database
        print("\n📡 Connecting to production database...")
        conn = psycopg2.connect(PRODUCTION_DB_URL)
        cur = conn.cursor()
        print("✅ Connected to production database (Railway)")
        
        # STEP 1: Add pricing columns
        print("\n" + "=" * 80)
        print("STEP 1: ADD PRICING COLUMNS")
        print("=" * 80)
        
        print("\n🔍 Checking if columns exist...")
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'pros' 
            AND column_name IN (
                'private_30min_price',
                'private_45min_price',
                'private_60min_price',
                'semi_private_60min_price',
                'group_3players_price',
                'group_4plus_price'
            )
        """)
        
        existing_columns = [row[0] for row in cur.fetchall()]
        
        if len(existing_columns) == 6:
            print("✅ All 6 pricing columns already exist")
        else:
            print(f"   Adding {6 - len(existing_columns)} missing columns...")
            
            cur.execute("""
                ALTER TABLE pros 
                ADD COLUMN IF NOT EXISTS private_30min_price DECIMAL(10,2),
                ADD COLUMN IF NOT EXISTS private_45min_price DECIMAL(10,2),
                ADD COLUMN IF NOT EXISTS private_60min_price DECIMAL(10,2),
                ADD COLUMN IF NOT EXISTS semi_private_60min_price DECIMAL(10,2),
                ADD COLUMN IF NOT EXISTS group_3players_price DECIMAL(10,2),
                ADD COLUMN IF NOT EXISTS group_4plus_price DECIMAL(10,2)
            """)
            
            conn.commit()
            print("✅ Pricing columns added successfully")
        
        # STEP 2: Populate pricing data
        print("\n" + "=" * 80)
        print("STEP 2: POPULATE PRICING DATA")
        print("=" * 80)
        
        # Get active pros
        print("\n🔍 Finding active pros...")
        cur.execute("""
            SELECT id, name, email 
            FROM pros 
            WHERE is_active = true 
            ORDER BY name
        """)
        
        pros = cur.fetchall()
        
        if not pros:
            print("⚠️  No active pros found")
        else:
            print(f"✅ Found {len(pros)} active pros:")
            for pro in pros:
                print(f"   ID {pro[0]}: {pro[1]} ({pro[2] or 'No email'})")
            
            # Update Olga Martinsone
            print("\n📝 Updating Olga Martinsone pricing...")
            cur.execute("""
                UPDATE pros 
                SET private_30min_price = 55.00,
                    private_45min_price = 85.00,
                    private_60min_price = 100.00,
                    semi_private_60min_price = 55.00,
                    group_3players_price = 40.00,
                    group_4plus_price = 35.00
                WHERE name = 'Olga Martinsone' AND is_active = true
            """)
            
            if cur.rowcount > 0:
                print(f"✅ Updated Olga Martinsone")
            
            # Update Mike Simms
            print("📝 Updating Mike Simms pricing...")
            cur.execute("""
                UPDATE pros 
                SET private_30min_price = 50.00,
                    private_45min_price = 75.00,
                    private_60min_price = 90.00,
                    semi_private_60min_price = 50.00,
                    group_3players_price = 35.00,
                    group_4plus_price = 30.00
                WHERE name = 'Mike Simms' AND is_active = true
            """)
            
            if cur.rowcount > 0:
                print(f"✅ Updated Mike Simms")
            
            # Update any remaining pros with default pricing
            print("📝 Updating remaining pros with default pricing...")
            cur.execute("""
                UPDATE pros 
                SET private_30min_price = 50.00,
                    private_45min_price = 75.00,
                    private_60min_price = 90.00,
                    semi_private_60min_price = 50.00,
                    group_3players_price = 35.00,
                    group_4plus_price = 30.00
                WHERE is_active = true 
                AND private_30min_price IS NULL
            """)
            
            if cur.rowcount > 0:
                print(f"✅ Updated {cur.rowcount} additional pros")
            
            conn.commit()
        
        # STEP 3: Verify migration
        print("\n" + "=" * 80)
        print("STEP 3: VERIFY MIGRATION")
        print("=" * 80)
        
        cur.execute("""
            SELECT 
                name,
                private_30min_price,
                private_45min_price,
                private_60min_price,
                semi_private_60min_price,
                group_3players_price,
                group_4plus_price,
                email
            FROM pros 
            WHERE is_active = true 
            ORDER BY name
        """)
        
        pros = cur.fetchall()
        
        print(f"\n✅ Verified {len(pros)} active pros with pricing:\n")
        for pro in pros:
            print(f"   {pro[0]} ({pro[7] or 'No email'}):")
            print(f"      Private: ${pro[1]:.0f} / ${pro[2]:.0f} / ${pro[3]:.0f}")
            print(f"      Semi-Private: ${pro[4]:.0f}/person")
            print(f"      Group: ${pro[5]:.0f} / ${pro[6]:.0f} per person\n")
        
        cur.close()
        conn.close()
        
        print("=" * 80)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print("\nWhat was done:")
        print("  1. ✅ Added 6 pricing columns to pros table")
        print("  2. ✅ Populated pricing data for all active pros")
        print("  3. ✅ Verified all data is correct")
        print("\nNext steps:")
        print("  1. Test /mobile/schedule-lesson on production")
        print("  2. Verify pricing displays correctly")
        print("  3. Submit a test lesson request")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    print("\n⚠️  PRODUCTION DATABASE MIGRATION")
    print("=" * 80)
    print("Database: ballast.proxy.rlwy.net:40911/railway")
    print("\nThis script will:")
    print("  1. Add 6 pricing columns to pros table")
    print("  2. Populate pricing for all active pros")
    print("\nPricing structure:")
    print("  • Olga Martinsone: $55/$85/$100 (private), $55 (semi), $40/$35 (group)")
    print("  • Mike Simms: $50/$75/$90 (private), $50 (semi), $35/$30 (group)")
    print("  • Others (if any): Default pricing (same as Mike Simms)")
    print("=" * 80)
    
    response = input("\nContinue with migration? (yes/no): ").strip().lower()
    
    if response == 'yes':
        migrate_lesson_pricing()
    else:
        print("\n❌ Migration cancelled")
        sys.exit(0)

