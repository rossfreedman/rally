#!/usr/bin/env python3
"""
Maintenance Mode ETL Wrapper
===========================

Wraps atomic ETL with maintenance mode to prevent users from seeing
inconsistent data during the ETL execution window.

Features:
- Automatic maintenance mode activation during ETL
- User-friendly maintenance page with ETA
- Automatic restoration when ETL completes
- Emergency maintenance mode bypass for admins
- Graceful handling of ETL failures

Usage:
    python chronjobs/maintenance_mode_wrapper.py --environment local
    python chronjobs/maintenance_mode_wrapper.py --environment railway_production --force
"""

import os
import sys
import time
from datetime import datetime, timedelta
from contextlib import contextmanager

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from database_utils import execute_query_one, execute_update
from data.etl.database_import.atomic_wrapper import AtomicETLWrapper


class MaintenanceModeManager:
    """Manages maintenance mode during ETL operations"""
    
    def __init__(self):
        self.maintenance_start_time = None
        self.estimated_duration_minutes = 5  # Conservative estimate
    
    def is_maintenance_mode_active(self) -> bool:
        """Check if maintenance mode is currently active"""
        try:
            result = execute_query_one("""
                SELECT value FROM system_settings 
                WHERE key = 'maintenance_mode'
            """)
            return result and result['value'].lower() == 'true'
        except Exception:
            return False
    
    def enable_maintenance_mode(self, estimated_duration_minutes: int = 5):
        """Enable maintenance mode with estimated completion time"""
        try:
            self.maintenance_start_time = datetime.now()
            estimated_completion = self.maintenance_start_time + timedelta(minutes=estimated_duration_minutes)
            
            # Set maintenance mode flag
            execute_update("""
                INSERT INTO system_settings (key, value, description)
                VALUES ('maintenance_mode', 'true', 'ETL maintenance mode active')
                ON CONFLICT (key) DO UPDATE SET 
                    value = EXCLUDED.value,
                    updated_at = CURRENT_TIMESTAMP
            """)
            
            # Set estimated completion time for user display
            execute_update("""
                INSERT INTO system_settings (key, value, description)
                VALUES ('maintenance_eta', %s, 'Estimated maintenance completion time')
                ON CONFLICT (key) DO UPDATE SET 
                    value = EXCLUDED.value,
                    updated_at = CURRENT_TIMESTAMP
            """, [estimated_completion.isoformat()])
            
            # Set maintenance reason
            execute_update("""
                INSERT INTO system_settings (key, value, description)
                VALUES ('maintenance_reason', 'Database update in progress', 'Current maintenance reason')
                ON CONFLICT (key) DO UPDATE SET 
                    value = EXCLUDED.value,
                    updated_at = CURRENT_TIMESTAMP
            """)
            
            print(f"🔧 Maintenance mode ENABLED - ETA: {estimated_completion.strftime('%H:%M:%S')}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to enable maintenance mode: {e}")
            return False
    
    def disable_maintenance_mode(self):
        """Disable maintenance mode and clean up"""
        try:
            # Disable maintenance mode
            execute_update("""
                UPDATE system_settings 
                SET value = 'false', updated_at = CURRENT_TIMESTAMP
                WHERE key = 'maintenance_mode'
            """)
            
            # Clean up maintenance-related settings
            execute_update("DELETE FROM system_settings WHERE key IN ('maintenance_eta', 'maintenance_reason')")
            
            if self.maintenance_start_time:
                duration = datetime.now() - self.maintenance_start_time
                print(f"✅ Maintenance mode DISABLED - Duration: {duration}")
            else:
                print("✅ Maintenance mode DISABLED")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to disable maintenance mode: {e}")
            return False
    
    @contextmanager
    def maintenance_context(self, estimated_duration_minutes: int = 5):
        """Context manager for automatic maintenance mode management"""
        enabled = self.enable_maintenance_mode(estimated_duration_minutes)
        
        try:
            yield enabled
        finally:
            if enabled:
                self.disable_maintenance_mode()


