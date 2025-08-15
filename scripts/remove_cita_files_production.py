#!/usr/bin/env python3
"""
Remove CITA Files from Production
=================================

Remove any CITA league files from the data/leagues folder in production.
This completes the CITA cleanup after database removal.
"""

import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

class CITAFileRemover:
    def __init__(self):
        self.base_path = Path(__file__).parent.parent  # Rally root directory
        self.leagues_path = self.base_path / "data" / "leagues"
        self.removed_files = []
        self.removed_dirs = []
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def scan_for_cita_files(self):
        """Scan for any CITA-related files or directories"""
        self.log("🔍 Scanning for CITA files and directories")
        
        cita_items = []
        
        if not self.leagues_path.exists():
            self.log(f"📁 Leagues directory not found at {self.leagues_path}")
            return cita_items
        
        self.log(f"📁 Scanning leagues directory: {self.leagues_path}")
        
        # Check for CITA directory
        cita_dir = self.leagues_path / "CITA"
        if cita_dir.exists():
            cita_items.append({
                'path': cita_dir,
                'type': 'directory',
                'size': self._get_dir_size(cita_dir)
            })
            self.log(f"📂 Found CITA directory: {cita_dir}")
        
        # Check for any files with CITA in the name in other directories
        for item in self.leagues_path.rglob("*"):
            if "cita" in item.name.lower() or "CITA" in item.name:
                if item != cita_dir:  # Don't double-count the directory
                    cita_items.append({
                        'path': item,
                        'type': 'file' if item.is_file() else 'directory',
                        'size': item.stat().st_size if item.is_file() else self._get_dir_size(item)
                    })
                    self.log(f"📄 Found CITA-related item: {item}")
        
        if not cita_items:
            self.log("✅ No CITA files or directories found")
        else:
            self.log(f"📊 Found {len(cita_items)} CITA-related items")
            total_size = sum(item['size'] for item in cita_items)
            self.log(f"📊 Total size: {self._format_size(total_size)}")
        
        return cita_items
    
    def _get_dir_size(self, directory):
        """Calculate total size of directory"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
        except (OSError, IOError):
            pass
        return total_size
    
    def _format_size(self, size_bytes):
        """Format byte size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"
    
    def remove_cita_files(self, cita_items, dry_run=False):
        """Remove CITA files and directories"""
        if dry_run:
            self.log("🔄 DRY RUN MODE - No files will be removed")
        else:
            self.log("🚀 LIVE MODE - Removing CITA files")
        
        if not cita_items:
            self.log("✅ No CITA files to remove")
            return True
        
        success = True
        
        for item in cita_items:
            try:
                path = item['path']
                item_type = item['type']
                size = item['size']
                
                if dry_run:
                    self.log(f"🔄 DRY RUN: Would remove {item_type} {path} ({self._format_size(size)})")
                else:
                    if item_type == 'directory':
                        shutil.rmtree(path)
                        self.removed_dirs.append(str(path))
                        self.log(f"✅ Removed directory: {path} ({self._format_size(size)})")
                    else:
                        path.unlink()
                        self.removed_files.append(str(path))
                        self.log(f"✅ Removed file: {path} ({self._format_size(size)})")
                        
            except Exception as e:
                self.log(f"❌ Failed to remove {path}: {e}", "ERROR")
                success = False
        
        if not dry_run:
            if success:
                total_removed = len(self.removed_files) + len(self.removed_dirs)
                self.log(f"✅ Successfully removed {total_removed} CITA items")
                
                if self.removed_files:
                    self.log(f"📄 Files removed: {len(self.removed_files)}")
                    for file_path in self.removed_files:
                        self.log(f"  - {file_path}")
                
                if self.removed_dirs:
                    self.log(f"📂 Directories removed: {len(self.removed_dirs)}")
                    for dir_path in self.removed_dirs:
                        self.log(f"  - {dir_path}")
            else:
                self.log("⚠️ Some CITA files could not be removed", "WARNING")
        
        return success
    
    def verify_removal(self):
        """Verify that CITA files have been removed"""
        self.log("🔍 Verifying CITA file removal")
        
        remaining_items = self.scan_for_cita_files()
        
        if not remaining_items:
            self.log("✅ All CITA files successfully removed!")
            return True
        else:
            self.log(f"❌ {len(remaining_items)} CITA items still remain", "ERROR")
            for item in remaining_items:
                self.log(f"  - {item['type']}: {item['path']}")
            return False
    
    def list_remaining_leagues(self):
        """List the remaining league directories"""
        self.log("📊 Remaining league directories:")
        
        if not self.leagues_path.exists():
            self.log("📁 No leagues directory found")
            return
        
        league_dirs = [d for d in self.leagues_path.iterdir() if d.is_dir()]
        
        for league_dir in sorted(league_dirs):
            # Count files in directory
            file_count = sum(1 for _ in league_dir.rglob("*") if _.is_file())
            dir_size = self._get_dir_size(league_dir)
            self.log(f"  📂 {league_dir.name}: {file_count} files ({self._format_size(dir_size)})")
    
    def run_removal(self, dry_run=False):
        """Run the complete CITA file removal process"""
        if dry_run:
            self.log("🔄 STARTING CITA FILE ANALYSIS (DRY RUN)")
        else:
            self.log("🚀 STARTING CITA FILE REMOVAL (LIVE MODE)")
        
        try:
            # Scan for CITA files
            cita_items = self.scan_for_cita_files()
            
            # Remove files
            success = self.remove_cita_files(cita_items, dry_run)
            
            if not dry_run:
                # Verify removal
                verification_success = self.verify_removal()
                
                # List remaining leagues
                self.list_remaining_leagues()
                
                if success and verification_success:
                    self.log("✅ CITA FILE REMOVAL COMPLETED SUCCESSFULLY")
                else:
                    self.log("⚠️ CITA FILE REMOVAL PARTIALLY COMPLETED", "WARNING")
                
                return success and verification_success
            else:
                self.log("🔄 DRY RUN COMPLETED - Review items above")
                return True
                
        except Exception as e:
            self.log(f"❌ File removal failed with error: {e}", "ERROR")
            return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Remove CITA files from production')
    parser.add_argument('--dry-run', action='store_true', help='Analyze without removing files')
    args = parser.parse_args()
    
    print("🗑️  PRODUCTION CITA FILE REMOVER")
    print("=" * 50)
    
    remover = CITAFileRemover()
    success = remover.run_removal(dry_run=args.dry_run)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
