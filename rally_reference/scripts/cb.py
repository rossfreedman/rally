#!/usr/bin/env python3
"""
Rally Codebase Backup Utility

This script creates a backup of the Rally codebase in a sibling directory named 'rally_backups'.
Backups are stored with timestamps and can be automatically cleaned up based on age.

Usage:
    python3 cb.py                          # Create a backup with default settings
    python3 cb.py --max-backups 5          # Keep only 5 most recent backups
    python3 cb.py --exclude __pycache__ .venv node_modules  # Exclude specific directories
    python3 cb.py --list                   # List existing backups without creating a new one
    python3 cb.py --no-confirm             # Skip confirmation before deleting old backups
    
Author: Rally Team
"""

import os
import shutil
from datetime import datetime
import sys
import argparse
import time

def list_backups():
    """List all existing backups without creating a new one"""
    try:
        # Get current directory (script is in rally/scripts/)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Get rally root directory (parent of scripts directory)
        rally_root = os.path.dirname(current_dir)
        
        # Get parent directory (where rally and rally_backups should both be located)
        parent_dir = os.path.dirname(rally_root)
        
        # Check if backup directory exists
        backup_dir = os.path.join(parent_dir, 'rally_backups')
        if not os.path.exists(backup_dir):
            print("\n⚠️  No backups found. Backup directory does not exist.")
            return
        
        # List the contents of the backup directory
        backups = [d for d in os.listdir(backup_dir) 
                  if os.path.isdir(os.path.join(backup_dir, d)) and d.startswith('rally_')]
                  
        if not backups:
            print("\n⚠️  No backups found in the backup directory.")
            return
            
        backups.sort(reverse=True)
        
        print(f"\n📋 Existing backups ({len(backups)}):")
        total_size = 0
        
        for i, backup in enumerate(backups, 1):
            backup_path = os.path.join(backup_dir, backup)
            backup_time = os.path.getmtime(backup_path)
            backup_time_str = datetime.fromtimestamp(backup_time).strftime('%Y-%m-%d %I:%M %p')
            backup_size = get_dir_size(backup_path)
            total_size += backup_size
            backup_size_mb = backup_size / (1024 * 1024)
            
            print(f"{i}. {backup} (created: {backup_time_str}, size: {backup_size_mb:.2f} MB)")
        
        # Calculate total size
        total_size_mb = total_size / (1024 * 1024)
        total_size_gb = total_size_mb / 1024
        
        print(f"\nTotal space used: {total_size_mb:.2f} MB ({total_size_gb:.2f} GB)")
        print(f"Backup location: {backup_dir}")
        
    except Exception as e:
        print(f"\n❌ Error listing backups: {str(e)}")
        sys.exit(1)

