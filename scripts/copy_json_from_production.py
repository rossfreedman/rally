#!/usr/bin/env python3
"""
Copy JSON Files from Production to Local

This script copies CNSWPL JSON files from Railway production to local
so you can test fixes locally with production data.

Usage:
    python3 scripts/copy_json_from_production.py [--league CNSWPL] [--all]
"""

import os
import sys
import subprocess
import json
import shutil
from datetime import datetime
from pathlib import Path

def check_railway_cli():
    """Check if Railway CLI is installed"""
    try:
        result = subprocess.run(['railway', '--version'], 
                              capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

def check_railway_login():
    """Check if logged into Railway"""
    try:
        result = subprocess.run(['railway', 'status'], 
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

def backup_local_files(local_path, files):
    """Backup existing local files"""
    backup_dir = Path(local_path) / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    backed_up = []
    for file in files:
        source = Path(local_path) / file
        if source.exists():
            dest = backup_dir / file
            shutil.copy2(source, dest)
            backed_up.append(file)
            print(f"   ✅ Backed up: {file}")
    
    return backup_dir, backed_up

def copy_file_from_production(production_path, local_path, filename):
    """Copy a single file from production using Railway CLI"""
    source_file = f"{production_path}/{filename}"
    local_file = Path(local_path) / filename
    
    # Create local directory if it doesn't exist
    local_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Use railway run to execute cat command on production
        cmd = [
            'railway', 'run',
            '--environment', 'production',
            '--service', 'rally-production',
            'cat', source_file
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and result.stdout:
            # Write the output to local file
            with open(local_file, 'w', encoding='utf-8') as f:
                f.write(result.stdout)
            
            # Validate JSON if it's a JSON file
            if filename.endswith('.json'):
                try:
                    with open(local_file, 'r', encoding='utf-8') as f:
                        json.load(f)
                except json.JSONDecodeError:
                    print(f"      ⚠️  Warning: {filename} is not valid JSON")
                    return False
            
            return True
        else:
            # Try alternative method: use railway shell
            print(f"      ⚠️  Trying alternative method for {filename}...")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"      ❌ Timeout copying {filename}")
        return False
    except Exception as e:
        print(f"      ❌ Error copying {filename}: {e}")
        return False

def copy_files_via_railway_shell(production_path, local_path, files):
    """Alternative method: SSH into production and copy files"""
    print("   Using Railway shell method...")
    
    # Create a temporary script
    script_content = f"""#!/bin/bash
cd {production_path}
for file in {" ".join(files)}; do
    if [ -f "$file" ]; then
        cat "$file"
        echo "---FILE_END---"
    fi
done
"""
    
    # Write script to temp file
    temp_script = Path('/tmp/railway_copy_script.sh')
    with open(temp_script, 'w') as f:
        f.write(script_content)
    temp_script.chmod(0o755)
    
    try:
        # Execute via railway shell
        cmd = ['railway', 'run', '--environment', 'production', 'bash', str(temp_script)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        # Parse output (files separated by ---FILE_END---)
        if result.returncode == 0:
            parts = result.stdout.split('---FILE_END---')
            for i, file in enumerate(files):
                if i < len(parts) - 1:  # Last part is empty
                    content = parts[i].strip()
                    if content:
                        local_file = Path(local_path) / file
                        with open(local_file, 'w', encoding='utf-8') as f:
                            f.write(content)
                        print(f"      ✅ Copied {file}")
                        return True
        
        return False
    except Exception as e:
        print(f"      ❌ Error with shell method: {e}")
        return False
    finally:
        if temp_script.exists():
            temp_script.unlink()

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Copy JSON files from production to local')
    parser.add_argument('--league', default='CNSWPL', help='League to copy (default: CNSWPL)')
    parser.add_argument('--all', action='store_true', help='Copy all JSON files, not just main ones')
    args = parser.parse_args()
    
    print("=" * 80)
    print("📋 Copying JSON Files from Production to Local")
    print("=" * 80)
    print()
    
    # Check prerequisites
    if not check_railway_cli():
        print("❌ Railway CLI not found. Please install it first:")
        print("   npm install -g @railway/cli")
        sys.exit(1)
    
    if not check_railway_login():
        print("❌ Not logged into Railway. Please run:")
        print("   railway login")
        sys.exit(1)
    
    # Setup paths
    league = args.league
    production_path = f"/app/data/leagues/{league}"
    local_path = f"data/leagues/{league}"
    
    # Define files to copy
    main_files = [
        "series_stats.json",
        "match_history.json",
        "match_scores.json",
        "schedules.json",
        "players.json",
    ]
    
    files = main_files
    
    print(f"📁 Production path: {production_path}")
    print(f"📁 Local path: {local_path}")
    print()
    
    # Backup existing files
    print("💾 Backing up existing local files...")
    backup_dir, backed_up = backup_local_files(local_path, files)
    print(f"   Backup location: {backup_dir}")
    print()
    
    # Copy files
    print("📤 Copying files from production...")
    copied = 0
    failed = []
    
    for file in files:
        print(f"   Copying {file}...")
        if copy_file_from_production(production_path, local_path, file):
            file_size = Path(local_path) / file
            if file_size.exists():
                size = file_size.stat().st_size
                print(f"      ✅ Copied {file} ({size:,} bytes)")
                copied += 1
            else:
                print(f"      ❌ File not found after copy: {file}")
                failed.append(file)
        else:
            # Try alternative method
            if copy_files_via_railway_shell(production_path, local_path, [file]):
                copied += 1
            else:
                print(f"      ❌ Failed to copy: {file}")
                failed.append(file)
    
    print()
    print("=" * 80)
    print("📊 Summary")
    print("=" * 80)
    print(f"✅ Successfully copied: {copied} files")
    if failed:
        print(f"❌ Failed: {len(failed)} files - {', '.join(failed)}")
    print(f"💾 Backup location: {backup_dir}")
    print()
    
    if copied > 0:
        print("✅ Files are ready for local testing!")
        print()
        print("You can now run:")
        print(f"   python3 scripts/fix_cnswpl_series_h_stats.py")
    
    if failed:
        print()
        print("⚠️  Some files failed to copy.")
        print("   They may not exist on production, or there was a connection issue.")
        print("   You can manually check production via:")
        print(f"   railway ssh --environment production")
        print(f"   ls -lh {production_path}/")

if __name__ == "__main__":
    main()

