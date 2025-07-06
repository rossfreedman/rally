"""
Admin Maintenance Routes
=======================

Admin-only routes for emergency maintenance mode control during ETL operations.
"""

from flask import Blueprint, request, jsonify, session, render_template_string
from functools import wraps
from database_utils import execute_query_one, execute_update
from datetime import datetime

# Create blueprint
admin_maintenance = Blueprint('admin_maintenance', __name__, url_prefix='/admin')


def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user', {})
        if not user.get('is_admin', False):
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function


@admin_maintenance.route('/maintenance-status')
@admin_required
def maintenance_status():
    """Get current maintenance mode status"""
    try:
        # Check maintenance mode status
        mode_result = execute_query_one("""
            SELECT value FROM system_settings 
            WHERE key = 'maintenance_mode'
        """)
        
        # Get maintenance reason
        reason_result = execute_query_one("""
            SELECT value FROM system_settings 
            WHERE key = 'maintenance_reason'
        """)
        
        # Get maintenance ETA
        eta_result = execute_query_one("""
            SELECT value FROM system_settings 
            WHERE key = 'maintenance_eta'
        """)
        
        is_active = mode_result and mode_result['value'].lower() == 'true'
        
        status = {
            'maintenance_active': is_active,
            'reason': reason_result['value'] if reason_result else None,
            'eta': eta_result['value'] if eta_result else None,
            'current_time': datetime.now().isoformat()
        }
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({'error': f'Failed to get maintenance status: {str(e)}'}), 500


@admin_maintenance.route('/disable-maintenance', methods=['POST'])
@admin_required
def disable_maintenance():
    """Emergency disable maintenance mode"""
    try:
        # Disable maintenance mode
        execute_update("""
            UPDATE system_settings 
            SET value = 'false', updated_at = CURRENT_TIMESTAMP
            WHERE key = 'maintenance_mode'
        """)
        
        # Clean up maintenance-related settings
        execute_update("""
            DELETE FROM system_settings 
            WHERE key IN ('maintenance_eta', 'maintenance_reason')
        """)
        
        # Log the admin action
        admin_user = session.get('user', {})
        admin_email = admin_user.get('email', 'unknown')
        
        return jsonify({
            'success': True,
            'message': 'Maintenance mode disabled successfully',
            'disabled_by': admin_email,
            'disabled_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to disable maintenance mode: {str(e)}'}), 500


@admin_maintenance.route('/enable-maintenance', methods=['POST'])
@admin_required
def enable_maintenance():
    """Manually enable maintenance mode"""
    try:
        data = request.get_json() or {}
        reason = data.get('reason', 'Manual maintenance mode activation')
        duration_minutes = data.get('duration_minutes', 5)
        
        # Calculate ETA
        from datetime import timedelta
        eta = datetime.now() + timedelta(minutes=duration_minutes)
        
        # Enable maintenance mode
        execute_update("""
            INSERT INTO system_settings (key, value, description)
            VALUES ('maintenance_mode', 'true', 'Manual maintenance mode')
            ON CONFLICT (key) DO UPDATE SET 
                value = EXCLUDED.value,
                updated_at = CURRENT_TIMESTAMP
        """)
        
        # Set reason
        execute_update("""
            INSERT INTO system_settings (key, value, description)
            VALUES ('maintenance_reason', %s, 'Maintenance reason')
            ON CONFLICT (key) DO UPDATE SET 
                value = EXCLUDED.value,
                updated_at = CURRENT_TIMESTAMP
        """, [reason])
        
        # Set ETA
        execute_update("""
            INSERT INTO system_settings (key, value, description)
            VALUES ('maintenance_eta', %s, 'Maintenance ETA')
            ON CONFLICT (key) DO UPDATE SET 
                value = EXCLUDED.value,
                updated_at = CURRENT_TIMESTAMP
        """, [eta.isoformat()])
        
        admin_user = session.get('user', {})
        admin_email = admin_user.get('email', 'unknown')
        
        return jsonify({
            'success': True,
            'message': 'Maintenance mode enabled successfully',
            'reason': reason,
            'eta': eta.isoformat(),
            'enabled_by': admin_email,
            'enabled_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to enable maintenance mode: {str(e)}'}), 500


