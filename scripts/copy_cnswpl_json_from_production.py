#!/usr/bin/env python3
"""
Copy CNSWPL JSON Files from Production to Local

This script uses Railway CLI to copy JSON files from production to local.
It creates a temporary script on production, executes it, and saves the output locally.

Usage:
    python3 scripts/copy_cnswpl_json_from_production.py
"""

import os
import sys
import subprocess
import json
import shutil
from datetime import datetime
from pathlib import Path

def check_command(cmd):
    """Check if a command exists"""
    try:
        subprocess.run(cmd, capture_output=True, check=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
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
            print(f"   ✅ Backed up: {file} ({source.stat().st_size:,} bytes)")
        else:
            print(f"   ⚠️  File not found locally (will download): {file}")
    
    return backup_dir

def get_file_from_production_via_ssh(filepath, output_path):
    """Get a file from production using Railway SSH"""
    try:
        # Use railway run to cat the file
        # This works by running a command on production that outputs the file
        cmd = [
            'railway', 'run',
            '--environment', 'production',
            'cat', filepath
        ]
        
        print(f"      Executing: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path(__file__).parent.parent
        )
        
        if result.returncode == 0:
            content = result.stdout
            if content and len(content.strip()) > 0:
                # Write to local file
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # Validate JSON
                try:
                    with open(output_path, 'r', encoding='utf-8') as f:
                        json.load(f)
                    return True
                except json.JSONDecodeError as e:
                    print(f"      ⚠️  Warning: File is not valid JSON: {e}")
                    return True  # Still return True as file was copied
            else:
                print(f"      ❌ File appears empty")
                return False
        else:
            print(f"      ❌ Command failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"      ❌ Timeout while copying file")
        return False
    except Exception as e:
        print(f"      ❌ Error: {e}")
        return False

def main():
    """Main function"""
    print("=" * 80)
    print("📋 Copying CNSWPL JSON Files from Production to Local")
    print("=" * 80)
    print()
    
    # Check Railway CLI
    if not check_command(['railway', '--version']):
        print("❌ Railway CLI not found. Please install:")
        print("   npm install -g @railway/cli")
        sys.exit(1)
    
    # Check Railway login
    if not check_command(['railway', 'status']):
        print("❌ Not logged into Railway. Please run:")
        print("   railway login")
        print()
        print("Then link to production:")
        print("   railway link")
        print("   # Select: production environment")
        sys.exit(1)
    
    # Setup paths
    league = "CNSWPL"
    production_path = f"/app/data/leagues/{league}"
    local_path = Path("data/leagues") / league
    
    # Files to copy
    files = [
        "series_stats.json",
        "match_history.json",
        "match_scores.json",
        "schedules.json",
        "players.json",
    ]
    
    print(f"📁 Production: {production_path}")
    print(f"📁 Local: {local_path}")
    print()
    
    # Backup existing files
    print("💾 Backing up existing local files...")
    backup_dir = backup_local_files(local_path, files)
    print(f"   Backup location: {backup_dir}")
    print()
    
    # Copy files
    print("📤 Copying files from production...")
    print()
    
    copied = []
    failed = []
    
    for file in files:
        print(f"   📄 {file}...")
        production_file = f"{production_path}/{file}"
        local_file = local_path / file
        
        if get_file_from_production_via_ssh(production_file, local_file):
            if local_file.exists():
                size = local_file.stat().st_size
                print(f"      ✅ Copied ({size:,} bytes)")
                copied.append(file)
            else:
                print(f"      ❌ File not created")
                failed.append(file)
        else:
            failed.append(file)
        print()
    
    # Summary
    print("=" * 80)
    print("📊 Summary")
    print("=" * 80)
    print(f"✅ Successfully copied: {len(copied)}/{len(files)} files")
    if copied:
        print(f"   - {', '.join(copied)}")
    if failed:
        print(f"❌ Failed: {len(failed)} files")
        print(f"   - {', '.join(failed)}")
    print(f"💾 Backup: {backup_dir}")
    print()
    
    if copied:
        print("✅ Ready for local testing!")
        print()
        print("You can now run:")
        print("   python3 scripts/fix_cnswpl_series_h_stats.py")
        print()
    
    if failed:
        print("⚠️  Some files failed. Possible reasons:")
        print("   - Files don't exist on production")
        print("   - Railway connection issue")
        print("   - Check manually: railway ssh --environment production")
        print()

if __name__ == "__main__":
    main()

