"""
Schema Fix Routes

Temporary route to apply schema fixes on Railway
"""

from flask import Blueprint, jsonify, render_template, request
from core.database import get_db
import logging

schema_fix_bp = Blueprint('schema_fix', __name__)

@schema_fix_bp.route('/admin/fix-schema', methods=['GET', 'POST'])
def fix_schema():
    """Apply schema fixes"""
    
    if request.method == 'GET':
        return render_template('admin/schema_fix.html')
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            results = []
            
            # Fix 1: Create system_settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    id SERIAL PRIMARY KEY,
                    key VARCHAR(255) UNIQUE NOT NULL,
                    value TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            results.append("✅ system_settings table created/verified")
            
            # Fix 2: Initialize session_version
            cursor.execute("""
                INSERT INTO system_settings (key, value, description) 
                VALUES ('session_version', '6', 'Current session version for cache busting')
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """)
            results.append("✅ session_version initialized")
            
            # Fix 3: Add logo_filename column to clubs
            cursor.execute("""
                ALTER TABLE clubs 
                ADD COLUMN IF NOT EXISTS logo_filename VARCHAR(255)
            """)
            results.append("✅ logo_filename column added")
            
            # Fix 4: Check what columns exist in player_availability table
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'player_availability'
                ORDER BY ordinal_position
            """)
            existing_columns = cursor.fetchall()
            column_names = [col[0] for col in existing_columns]
            results.append(f"📋 player_availability existing columns: {', '.join(column_names)}")
            
            # Fix 5: Add missing columns to player_availability table
            if 'user_id' not in column_names:
                cursor.execute("""
                    ALTER TABLE player_availability 
                    ADD COLUMN user_id INTEGER REFERENCES users(id)
                """)
                results.append("✅ user_id column added to player_availability")
            else:
                results.append("✅ user_id column already exists")
                
            if 'tenniscores_player_id' not in column_names:
                cursor.execute("""
                    ALTER TABLE player_availability 
                    ADD COLUMN tenniscores_player_id VARCHAR(255)
                """)
                results.append("✅ tenniscores_player_id column added to player_availability")
            else:
                results.append("✅ tenniscores_player_id column already exists")
                
            if 'availability_status' not in column_names:
                cursor.execute("""
                    ALTER TABLE player_availability 
                    ADD COLUMN availability_status INTEGER DEFAULT 1
                """)
                results.append("✅ availability_status column added to player_availability")
            else:
                results.append("✅ availability_status column already exists")
                
            if 'notes' not in column_names:
                cursor.execute("""
                    ALTER TABLE player_availability 
                    ADD COLUMN notes TEXT
                """)
                results.append("✅ notes column added to player_availability")
            else:
                results.append("✅ notes column already exists")
                
            if 'match_date' not in column_names:
                cursor.execute("""
                    ALTER TABLE player_availability 
                    ADD COLUMN match_date DATE
                """)
                results.append("✅ match_date column added to player_availability")
            else:
                results.append("✅ match_date column already exists")
            
            # Fix 6: Remove conflicting old unique constraint 
            try:
                cursor.execute("""
                    DROP INDEX IF EXISTS unique_player_availability
                """)
                results.append("✅ Removed conflicting unique_player_availability constraint")
            except Exception as drop_error:
                results.append(f"⚠️ Could not remove old constraint: {str(drop_error)}")
            
            # Fix 7: Create partial unique index for user_id + match_date (if user_id exists now)
            try:
                cursor.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_player_availability_user_date 
                    ON player_availability (user_id, match_date)
                    WHERE user_id IS NOT NULL
                """)
                results.append("✅ user_id + match_date unique index created")
            except Exception as idx_error:
                results.append(f"⚠️ Index creation skipped: {str(idx_error)}")
            
            # Fix 8: Populate user_id for existing availability records (only if both columns exist)
            cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'player_availability' AND column_name IN ('user_id', 'tenniscores_player_id')
            """)
            available_cols = [row[0] for row in cursor.fetchall()]
            
            if 'user_id' in available_cols and 'tenniscores_player_id' in available_cols:
                cursor.execute("""
                    UPDATE player_availability 
                    SET user_id = (
                        SELECT upa.user_id 
                        FROM user_player_associations upa 
                        WHERE upa.tenniscores_player_id = player_availability.tenniscores_player_id
                        LIMIT 1
                    )
                    WHERE user_id IS NULL 
                    AND tenniscores_player_id IS NOT NULL
                """)
                updated_count = cursor.rowcount
                if updated_count > 0:
                    results.append(f"✅ Populated user_id for {updated_count} existing availability records")
                else:
                    results.append("✅ No existing availability records needed user_id population")
            else:
                results.append("⚠️ Skipped user_id population - missing required columns")
            
            conn.commit()
            
            # Verify fixes
            cursor.execute("SELECT value FROM system_settings WHERE key = 'session_version'")
            version_result = cursor.fetchone()
            if version_result:
                results.append(f"✅ session_version = {version_result[0]}")
            else:
                results.append("❌ session_version not found")
            
            cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'clubs' AND column_name = 'logo_filename'
            """)
            column_result = cursor.fetchone()
            if column_result:
                results.append("✅ logo_filename column exists")
            else:
                results.append("❌ logo_filename column missing")
                
            # Verify user_id column exists
            cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'player_availability' AND column_name = 'user_id'
            """)
            user_id_result = cursor.fetchone()
            if user_id_result:
                results.append("✅ player_availability.user_id column exists")
            else:
                results.append("❌ player_availability.user_id column missing")
            
            return jsonify({
                'success': True,
                'message': 'Schema fixes applied successfully',
                'results': results
            })
            
    except Exception as e:
        logging.error(f"Schema fix error: {e}")
        return jsonify({
            'success': False,
            'message': f'Error applying schema fixes: {str(e)}'
        }), 500 