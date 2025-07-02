#!/usr/bin/env python3
"""
Automated ETL Runner for Railway

This script automates the process of running ETL on Railway's infrastructure
from your local machine. It handles SSH connection and command execution.
"""

import subprocess
import sys
import time
import argparse
from datetime import datetime

class RailwayETLRunner:
    def __init__(self):
        self.railway_connected = False
    
    def log(self, message, level="INFO"):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def check_railway_status(self):
        """Check if Railway CLI is connected"""
        try:
            result = subprocess.run(
                ["railway", "status"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            
            if "Project:" in result.stdout:
                self.log("✅ Railway CLI connected")
                self.log(f"📊 {result.stdout.strip()}")
                return True
            else:
                self.log("❌ Railway CLI not connected", "ERROR")
                return False
                
        except subprocess.CalledProcessError as e:
            self.log(f"❌ Railway status check failed: {e}", "ERROR")
            return False
    
    def test_railway_connection(self):
        """Test Railway database connection"""
        try:
            self.log("🔍 Testing Railway database connection...")
            result = subprocess.run([
                "railway", "run", 
                "python", "chronjobs/railway_cron_etl.py", "--test-only"
            ], capture_output=True, text=True, check=True)
            
            if "✅ Database connection successful!" in result.stdout:
                self.log("✅ Railway database connection test passed")
                return True
            else:
                self.log("❌ Railway database connection test failed", "ERROR")
                self.log(result.stdout)
                return False
                
        except subprocess.CalledProcessError as e:
            self.log(f"❌ Railway connection test failed: {e}", "ERROR")
            return False
    
    def run_etl_via_railway_run(self, environment=None, disable_validation=None):
        """Run ETL using 'railway run' (executes locally with Railway env vars)"""
        self.log("🚀 Starting ETL via 'railway run'...")
        
        cmd = ["railway", "run", "python", "chronjobs/railway_background_etl.py"]
        if environment:
            cmd.extend(["--environment", environment])
        if disable_validation is True:
            cmd.append("--disable-validation")
        elif disable_validation is False:
            cmd.append("--enable-validation")
        
        try:
            # Run with real-time output
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Stream output in real-time
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    print(output.strip())
            
            return_code = process.poll()
            
            if return_code == 0:
                self.log("🎉 ETL completed successfully!")
                return True
            else:
                self.log(f"❌ ETL failed with return code {return_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ ETL execution failed: {e}", "ERROR")
            return False
    
    def run_etl_via_ssh(self, environment=None, disable_validation=None):
        """Run ETL via Railway SSH (executes on Railway servers)"""
        self.log("🚀 Starting ETL via Railway SSH...")
        
        cmd = "python chronjobs/railway_background_etl.py"
        if environment:
            cmd += f" --environment {environment}"
        if disable_validation is True:
            cmd += " --disable-validation"
        elif disable_validation is False:
            cmd += " --enable-validation"
        
        try:
            # Create a temporary script for SSH execution
            ssh_script = f'''
            set -e
            echo "🔗 Connected to Railway server"
            echo "📁 Current directory: $(pwd)"
            echo "🐍 Python version: $(python --version)"
            echo "🚀 Starting ETL process..."
            {cmd}
            echo "✅ ETL process completed"
            '''
            
            # Execute via SSH
            result = subprocess.run([
                "railway", "ssh", "-c", ssh_script
            ], text=True)
            
            if result.returncode == 0:
                self.log("🎉 ETL via SSH completed successfully!")
                return True
            else:
                self.log(f"❌ ETL via SSH failed with return code {result.returncode}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ SSH ETL execution failed: {e}", "ERROR")
            return False
    
    def trigger_railway_cron(self):
        """Trigger Railway cron job manually (if supported)"""
        self.log("🔄 Attempting to trigger Railway cron job...")
        # Note: Railway doesn't have a direct CLI command to trigger cron jobs
        # This would require Railway API integration
        self.log("⚠️ Manual cron triggering not supported via CLI", "WARNING")
        return False
    
    def run_automated_etl(self, method="railway_run", environment=None, disable_validation=None):
        """Main automation method"""
        self.log("🤖 Starting automated ETL process...")
        self.log(f"📊 Method: {method}")
        if environment:
            self.log(f"🌍 Environment: {environment}")
        if disable_validation is not None:
            self.log(f"🔧 Validation: {'disabled' if disable_validation else 'enabled'}")
        
        # Step 1: Check Railway connection
        if not self.check_railway_status():
            self.log("❌ Please run 'railway login' and link your project", "ERROR")
            return False
        
        # Step 2: Test database connection
        if not self.test_railway_connection():
            self.log("❌ Database connection test failed", "ERROR")
            return False
        
        # Step 3: Run ETL based on method
        start_time = datetime.now()
        
        if method == "railway_run":
            success = self.run_etl_via_railway_run(environment=environment, disable_validation=disable_validation)
        elif method == "ssh":
            success = self.run_etl_via_ssh(environment=environment, disable_validation=disable_validation)
        elif method == "cron":
            success = self.trigger_railway_cron()
        else:
            self.log(f"❌ Unknown method: {method}", "ERROR")
            return False
        
        # Step 4: Report results
        end_time = datetime.now()
        duration = end_time - start_time
        
        if success:
            self.log(f"🎊 Automated ETL completed successfully in {duration}")
        else:
            self.log(f"💥 Automated ETL failed after {duration}", "ERROR")
        
        return success

def main():
    parser = argparse.ArgumentParser(description='Automated ETL Runner for Railway')
    parser.add_argument('--method', choices=['railway_run', 'ssh', 'cron'], 
                       default='railway_run',
                       help='Method to run ETL (default: railway_run)')
    parser.add_argument('--environment', '-e',
                       choices=['local', 'railway_staging', 'railway_production'],
                       help='Force specific environment (overrides auto-detection)')
    parser.add_argument('--disable-validation', action='store_true',
                       help='Disable player validation for faster imports')
    parser.add_argument('--enable-validation', action='store_true',
                       help='Enable player validation (overrides environment defaults)')
    parser.add_argument('--test-only', action='store_true',
                       help='Only test connection, don\'t run ETL')
    
    args = parser.parse_args()
    
    # Handle validation arguments
    disable_validation = None
    if args.disable_validation:
        disable_validation = True
    elif args.enable_validation:
        disable_validation = False
    
    runner = RailwayETLRunner()
    
    if args.test_only:
        print("🧪 Testing Railway connection only...")
        runner.check_railway_status()
        runner.test_railway_connection()
    else:
        success = runner.run_automated_etl(
            method=args.method,
            environment=args.environment,
            disable_validation=disable_validation
        )
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 