@admin_maintenance.route('/maintenance-control')
@admin_required  
def maintenance_control_page():
    """Admin page for maintenance mode control"""
    
    # Get current status
    try:
        mode_result = execute_query_one("""
            SELECT value FROM system_settings WHERE key = 'maintenance_mode'
        """)
        reason_result = execute_query_one("""
            SELECT value FROM system_settings WHERE key = 'maintenance_reason'
        """)
        eta_result = execute_query_one("""
            SELECT value FROM system_settings WHERE key = 'maintenance_eta'
        """)
        
        is_active = mode_result and mode_result['value'].lower() == 'true'
        current_reason = reason_result['value'] if reason_result else 'No reason set'
        current_eta = eta_result['value'] if eta_result else 'No ETA set'
        
    except Exception:
        is_active = False
        current_reason = 'Status check failed'
        current_eta = 'Unknown'
    
    admin_user = session.get('user', {})
    admin_name = f"{admin_user.get('first_name', '')} {admin_user.get('last_name', '')}".strip()
    
    html_template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Rally Admin - Maintenance Control</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 min-h-screen py-8">
        <div class="max-w-2xl mx-auto">
            <div class="bg-white rounded-lg shadow-lg p-6">
                <h1 class="text-2xl font-bold text-gray-800 mb-6">🔧 Maintenance Mode Control</h1>
                
                <div class="mb-6 p-4 rounded-lg {{ 'bg-red-50 border border-red-200' if is_active else 'bg-green-50 border border-green-200' }}">
                    <h2 class="text-lg font-semibold {{ 'text-red-800' if is_active else 'text-green-800' }}">
                        Status: {{ 'ACTIVE' if is_active else 'INACTIVE' }}
                    </h2>
                    {% if is_active %}
                    <p class="text-red-600 mt-2">
                        <strong>Reason:</strong> {{ current_reason }}<br>
                        <strong>ETA:</strong> {{ current_eta }}
                    </p>
                    {% else %}
                    <p class="text-green-600 mt-2">Application is running normally</p>
                    {% endif %}
                </div>
                
                <div class="space-y-4">
                    {% if is_active %}
                    <button onclick="disableMaintenance()" 
                            class="w-full bg-red-600 hover:bg-red-700 text-white font-bold py-3 px-4 rounded">
                        🚨 EMERGENCY DISABLE MAINTENANCE MODE
                    </button>
                    {% else %}
                    <div class="space-y-3">
                        <input type="text" id="reason" placeholder="Maintenance reason" 
                               class="w-full p-2 border border-gray-300 rounded" 
                               value="Manual maintenance activation">
                        <input type="number" id="duration" placeholder="Duration (minutes)" 
                               class="w-full p-2 border border-gray-300 rounded" 
                               value="5" min="1" max="60">
                        <button onclick="enableMaintenance()" 
                                class="w-full bg-yellow-600 hover:bg-yellow-700 text-white font-bold py-3 px-4 rounded">
                            🔧 Enable Maintenance Mode
                        </button>
                    </div>
                    {% endif %}
                </div>
                
                <div class="mt-6 p-4 bg-gray-50 rounded-lg">
                    <h3 class="font-semibold text-gray-700 mb-2">Admin Info</h3>
                    <p class="text-sm text-gray-600">
                        Logged in as: {{ admin_name }}<br>
                        Current time: {{ current_time }}
                    </p>
                </div>
                
                <div id="result" class="mt-4"></div>
            </div>
        </div>
        
        <script>
            async function disableMaintenance() {
                try {
                    const response = await fetch('/admin/disable-maintenance', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'}
                    });
                    const result = await response.json();
                    
                    if (result.success) {
                        showResult('✅ Maintenance mode disabled successfully!', 'success');
                        setTimeout(() => location.reload(), 2000);
                    } else {
                        showResult('❌ Failed: ' + result.error, 'error');
                    }
                } catch (error) {
                    showResult('❌ Error: ' + error.message, 'error');
                }
            }
            
            async function enableMaintenance() {
                try {
                    const reason = document.getElementById('reason').value;
                    const duration = parseInt(document.getElementById('duration').value);
                    
                    if (!reason.trim()) {
                        showResult('❌ Please enter a reason', 'error');
                        return;
                    }
                    
                    const response = await fetch('/admin/enable-maintenance', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            reason: reason,
                            duration_minutes: duration
                        })
                    });
                    const result = await response.json();
                    
                    if (result.success) {
                        showResult('✅ Maintenance mode enabled successfully!', 'success');
                        setTimeout(() => location.reload(), 2000);
                    } else {
                        showResult('❌ Failed: ' + result.error, 'error');
                    }
                } catch (error) {
                    showResult('❌ Error: ' + error.message, 'error');
                }
            }
            
            function showResult(message, type) {
                const resultDiv = document.getElementById('result');
                const bgColor = type === 'success' ? 'bg-green-100 border-green-400 text-green-700' : 'bg-red-100 border-red-400 text-red-700';
                resultDiv.innerHTML = `<div class="border ${bgColor} px-4 py-3 rounded">${message}</div>`;
            }
        </script>
    </body>
    </html>
    '''
    
    return render_template_string(html_template, 
                                is_active=is_active,
                                current_reason=current_reason,
                                current_eta=current_eta,
                                admin_name=admin_name or 'Unknown Admin',
                                current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


@admin_maintenance.route('/etl-control')
@admin_required
def etl_control_page():
    """Admin page for ETL control with maintenance mode"""
    
    admin_user = session.get('user', {})
    admin_name = f"{admin_user.get('first_name', '')} {admin_user.get('last_name', '')}".strip()
    
    html_template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Rally Admin - ETL Control</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 min-h-screen py-8">
        <div class="max-w-2xl mx-auto">
            <div class="bg-white rounded-lg shadow-lg p-6">
                <h1 class="text-2xl font-bold text-gray-800 mb-6">🚀 ETL Control Panel</h1>
                
                <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                    <h2 class="text-lg font-semibold text-blue-800">Production ETL Commands</h2>
                    <p class="text-blue-600 text-sm mt-2">Use these commands to run ETL with maintenance mode protection</p>
                </div>
                
                <div class="space-y-4">
                    <div class="p-4 bg-gray-50 rounded-lg">
                        <h3 class="font-semibold text-gray-700 mb-2">🏠 Local ETL (Development)</h3>
                        <code class="block text-sm bg-gray-800 text-green-400 p-2 rounded">
                            python chronjobs/maintenance_mode_wrapper.py --environment local
                        </code>
                    </div>
                    
                    <div class="p-4 bg-gray-50 rounded-lg">
                        <h3 class="font-semibold text-gray-700 mb-2">🟡 Staging ETL</h3>
                        <code class="block text-sm bg-gray-800 text-green-400 p-2 rounded">
                            python chronjobs/maintenance_mode_wrapper.py --environment railway_staging
                        </code>
                    </div>
                    
                    <div class="p-4 bg-red-50 border border-red-200 rounded-lg">
                        <h3 class="font-semibold text-red-700 mb-2">🔴 Production ETL (Requires --force)</h3>
                        <code class="block text-sm bg-gray-800 text-green-400 p-2 rounded">
                            python chronjobs/maintenance_mode_wrapper.py --environment railway_production --force
                        </code>
                        <p class="text-red-600 text-xs mt-2">⚠️ This will put the live site in maintenance mode for ~3-5 minutes</p>
                    </div>
                </div>
                
                <div class="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <h3 class="font-semibold text-yellow-800 mb-2">🛡️ How Maintenance Mode Works</h3>
                    <ul class="text-yellow-700 text-sm space-y-1">
                        <li>• Automatically enables maintenance mode before ETL starts</li>
                        <li>• Users see a friendly maintenance page instead of broken data</li>
                        <li>• Admins can still access the site during maintenance</li>
                        <li>• Automatically disables maintenance mode when ETL completes</li>
                        <li>• Emergency disable available if something goes wrong</li>
                    </ul>
                </div>
                
                <div class="mt-6 flex space-x-4">
                    <a href="/admin/maintenance-control" 
                       class="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded text-center">
                        🔧 Maintenance Control
                    </a>
                    <a href="/admin" 
                       class="flex-1 bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded text-center">
                        ← Back to Admin
                    </a>
                </div>
                
                <div class="mt-6 p-4 bg-gray-50 rounded-lg">
                    <h3 class="font-semibold text-gray-700 mb-2">Admin Info</h3>
                    <p class="text-sm text-gray-600">
                        Logged in as: {{ admin_name }}<br>
                        Current time: {{ current_time }}
                    </p>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''
    
    return render_template_string(html_template,
                                admin_name=admin_name or 'Unknown Admin',
                                current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')) 