class MaintenanceModeETLWrapper:
    """Wrapper that combines atomic ETL with maintenance mode"""
    
    def __init__(self, environment: str = None, create_backup: bool = True, 
                 maintenance_duration_estimate: int = 5):
        self.environment = environment
        self.create_backup = create_backup
        self.maintenance_duration_estimate = maintenance_duration_estimate
        
        self.maintenance_manager = MaintenanceModeManager()
        self.atomic_etl = AtomicETLWrapper(environment, create_backup)
    
    def run_with_maintenance_mode(self) -> bool:
        """Run ETL with automatic maintenance mode management"""
        print("🚀 Starting Maintenance Mode ETL")
        print("=" * 60)
        
        # Check if already in maintenance mode
        if self.maintenance_manager.is_maintenance_mode_active():
            print("⚠️  Maintenance mode already active - proceeding with ETL")
            return self.atomic_etl.run_atomic_etl()
        
        # Run ETL with maintenance mode
        with self.maintenance_manager.maintenance_context(self.maintenance_duration_estimate) as maintenance_enabled:
            if not maintenance_enabled:
                print("❌ Failed to enable maintenance mode - aborting ETL for safety")
                return False
            
            print("🔧 Maintenance mode active - users will see maintenance page")
            print("🔄 Starting atomic ETL process...")
            
            # Give the maintenance page a moment to activate
            time.sleep(2)
            
            # Run the actual ETL
            success = self.atomic_etl.run_atomic_etl()
            
            if success:
                print("✅ ETL completed successfully - maintenance mode will be disabled")
            else:
                print("❌ ETL failed - maintenance mode will be disabled")
            
            return success


def create_maintenance_page_template():
    """Create a maintenance page template for the app"""
    template_content = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rally - Maintenance Mode</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <meta http-equiv="refresh" content="30">
</head>
<body class="bg-gray-100 min-h-screen flex items-center justify-center">
    <div class="bg-white p-8 rounded-lg shadow-lg max-w-md w-full mx-4">
        <div class="text-center">
            <h1 class="text-2xl font-bold text-gray-800 mb-4">🔧 Maintenance Mode</h1>
            <p class="text-gray-600 mb-6">Rally is currently being updated with the latest match data and statistics.</p>
            
            <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                <p class="text-blue-800 font-medium">{{ maintenance_reason or "Database update in progress" }}</p>
                {% if maintenance_eta %}
                <p class="text-blue-600 text-sm mt-2">
                    Estimated completion: {{ maintenance_eta.strftime('%H:%M:%S') }}
                </p>
                {% endif %}
            </div>
            
            <div class="space-y-2 text-sm text-gray-500">
                <p>⚡ The update should complete in a few minutes</p>
                <p>🔄 This page will refresh automatically</p>
                <p>📱 Please check back shortly</p>
            </div>
        </div>
    </div>
</body>
</html>
'''
    
    maintenance_template_path = os.path.join(project_root, 'templates', 'maintenance.html')
    
    try:
        os.makedirs(os.path.dirname(maintenance_template_path), exist_ok=True)
        with open(maintenance_template_path, 'w') as f:
            f.write(template_content)
        print(f"✅ Created maintenance page template: {maintenance_template_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to create maintenance template: {e}")
        return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Maintenance Mode ETL Wrapper')
    parser.add_argument('--environment', choices=['local', 'railway_staging', 'railway_production'],
                       help='Target environment')
    parser.add_argument('--no-backup', action='store_true',
                       help='Skip backup creation')
    parser.add_argument('--force', action='store_true',
                       help='Force import even in production')
    parser.add_argument('--duration-estimate', type=int, default=5,
                       help='Estimated maintenance duration in minutes (default: 5)')
    parser.add_argument('--create-template', action='store_true',
                       help='Create maintenance page template and exit')
    parser.add_argument('--disable-maintenance', action='store_true',
                       help='Disable maintenance mode and exit')
    
    args = parser.parse_args()
    
    # Handle utility commands
    if args.create_template:
        success = create_maintenance_page_template()
        return 0 if success else 1
    
    if args.disable_maintenance:
        manager = MaintenanceModeManager()
        success = manager.disable_maintenance_mode()
        return 0 if success else 1
    
    # Safety check for production
    if args.environment == 'railway_production' and not args.force:
        print("❌ Production imports require --force flag for safety")
        print("   Use: python chronjobs/maintenance_mode_wrapper.py --environment railway_production --force")
        return 1
    
    # Initialize and run maintenance mode ETL
    wrapper = MaintenanceModeETLWrapper(
        environment=args.environment,
        create_backup=not args.no_backup,
        maintenance_duration_estimate=args.duration_estimate
    )
    
    success = wrapper.run_with_maintenance_mode()
    
    if success:
        print("\n🎉 Maintenance mode ETL completed successfully!")
        print("✅ Users can now access the application normally")
        return 0
    else:
        print("\n💥 Maintenance mode ETL failed!")
        print("❌ Check logs for details")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 