def create_backup(max_backups=10, exclude_patterns=None, no_confirm=False):
    """
    Create a backup of the current codebase
    
    Args:
        max_backups (int): Maximum number of backups to keep
        exclude_patterns (list): List of patterns to exclude from backup
        no_confirm (bool): Skip confirmation before deleting old backups
    """
    try:
        start_time = time.time()
        
        # Get current directory (script is in rally/scripts/)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Get rally root directory (parent of scripts directory)
        rally_root = os.path.dirname(current_dir)
        rally_dir_name = os.path.basename(rally_root)
        
        # Get parent directory (where rally and rally_backups should both be located)
        parent_dir = os.path.dirname(rally_root)
        
        # Create backup directory as a sibling to rally folder
        backup_dir = os.path.join(parent_dir, 'rally_backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Get current timestamp in desired format (YYYY_MM_DD_HHMM)
        timestamp = datetime.now().strftime('%Y_%m_%d_%H%M')
        
        # Create backup folder name
        backup_name = f'rally_backup_{timestamp}'
        backup_path = os.path.join(backup_dir, backup_name)
        
        # Default exclude patterns if none provided
        if exclude_patterns is None:
            exclude_patterns = [
                '__pycache__', 
                '.git', 
                '.venv', 
                'node_modules',
                '*.pyc', 
                '.DS_Store',
                '*.log'
            ]
        
        # Create the backup
        print(f"\n🔄 Creating backup: {backup_name}")
        print(f"Rally folder: {rally_root}")
        print(f"Backup destination: {backup_path}")
        print(f"Excluding patterns: {exclude_patterns}")
        
        # Custom copy function to show progress
        def copy_with_progress(src, dst, ignore=None):
            if os.path.isdir(src):
                if not os.path.exists(dst):
                    os.makedirs(dst)
                    print(f"📁 Created directory: {os.path.relpath(dst, backup_path)}")
                files = os.listdir(src)
                if ignore is not None:
                    ignored_names = ignore(src, files)
                    files = [f for f in files if f not in ignored_names]
                for f in files:
                    s = os.path.join(src, f)
                    d = os.path.join(dst, f)
                    if os.path.isdir(s):
                        copy_with_progress(s, d, ignore)
                    else:
                        shutil.copy2(s, d)
                        rel_path = os.path.relpath(d, backup_path)
                        print(f"📄 Copied: {rel_path}")
            else:
                shutil.copy2(src, dst)
                rel_path = os.path.relpath(dst, backup_path)
                print(f"📄 Copied: {rel_path}")

        # Custom ignore function to ignore specified directories
        def ignore_patterns(path, names):
            ignored = set()
            for name in names:
                # Check if the name matches any of the exclude patterns
                for pattern in exclude_patterns:
                    if pattern.startswith('*'):
                        # Handle file extension patterns
                        if name.endswith(pattern[1:]):
                            ignored.add(name)
                    elif name == pattern:
                        # Handle exact match patterns
                        ignored.add(name)
            return ignored
        
        # Copy the entire directory with progress
        copy_with_progress(rally_root, backup_path, ignore=ignore_patterns)
        
        # Calculate the backup size
        backup_size = get_dir_size(backup_path)
        backup_size_mb = backup_size / (1024 * 1024)
        
        # Calculate the time taken
        elapsed_time = time.time() - start_time
        
        print(f"\n✅ Backup completed successfully!")
        print(f"Backup location: {backup_path}")
        print(f"Backup size: {backup_size_mb:.2f} MB")
        print(f"Time taken: {elapsed_time:.2f} seconds")
        
        # Cleanup old backups if needed
        cleanup_old_backups(backup_dir, max_backups, no_confirm)
        
        # List the contents of the backup directory
        backups = [d for d in os.listdir(backup_dir) 
                  if os.path.isdir(os.path.join(backup_dir, d)) and d.startswith('rally_')]
        backups.sort(reverse=True)
        
        print(f"\nExisting backups ({len(backups)}):")
        for backup in backups[:5]:  # Show 5 most recent backups
            backup_time = os.path.getmtime(os.path.join(backup_dir, backup))
            backup_time_str = datetime.fromtimestamp(backup_time).strftime('%Y-%m-%d %I:%M %p')
            backup_path = os.path.join(backup_dir, backup)
            backup_size = get_dir_size(backup_path)
            backup_size_mb = backup_size / (1024 * 1024)
            print(f"- {backup} (created: {backup_time_str}, size: {backup_size_mb:.2f} MB)")
        
        if len(backups) > 5:
            print(f"... and {len(backups) - 5} more")
        
        return backup_path
    
    except Exception as e:
        print(f"\n❌ Error creating backup: {str(e)}")
        sys.exit(1)

def cleanup_old_backups(backup_dir, max_backups, no_confirm=False):
    """
    Clean up old backups, keeping only the most recent ones
    
    Args:
        backup_dir (str): Backup directory path
        max_backups (int): Maximum number of backups to keep
        no_confirm (bool): Skip confirmation before deleting
    """
    try:
        # List all backup directories
        backups = [d for d in os.listdir(backup_dir) 
                  if os.path.isdir(os.path.join(backup_dir, d)) and d.startswith('rally_')]
        
        # Sort by modification time (newest first)
        backups.sort(key=lambda x: os.path.getmtime(os.path.join(backup_dir, x)), reverse=True)
        
        # If we have more backups than the maximum, delete the oldest ones
        if len(backups) > max_backups:
            backups_to_delete = backups[max_backups:]
            print(f"\nFound {len(backups_to_delete)} older backups that can be removed.")
            
            # Get confirmation before deleting unless --no-confirm flag is set
            if not no_confirm:
                confirm = input(f"Delete {len(backups_to_delete)} old backup(s)? [y/N]: ")
                if confirm.lower() != 'y':
                    print("Skipping cleanup of old backups.")
                    return
            
            print(f"\nCleaning up {len(backups_to_delete)} old backups (keeping {max_backups} most recent)...")
            
            for backup in backups_to_delete:
                backup_path = os.path.join(backup_dir, backup)
                print(f"Deleting old backup: {backup}")
                shutil.rmtree(backup_path)
                
            print(f"Cleanup complete. {len(backups_to_delete)} old backups removed.")
    
    except Exception as e:
        print(f"Warning: Error during cleanup: {str(e)}")

def get_dir_size(path):
    """
    Calculate the total size of a directory in bytes
    
    Args:
        path (str): Directory path
        
    Returns:
        int: Directory size in bytes
    """
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.exists(fp):
                total_size += os.path.getsize(fp)
    return total_size

def main():
    """Main entry point for backup script"""
    parser = argparse.ArgumentParser(description='Create a backup of the rally codebase')
    parser.add_argument('--max-backups', type=int, default=10,
                        help='Maximum number of backups to keep (default: 10)')
    parser.add_argument('--exclude', type=str, nargs='+',
                        help='Patterns to exclude from backup (space separated)')
    parser.add_argument('--list', action='store_true',
                        help='List existing backups without creating a new one')
    parser.add_argument('--no-confirm', action='store_true',
                        help='Skip confirmation before deleting old backups')
    args = parser.parse_args()
    
    if args.list:
        list_backups()
    else:
        create_backup(max_backups=args.max_backups, exclude_patterns=args.exclude, no_confirm=args.no_confirm)

if __name__ == "__main__":
    main()