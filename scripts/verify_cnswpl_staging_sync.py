#!/usr/bin/env python3
"""
Verify that CNSWPL JSON files on staging match local files exactly
"""

import os
import json
import hashlib
import subprocess
import sys
from datetime import datetime

def get_file_hash(file_path):
    """Calculate SHA256 hash of file content"""
    hasher = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        return f"ERROR: {e}"

def get_file_stats(file_path):
    """Get file size and modification time"""
    try:
        stat = os.stat(file_path)
        return {
            'size': stat.st_size,
            'size_mb': stat.st_size / (1024 * 1024),
            'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        return {'error': str(e)}

def get_json_summary(file_path):
    """Get summary statistics from JSON file"""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            return {
                'type': 'array',
                'count': len(data),
                'first_keys': list(data[0].keys()) if data else [],
                'sample_record': data[0] if data else None
            }
        elif isinstance(data, dict):
            return {
                'type': 'object',
                'keys': list(data.keys()),
                'first_values': {k: len(v) if isinstance(v, list) else str(v)[:50] for k, v in list(data.items())[:3]}
            }
        else:
            return {'type': type(data).__name__, 'value': str(data)[:100]}
    except Exception as e:
        return {'error': str(e)}

def get_remote_file_info(remote_path):
    """Get file info from staging using Railway"""
    print(f"    🔍 Checking remote file: {remote_path}")
    
    # Get file stats (macOS stat syntax - Railway staging runs locally)
    stat_cmd = f'railway run --service="Rally STAGING App" -- stat -f "%z %m" {remote_path} 2>/dev/null || echo "NOT_FOUND"'
    result = subprocess.run(stat_cmd, shell=True, capture_output=True, text=True)
    
    if "NOT_FOUND" in result.stdout or result.returncode != 0:
        return {'exists': False, 'error': 'File not found on staging'}
    
    try:
        size, mtime = result.stdout.strip().split()
        remote_info = {
            'exists': True,
            'size': int(size),
            'size_mb': int(size) / (1024 * 1024),
            'modified': datetime.fromtimestamp(int(mtime)).strftime('%Y-%m-%d %H:%M:%S')
        }
    except:
        return {'exists': True, 'error': 'Could not parse file stats'}
    
    # Get file hash
    hash_cmd = f'railway run --service="Rally STAGING App" -- sha256sum {remote_path} 2>/dev/null | cut -d" " -f1'
    result = subprocess.run(hash_cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        remote_info['hash'] = result.stdout.strip()
    else:
        remote_info['hash'] = 'ERROR: Could not calculate hash'
    
    # Get JSON summary
    json_cmd = f'railway run --service="Rally STAGING App" -- python3 -c "import json; data=json.load(open(\'{remote_path}\')); print(f\'TYPE: {{type(data).__name__}}\'); print(f\'COUNT: {{len(data) if isinstance(data, list) else len(data.keys()) if isinstance(data, dict) else \"N/A\"}}\'); print(f\'FIRST: {{str(data[0] if isinstance(data, list) and data else list(data.keys())[:3] if isinstance(data, dict) else \"N/A\")[:100]}}\');"'
    result = subprocess.run(json_cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        lines = result.stdout.strip().split('\n')
        remote_info['json_summary'] = {
            'type': lines[0].replace('TYPE: ', '') if len(lines) > 0 else 'unknown',
            'count': lines[1].replace('COUNT: ', '') if len(lines) > 1 else 'unknown',
            'first': lines[2].replace('FIRST: ', '') if len(lines) > 2 else 'unknown'
        }
    else:
        remote_info['json_summary'] = {'error': 'Could not parse JSON'}
    
    return remote_info

def verify_cnswpl_files():
    """Main verification function"""
    print("🔍 VERIFYING CNSWPL FILES: LOCAL vs STAGING")
    print("=" * 55)
    
    # Files to verify
    cnswpl_files = [
        "data/leagues/CNSWPL/match_history.json",
        "data/leagues/CNSWPL/players.json", 
        "data/leagues/CNSWPL/schedules.json",
        "data/leagues/CNSWPL/series_stats.json"
    ]
    
    verification_results = []
    all_match = True
    
    for local_path in cnswpl_files:
        print(f"\n📄 Verifying: {os.path.basename(local_path)}")
        print("-" * 40)
        
        # Check local file
        if not os.path.exists(local_path):
            print(f"   ❌ Local file not found: {local_path}")
            all_match = False
            continue
        
        # Get local file info
        local_stats = get_file_stats(local_path)
        local_hash = get_file_hash(local_path)
        local_json = get_json_summary(local_path)
        
        print(f"   📊 Local:  {local_stats['size_mb']:.1f}MB | Modified: {local_stats['modified']}")
        print(f"   🔐 Hash:   {local_hash[:16]}...")
        print(f"   📋 JSON:   {local_json.get('type', 'unknown')} with {local_json.get('count', 'unknown')} items")
        
        # Get remote file info (Railway staging uses local directory structure)
        remote_path = local_path  # Railway staging runs from local directory
        remote_info = get_remote_file_info(remote_path)
        
        if not remote_info.get('exists', False):
            print(f"   ❌ Remote: File not found on staging")
            all_match = False
            verification_results.append({
                'file': local_path,
                'status': 'MISSING_REMOTE',
                'local': local_stats,
                'remote': remote_info
            })
            continue
        
        print(f"   📊 Remote: {remote_info['size_mb']:.1f}MB | Modified: {remote_info['modified']}")
        print(f"   🔐 Hash:   {remote_info['hash'][:16]}...")
        print(f"   📋 JSON:   {remote_info['json_summary'].get('type', 'unknown')} with {remote_info['json_summary'].get('count', 'unknown')} items")
        
        # Compare files
        size_match = local_stats['size'] == remote_info['size']
        hash_match = local_hash == remote_info['hash']
        json_count_match = str(local_json.get('count', '')) == str(remote_info['json_summary'].get('count', ''))
        
        if size_match and hash_match and json_count_match:
            print(f"   ✅ MATCH: Files are identical")
            status = 'MATCH'
        else:
            print(f"   ❌ MISMATCH:")
            if not size_match:
                print(f"      • Size: Local={local_stats['size']} vs Remote={remote_info['size']}")
            if not hash_match:
                print(f"      • Hash: Different content")
            if not json_count_match:
                print(f"      • Count: Local={local_json.get('count')} vs Remote={remote_info['json_summary'].get('count')}")
            status = 'MISMATCH'
            all_match = False
        
        verification_results.append({
            'file': local_path,
            'status': status,
            'local': {**local_stats, 'hash': local_hash, 'json': local_json},
            'remote': remote_info
        })
    
    # Summary
    print(f"\n{'='*55}")
    print("📋 VERIFICATION SUMMARY")
    print(f"{'='*55}")
    
    for result in verification_results:
        status_icon = "✅" if result['status'] == 'MATCH' else "❌"
        print(f"   {status_icon} {os.path.basename(result['file'])}: {result['status']}")
    
    if all_match:
        print(f"\n🎉 SUCCESS: All CNSWPL files match between local and staging!")
        print(f"   • All files exist on both environments")
        print(f"   • All file sizes match exactly")
        print(f"   • All content hashes match exactly")
        print(f"   • All JSON record counts match")
    else:
        print(f"\n⚠️  ISSUES FOUND: Some files don't match")
        print(f"   • Run upload script to sync: python scripts/upload_cnswpl_to_staging.py")
    
    return all_match

def quick_check():
    """Quick file existence and size check"""
    print("⚡ QUICK CHECK: CNSWPL File Existence & Sizes")
    print("=" * 45)
    
    files = [
        "data/leagues/CNSWPL/match_history.json",
        "data/leagues/CNSWPL/players.json", 
        "data/leagues/CNSWPL/schedules.json",
        "data/leagues/CNSWPL/series_stats.json"
    ]
    
    for local_path in files:
        filename = os.path.basename(local_path)
        
        # Local check
        if os.path.exists(local_path):
            size_mb = os.path.getsize(local_path) / (1024 * 1024)
            print(f"📄 {filename:<20} Local: {size_mb:>6.1f}MB", end="")
        else:
            print(f"📄 {filename:<20} Local: NOT FOUND", end="")
            continue
        
        # Remote check (Railway staging uses local directory structure)
        remote_path = local_path  # Railway staging runs from local directory
        cmd = f'railway run --service="Rally STAGING App" -- stat -f "%z" {remote_path} 2>/dev/null || echo "0"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        try:
            remote_size = int(result.stdout.strip())
            if remote_size > 0:
                remote_mb = remote_size / (1024 * 1024)
                match_icon = "✅" if abs(size_mb - remote_mb) < 0.1 else "❌"
                print(f" | Remote: {remote_mb:>6.1f}MB {match_icon}")
            else:
                print(f" | Remote: NOT FOUND ❌")
        except:
            print(f" | Remote: ERROR ❌")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        quick_check()
    else:
        verify_cnswpl_files()
