#!/usr/bin/env python3
"""
Upload CNSWPL files to Railway staging using temporary local scripts
"""

import os
import subprocess
import tempfile
import json

def create_upload_script(files_to_upload):
    """Create a Python script that will run on Railway to create the files"""
    
    script_content = '''#!/usr/bin/env python3
import os
import json

def create_cnswpl_files():
    """Create CNSWPL files from embedded data"""
    
    # File data will be embedded here
    file_data = {
'''

    # Read each file and embed its content
    for file_path in files_to_upload:
        print(f"📖 Reading {file_path}...")
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Escape the content for Python string literal
        escaped_content = json.dumps(content)
        script_content += f'        "{file_path}": {escaped_content},\n'
    
    script_content += '''    }
    
    # Create each file
    for file_path, content in file_data.items():
        full_path = f"/app/{file_path}"
        
        # Create directory if needed
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Write file
        with open(full_path, 'w') as f:
            f.write(content)
        
        print(f"✅ Created {full_path} ({len(content):,} chars)")
    
    print("🎉 All CNSWPL files created successfully!")

if __name__ == "__main__":
    create_cnswpl_files()
'''
    
    return script_content

def upload_cnswpl_files():
    """Upload CNSWPL files using embedded script approach"""
    print("🚀 UPLOADING CNSWPL JSON FILES TO RAILWAY STAGING")
    print("=" * 55)
    
    files_to_upload = [
        "data/leagues/CNSWPL/match_history.json",
        "data/leagues/CNSWPL/players.json", 
        "data/leagues/CNSWPL/schedules.json",
        "data/leagues/CNSWPL/series_stats.json"
    ]
    
    # Check local files
    print("📋 Checking local files...")
    total_size = 0
    for file_path in files_to_upload:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            size_mb = size / (1024 * 1024)
            total_size += size
            print(f"   ✅ {file_path} ({size_mb:.1f}MB)")
        else:
            print(f"   ❌ {file_path} - NOT FOUND")
            return False
    
    print(f"\n📊 Total size: {total_size / (1024 * 1024):.1f}MB")
    
    # Create the upload script
    print("\n📝 Creating upload script...")
    script_content = create_upload_script(files_to_upload)
    
    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
        temp_file.write(script_content)
        temp_script_path = temp_file.name
    
    print(f"   📄 Script size: {len(script_content) / (1024 * 1024):.1f}MB")
    
    try:
        # Upload and run the script on Railway
        print("\n📤 Uploading and executing script on Railway...")
        
        # Create a command that uploads and runs the script
        upload_and_run_cmd = f'''
        railway run --service="Rally STAGING App" -- bash -c "
            cat > /tmp/create_cnswpl.py << 'SCRIPT_EOF'
$(cat {temp_script_path})
SCRIPT_EOF
            python3 /tmp/create_cnswpl.py
        "
        '''
        
        result = subprocess.run(upload_and_run_cmd, shell=True, capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            print("   ✅ Script executed successfully!")
            print("   Output:", result.stdout.strip()[-500:])  # Last 500 chars of output
        else:
            print("   ❌ Script execution failed!")
            print("   Error:", result.stderr)
            return False
        
    finally:
        # Clean up temp file
        os.unlink(temp_script_path)
    
    # Verify upload
    print("\n🔍 Verifying upload...")
    verify_cmd = 'railway run --service="Rally STAGING App" -- ls -la /app/data/leagues/CNSWPL/'
    result = subprocess.run(verify_cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    
    print("\n✅ CNSWPL files uploaded to staging!")
    return True

if __name__ == "__main__":
    success = upload_cnswpl_files()
    if not success:
        print("\n❌ Upload failed")
        exit(1)
