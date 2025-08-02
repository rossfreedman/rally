#!/usr/bin/env python3
"""
Web-accessible constraint fix endpoint
Visit: https://your-railway-url.railway.app/fix-constraints
"""

import os
import sys
from flask import Flask, jsonify

# Prevent Flask startup conflicts
os.environ['CRON_JOB_MODE'] = 'true'

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)

@app.route('/fix-constraints')
def fix_constraints():
    """Web endpoint to fix database constraints"""
    try:
        from scripts.fix_missing_database_constraints import DatabaseConstraintFixer
        
        fixer = DatabaseConstraintFixer()
        success = fixer.fix_all_constraints()
        
        if success:
            return jsonify({
                "status": "success",
                "message": "Database constraints fixed successfully!",
                "note": "ETL imports should now work properly"
            })
        else:
            return jsonify({
                "status": "error", 
                "message": "Some constraints could not be created"
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/health')
def health():
    return jsonify({"status": "ok", "service": "constraint-fixer"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)