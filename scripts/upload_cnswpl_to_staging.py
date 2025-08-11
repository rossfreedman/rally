#!/usr/bin/env python3
"""
Upload CNSWPL JSON files directly to Railway staging
"""

import os
import shutil
import subprocess
import json
import base64

def upload_files():
    print("🚀 UPLOADING CNSWPL JSON FILES TO RAILWAY STAGING")
    print("=" * 55)
    
    # CNSWPL files to upload
    files_to_upload = [
        "data/leagues/CNSWPL/match_history.json",
        "data/leagues/CNSWPL/players.json", 
        "data/leagues/CNSWPL/schedules.json",
        "data/leagues/CNSWPL/series_stats.json"
    ]
    
    # Check files exist locally
    print("📋 Checking local files...")
    for file_path in files_to_upload:
        if os.path.exists(file_path):
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            print(f"   ✅ {file_path} ({size_mb:.1f}MB)")
        else:
            print(f"   ❌ {file_path} - NOT FOUND")
            return False
    
    print("\n📤 Method 1: Using temporary file transfer...")
    
    for file_path in files_to_upload:
        print(f"\n🔄 Uploading {file_path}...")
        
        # Create remote path
        remote_path = f"/app/{file_path}"
        remote_dir = os.path.dirname(remote_path)
        
        # Create directory on staging
        mkdir_cmd = f'railway run --service="Rally STAGING App" -- mkdir -p {remote_dir}'
        print(f"   📁 Creating directory: {remote_dir}")
        result = subprocess.run(mkdir_cmd, shell=True, capture_output=True, text=True)
        
        # Method: Use base64 encoding to avoid command line length limits
        print(f"   📤 Encoding and uploading file content...")
        
        # Create upload script that decodes base64
        upload_script = f"""
import base64
import sys

# Read base64 content from stdin
b64_content = sys.stdin.read().strip()

# Decode and write to file
try:
    content = base64.b64decode(b64_content).decode('utf-8')
    with open('{remote_path}', 'w') as f:
        f.write(content)
    print("✅ Upload successful")
except Exception as e:
    print(f"❌ Upload failed: {{e}}")
    sys.exit(1)
"""
        
        # Encode file content to base64
        with open(file_path, 'rb') as f:
            file_content = f.read()
        b64_content = base64.b64encode(file_content).decode('ascii')
        
        # Write upload script to temp file
        script_path = f'/tmp/upload_script_{os.path.basename(file_path)}.py'
        with open(script_path, 'w') as f:
            f.write(upload_script)
        
        # Upload the script first
        script_upload_cmd = f'railway run --service="Rally STAGING App" -- bash -c "cat > /tmp/upload_script.py" < {script_path}'
        result = subprocess.run(script_upload_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"   ❌ Failed to upload script: {result.stderr}")
            return False
        
        # Run the upload script with base64 content
        upload_cmd = f'echo "{b64_content}" | railway run --service="Rally STAGING App" -- python3 /tmp/upload_script.py'
        
        try:
            result = subprocess.run(upload_cmd, shell=True, capture_output=True, text=True, timeout=300)
            if result.returncode == 0 and "✅ Upload successful" in result.stdout:
                print(f"   ✅ Success: {os.path.basename(file_path)}")
            else:
                print(f"   ❌ Failed: {result.stderr}")
                print(f"   Output: {result.stdout}")
                return False
        except subprocess.TimeoutExpired:
            print(f"   ⏰ Timeout uploading {file_path}")
            return False
        
        # Clean up temp file
        os.remove(script_path)
    
    print("\n🔍 Verifying upload...")
    verify_cmd = 'railway run --service="Rally STAGING App" -- ls -la /app/data/leagues/CNSWPL/'
    result = subprocess.run(verify_cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    
    print("\n✅ CNSWPL JSON files uploaded to staging!")
    print("🔄 Ready to run ETL import on staging")
    
    return True

if __name__ == "__main__":
    success = upload_files()
    if success:
        print("\n🚀 Next step: Run ETL import on staging")
        print("Command: railway run --service='Rally STAGING App' -- python3 data/etl/database_import/master_import.py")
    else:
        print("\n❌ Upload failed - check errors above")
