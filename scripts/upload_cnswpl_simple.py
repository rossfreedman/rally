#!/usr/bin/env python3
"""
Simple CNSWPL file upload using chunks to avoid command line length limits
"""

import os
import subprocess
import json

def upload_file_in_chunks(local_path, remote_path, chunk_size=50000):
    """Upload file in chunks to avoid command line length limits"""
    print(f"   📤 Uploading {os.path.basename(local_path)} in chunks...")
    
    # Create remote directory
    remote_dir = os.path.dirname(remote_path)
    mkdir_cmd = f'railway run --service="Rally STAGING App" -- mkdir -p {remote_dir}'
    result = subprocess.run(mkdir_cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"   ❌ Failed to create directory: {result.stderr}")
        return False
    
    # Clear the target file first
    clear_cmd = f'railway run --service="Rally STAGING App" -- bash -c "echo -n > {remote_path}"'
    result = subprocess.run(clear_cmd, shell=True, capture_output=True, text=True)
    
    # Read file and upload in chunks
    with open(local_path, 'r') as f:
        content = f.read()
    
    # Split content into chunks
    total_chunks = (len(content) + chunk_size - 1) // chunk_size
    
    for i in range(0, len(content), chunk_size):
        chunk = content[i:i + chunk_size]
        chunk_num = (i // chunk_size) + 1
        
        print(f"      📦 Chunk {chunk_num}/{total_chunks} ({len(chunk)} chars)")
        
        # Escape the chunk content for shell
        escaped_chunk = chunk.replace("'", "'\"'\"'").replace("\n", "\\n")
        
        # Append chunk to remote file
        append_cmd = f'''railway run --service="Rally STAGING App" -- bash -c "printf '{escaped_chunk}' >> {remote_path}"'''
        
        result = subprocess.run(append_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"   ❌ Failed to upload chunk {chunk_num}: {result.stderr}")
            return False
    
    print(f"   ✅ Upload complete: {total_chunks} chunks")
    return True

def verify_upload(local_path, remote_path):
    """Verify the uploaded file matches local"""
    print(f"   🔍 Verifying {os.path.basename(local_path)}...")
    
    # Get local file size and line count
    local_size = os.path.getsize(local_path)
    with open(local_path, 'r') as f:
        local_lines = len(f.readlines())
    
    # Get remote file size and line count
    stat_cmd = f'railway run --service="Rally STAGING App" -- bash -c "stat -c %s {remote_path} && wc -l < {remote_path}"'
    result = subprocess.run(stat_cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"   ❌ Could not verify remote file: {result.stderr}")
        return False
    
    lines = result.stdout.strip().split('\n')
    remote_size = int(lines[0])
    remote_lines = int(lines[1])
    
    print(f"   📊 Local:  {local_size:,} bytes, {local_lines:,} lines")
    print(f"   📊 Remote: {remote_size:,} bytes, {remote_lines:,} lines")
    
    if local_size == remote_size and local_lines == remote_lines:
        print(f"   ✅ Verification passed")
        return True
    else:
        print(f"   ❌ Verification failed - size or line count mismatch")
        return False

def upload_cnswpl_files():
    """Main upload function"""
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
    for file_path in files_to_upload:
        if os.path.exists(file_path):
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            print(f"   ✅ {file_path} ({size_mb:.1f}MB)")
        else:
            print(f"   ❌ {file_path} - NOT FOUND")
            return False
    
    print("\n📤 Uploading files...")
    
    for file_path in files_to_upload:
        print(f"\n🔄 Processing {file_path}...")
        remote_path = f"/app/{file_path}"
        
        # Upload file
        if not upload_file_in_chunks(file_path, remote_path):
            return False
        
        # Verify upload
        if not verify_upload(file_path, remote_path):
            return False
    
    print("\n🔍 Final verification...")
    verify_cmd = 'railway run --service="Rally STAGING App" -- ls -la /app/data/leagues/CNSWPL/'
    result = subprocess.run(verify_cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    
    print("\n✅ All CNSWPL JSON files uploaded successfully!")
    return True

if __name__ == "__main__":
    success = upload_cnswpl_files()
    if not success:
        print("\n❌ Upload failed - check errors above")
        exit(1)
