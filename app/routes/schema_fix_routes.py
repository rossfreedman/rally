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