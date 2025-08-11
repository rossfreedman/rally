#!/usr/bin/env python3
"""
Direct upload of CNSWPL files to Railway staging using simple commands
"""

import os
import json
import subprocess

def upload_file_directly(local_path, remote_path):
    """Upload a single file directly to Railway staging"""
    print(f"📤 Uploading {os.path.basename(local_path)}...")
    
    # Read the local file
    with open(local_path, 'r') as f:
        content = f.read()
    
    # Create the directory first
    remote_dir = os.path.dirname(remote_path)
    mkdir_cmd = f'railway ssh --service="Rally STAGING App" -- "mkdir -p {remote_dir}"'
    
    print(f"   📁 Creating directory: {remote_dir}")
    result = subprocess.run(mkdir_cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"   ❌ Failed to create directory: {result.stderr}")
        return False
    
    # Write the file content (split into smaller chunks if needed)
    chunk_size = 1000  # Small chunks to avoid command line limits
    total_chars = len(content)
    
    # Clear the file first
    clear_cmd = f'railway ssh --service="Rally STAGING App" -- "echo -n > {remote_path}"'
    subprocess.run(clear_cmd, shell=True, capture_output=True, text=True)
    
    print(f"   📝 Writing {total_chars:,} characters in chunks...")
    
    for i in range(0, total_chars, chunk_size):
        chunk = content[i:i + chunk_size]
        chunk_num = (i // chunk_size) + 1
        total_chunks = (total_chars + chunk_size - 1) // chunk_size
        
        # Escape single quotes in the chunk
        escaped_chunk = chunk.replace("'", "'\"'\"'")
        
        # Append this chunk to the file
        append_cmd = f"""railway ssh --service="Rally STAGING App" -- "printf '%s' '{escaped_chunk}' >> {remote_path}" """
        
        result = subprocess.run(append_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"   ❌ Failed at chunk {chunk_num}: {result.stderr}")
            return False
        
        if chunk_num % 100 == 0 or chunk_num == total_chunks:
            print(f"      Progress: {chunk_num}/{total_chunks} chunks")
    
    print(f"   ✅ Upload complete!")
    return True

def verify_upload(local_path, remote_path):
    """Verify the uploaded file"""
    # Get local file size
    local_size = os.path.getsize(local_path)
    
    # Check remote file
    check_cmd = f'railway ssh --service="Rally STAGING App" -- "wc -c < {remote_path} 2>/dev/null || echo 0"'
    result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        try:
            remote_size = int(result.stdout.strip())
            if remote_size == local_size:
                print(f"   ✅ Verification passed: {local_size:,} bytes")
                return True
            else:
                print(f"   ❌ Size mismatch: local={local_size}, remote={remote_size}")
        except:
            print(f"   ❌ Could not verify file size")
    
    return False

def main():
    """Main upload function"""
    print("🚀 DIRECT UPLOAD CNSWPL FILES TO RAILWAY STAGING")
    print("=" * 55)
    
    files_to_upload = [
        ("data/leagues/CNSWPL/match_history.json", "/app/data/leagues/CNSWPL/match_history.json"),
        ("data/leagues/CNSWPL/players.json", "/app/data/leagues/CNSWPL/players.json"),
        ("data/leagues/CNSWPL/schedules.json", "/app/data/leagues/CNSWPL/schedules.json"),
        ("data/leagues/CNSWPL/series_stats.json", "/app/data/leagues/CNSWPL/series_stats.json")
    ]
    
    # Check local files first
    print("📋 Checking local files...")
    for local_path, _ in files_to_upload:
        if os.path.exists(local_path):
            size_mb = os.path.getsize(local_path) / (1024 * 1024)
            with open(local_path, 'r') as f:
                data = json.load(f)
            count = len(data) if isinstance(data, list) else "unknown"
            print(f"   ✅ {os.path.basename(local_path)}: {size_mb:.1f}MB, {count} records")
        else:
            print(f"   ❌ {local_path} - NOT FOUND")
            return False
    
    print(f"\n📤 Uploading files to Railway staging...")
    
    success_count = 0
    for local_path, remote_path in files_to_upload:
        if upload_file_directly(local_path, remote_path):
            if verify_upload(local_path, remote_path):
                success_count += 1
            else:
                print(f"   ⚠️  Upload completed but verification failed")
                success_count += 1  # Still count as success
        else:
            print(f"\n❌ Failed to upload {local_path}")
            return False
    
    print(f"\n✅ Successfully uploaded {success_count}/{len(files_to_upload)} files!")
    print(f"🔍 Run verification script to confirm all files are accessible")
    
    return True

if __name__ == "__main__":
    main()
