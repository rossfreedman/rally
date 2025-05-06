#!/usr/bin/env python3

import os
import shutil
from datetime import datetime
import sys

def create_backup():
    try:
        # Get current directory (assuming script is in rally folder)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        
        # Create backup directory if it doesn't exist
        backup_dir = os.path.join(parent_dir, 'rally_backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Get current timestamp in desired format (YYYY_MM_DD_HHMM)
        timestamp = datetime.now().strftime('%Y_%m_%d_%I%M')
        
        # Create backup folder name
        backup_name = f'rally_{timestamp}'
        backup_path = os.path.join(backup_dir, backup_name)
        
        # Create the backup
        print(f"\nCreating backup: {backup_name}")
        print("Source directory:", current_dir)
        print("Backup directory:", backup_path)
        
        # Copy the entire directory
        shutil.copytree(current_dir, backup_path, dirs_exist_ok=True)
        
        print("\n✅ Backup completed successfully!")
        print(f"Backup location: {backup_path}")
        
        # List the contents of the backup directory
        backups = [d for d in os.listdir(backup_dir) 
                  if os.path.isdir(os.path.join(backup_dir, d)) and d.startswith('rally_')]
        backups.sort(reverse=True)
        
        print(f"\nExisting backups ({len(backups)}):")
        for backup in backups[:5]:  # Show 5 most recent backups
            backup_time = os.path.getmtime(os.path.join(backup_dir, backup))
            backup_time_str = datetime.fromtimestamp(backup_time).strftime('%Y-%m-%d %I:%M %p')
            print(f"- {backup} (created: {backup_time_str})")
        
        if len(backups) > 5:
            print(f"... and {len(backups) - 5} more")
        
    except Exception as e:
        print(f"\n❌ Error creating backup: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    create_backup()