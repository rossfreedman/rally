import os
import shutil
from datetime import datetime
import sys

def create_backup():
    # Get the parent directory of the current project
    current_dir = os.path.abspath('.')
    parent_dir = os.path.dirname(current_dir)
    
    # Create timestamp for backup folder
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Create backup directory in the sibling rally_backups folder
    backup_dir = os.path.join(parent_dir, 'rally_backups', f'rally_backup_{timestamp}')
    os.makedirs(backup_dir, exist_ok=True)
    
    # Directories and files to exclude
    exclude = {'.venv', '__pycache__', '.DS_Store'}
    
    # Copy files and directories
    for item in os.listdir('.'):
        if item in exclude:
            continue
            
        source = os.path.join('.', item)
        destination = os.path.join(backup_dir, item)
        
        try:
            if os.path.isdir(source):
                shutil.copytree(source, destination, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'))
            else:
                shutil.copy2(source, destination)
            print(f"Backed up: {item}")
        except Exception as e:
            print(f"Error backing up {item}: {str(e)}")
    
    print(f"\nBackup completed successfully in: {backup_dir}")

if __name__ == "__main__":
    try:
        create_backup()
    except Exception as e:
        print(f"Backup failed: {str(e)}")
        sys.exit(1)