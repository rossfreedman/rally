#!/usr/bin/env python3
"""
Copy JSON Files from Production to Local (CNSWPL and APTA Chicago)

This script copies JSON files from Railway production to local for both
CNSWPL and APTA_CHICAGO leagues.

Usage:
    python3 scripts/copy_production_json_files.py [--league CNSWPL|APTA_CHICAGO|all]
"""

import os
import sys
import subprocess
import json
import shutil
import argparse
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

def get_file_from_production(filepath, output_path):
    """Get a file from production using Railway CLI"""
    try:
        # Use railway run with the service name
        cmd = [
            'railway', 'run',
            '--service', 'Rally PRODUCTION App',
            'cat', filepath
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,  # Increase timeout for large files
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
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            print(f"      ❌ Command failed: {error_msg}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"      ❌ Timeout while copying file")
        return False
    except Exception as e:
        print(f"      ❌ Error: {e}")
        return False

def copy_league_files(league_config):
    """Copy files for a specific league"""
    league_name = league_config['name']
    league_dir = league_config['dir']
    files = league_config['files']
    
    print(f"\n{'=' * 80}")
    print(f"📋 {league_name}")
    print(f"{'=' * 80}")
    print()
    
    production_path = f"/app/data/leagues/{league_dir}"
    local_path = Path("data/leagues") / league_dir
    
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
        
        if get_file_from_production(production_file, local_file):
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
    
    return {
        'league': league_name,
        'copied': copied,
        'failed': failed,
        'backup_dir': backup_dir
    }

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Copy JSON files from production to local')
    parser.add_argument(
        '--league',
        choices=['CNSWPL', 'APTA_CHICAGO', 'all'],
        default='all',
        help='League to copy (default: all)'
    )
    args = parser.parse_args()
    
    print("=" * 80)
    print("📋 Copying JSON Files from Production to Local")
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
    
    # Define league configurations (using actual production filenames)
    leagues_config = {
        'CNSWPL': {
            'name': 'CNSWPL',
            'dir': 'CNSWPL',
            'files': [
                'series_stats.json',  # Created by scraper, needed for import
                'cnswpl_match_history_2024_2025.json',
                'cnswpl_players_career_stats.json',
            ]
        },
        'APTA_CHICAGO': {
            'name': 'APTA Chicago',
            'dir': 'APTA_CHICAGO',
            'files': [
                'series_stats.json',  # Created by scraper, needed for import
                'match_history_2024_2025.json',
                'player_history.json',
                'players_career_stats.json',
            ]
        }
    }
    
    # Note: These files are generated by scrapers and should exist after scraper runs:
    # - series_stats.json (created by scrape_stats.py, used by import_stats.py)
    # The following may not exist on production:
    # - match_scores.json (generated during import, might not persist)
    # - schedules.json (generated during import, might not persist)
    # - players.json (generated during import, might not persist)
    
    # Determine which leagues to process
    if args.league == 'all':
        leagues_to_process = list(leagues_config.keys())
    else:
        leagues_to_process = [args.league]
    
    # Process each league
    results = []
    for league_key in leagues_to_process:
        if league_key in leagues_config:
            result = copy_league_files(leagues_config[league_key])
            results.append(result)
        else:
            print(f"⚠️  Unknown league: {league_key}")
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 Summary")
    print("=" * 80)
    print()
    
    total_copied = 0
    total_failed = 0
    
    for result in results:
        league = result['league']
        copied_count = len(result['copied'])
        failed_count = len(result['failed'])
        total_copied += copied_count
        total_failed += failed_count
        
        print(f"📋 {league}:")
        print(f"   ✅ Copied: {copied_count}/{copied_count + failed_count} files")
        if result['copied']:
            print(f"      - {', '.join(result['copied'])}")
        if result['failed']:
            print(f"   ❌ Failed: {', '.join(result['failed'])}")
        print(f"   💾 Backup: {result['backup_dir']}")
        print()
    
    print("=" * 80)
    print(f"✅ Total copied: {total_copied} files")
    if total_failed > 0:
        print(f"❌ Total failed: {total_failed} files")
    print("=" * 80)
    print()
    
    if total_copied > 0:
        print("✅ Files are ready for local testing!")
        print()
        if 'CNSWPL' in [r['league'] for r in results]:
            print("You can now run:")
            print("   python3 scripts/fix_cnswpl_series_h_stats.py")
    
    if total_failed > 0:
        print()
        print("⚠️  Some files failed. Possible reasons:")
        print("   - Files don't exist on production")
        print("   - Railway connection issue")
        print("   - Check manually: railway ssh --environment production")
        print()

if __name__ == "__main__":
    main()

