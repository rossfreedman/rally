#!/usr/bin/env python3
"""
JSON Backup Manager for Rally Scrapers
======================================

Centralized backup functionality for JSON files before scraper updates.
Ensures data integrity and provides recovery capabilities.
"""

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

class JSONBackupManager:
    """Manages backup operations for JSON files used in scraping."""
    
    def __init__(self, backup_base_dir: str = "data/etl/scrapers/helpers/temp_jsons/backups/backup_jsons"):
        """
        Initialize the backup manager.
        
        Args:
            backup_base_dir: Base directory for all JSON backups
        """
        self.backup_base_dir = Path(backup_base_dir)
        self.backup_base_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timestamp for this session
        self.session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_backup_dir = self.backup_base_dir / f"session_{self.session_timestamp}"
        
        logger.info(f"📦 JSON Backup Manager initialized")
        logger.info(f"   Backup directory: {self.backup_base_dir}")
        logger.info(f"   Session directory: {self.session_backup_dir}")
    
    def backup_file(self, source_file: str, backup_reason: str = "scraper_update") -> Optional[str]:
        """
        Create a backup of a single JSON file.
        
        Args:
            source_file: Path to the source JSON file to backup
            backup_reason: Reason for the backup (for logging)
            
        Returns:
            str: Path to the backup file, or None if backup failed
        """
        source_path = Path(source_file)
        
        if not source_path.exists():
            logger.debug(f"⚠️ Source file doesn't exist, skipping backup: {source_file}")
            return None
        
        try:
            # Create session backup directory if it doesn't exist
            self.session_backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Create relative path structure in backup
            # Convert data/leagues/APTA_CHICAGO/match_history.json to APTA_CHICAGO/match_history.json
            if "data/leagues/" in str(source_path):
                relative_parts = source_path.parts[source_path.parts.index("leagues") + 1:]
                backup_relative_path = Path(*relative_parts)
            else:
                backup_relative_path = source_path.name
            
            # Create backup file path with timestamp
            backup_file_path = self.session_backup_dir / backup_relative_path
            backup_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy the file
            shutil.copy2(source_path, backup_file_path)
            
            # Get file size for logging
            file_size = source_path.stat().st_size
            size_mb = file_size / (1024 * 1024)
            
            logger.info(f"📦 Backed up: {source_path.name} ({size_mb:.1f}MB)")
            logger.debug(f"   From: {source_file}")
            logger.debug(f"   To: {backup_file_path}")
            logger.debug(f"   Reason: {backup_reason}")
            
            return str(backup_file_path)
            
        except Exception as e:
            logger.error(f"❌ Failed to backup {source_file}: {e}")
            return None
    
    def backup_league_files(self, league_dir: str, files_to_backup: List[str] = None) -> Dict[str, Optional[str]]:
        """
        Backup all JSON files for a specific league.
        
        Args:
            league_dir: Path to league directory (e.g., "data/leagues/APTA_CHICAGO")
            files_to_backup: List of specific files to backup, or None for default set
            
        Returns:
            Dict mapping original file paths to backup paths (None if backup failed)
        """
        if files_to_backup is None:
            files_to_backup = [
                "match_history.json",
                "players.json", 
                "schedules.json",
                "series_stats.json",
                "player_history.json"
            ]
        
        league_path = Path(league_dir)
        backup_results = {}
        
        logger.info(f"📦 Backing up league files: {league_path.name}")
        
        for filename in files_to_backup:
            file_path = league_path / filename
            backup_path = self.backup_file(str(file_path), f"league_update_{league_path.name}")
            backup_results[str(file_path)] = backup_path
        
        successful_backups = sum(1 for path in backup_results.values() if path is not None)
        logger.info(f"✅ League backup complete: {successful_backups}/{len(files_to_backup)} files backed up")
        
        return backup_results
    
    def backup_all_leagues(self) -> Dict[str, Dict[str, Optional[str]]]:
        """
        Backup JSON files for all leagues.
        
        Returns:
            Dict mapping league names to their backup results
        """
        leagues_dir = Path("data/leagues")
        all_backup_results = {}
        
        if not leagues_dir.exists():
            logger.warning(f"⚠️ Leagues directory not found: {leagues_dir}")
            return {}
        
        logger.info("📦 Starting backup of all league JSON files...")
        
        # Get all league directories (exclude 'all' as it's consolidated data)
        league_dirs = [d for d in leagues_dir.iterdir() 
                      if d.is_dir() and d.name != "all" and not d.name.startswith(".")]
        
        for league_dir in league_dirs:
            logger.info(f"📦 Processing league: {league_dir.name}")
            backup_results = self.backup_league_files(str(league_dir))
            all_backup_results[league_dir.name] = backup_results
        
        total_files = sum(len(results) for results in all_backup_results.values())
        successful_files = sum(
            sum(1 for path in results.values() if path is not None)
            for results in all_backup_results.values()
        )
        
        logger.info(f"🎉 All-league backup complete: {successful_files}/{total_files} files backed up")
        
        return all_backup_results
    
    def get_backup_summary(self) -> Dict[str, Any]:
        """
        Get summary of current session's backups.
        
        Returns:
            Dict with backup summary information
        """
        if not self.session_backup_dir.exists():
            return {
                "session_timestamp": self.session_timestamp,
                "total_files": 0,
                "total_size_mb": 0.0,
                "leagues_backed_up": [],
                "backup_directory": str(self.session_backup_dir)
            }
        
        total_files = 0
        total_size = 0
        leagues_backed_up = set()
        
        for backup_file in self.session_backup_dir.rglob("*.json"):
            total_files += 1
            total_size += backup_file.stat().st_size
            
            # Extract league name from path
            if len(backup_file.parts) > 1:
                leagues_backed_up.add(backup_file.parts[-2])  # Parent directory
        
        return {
            "session_timestamp": self.session_timestamp,
            "total_files": total_files,
            "total_size_mb": total_size / (1024 * 1024),
            "leagues_backed_up": sorted(list(leagues_backed_up)),
            "backup_directory": str(self.session_backup_dir)
        }
    
    def cleanup_old_backups(self, keep_days: int = 30) -> int:
        """
        Clean up backup sessions older than specified days.
        
        Args:
            keep_days: Number of days of backups to retain
            
        Returns:
            int: Number of backup sessions removed
        """
        cutoff_time = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)
        removed_count = 0
        
        logger.info(f"🧹 Cleaning up backup sessions older than {keep_days} days...")
        
        for session_dir in self.backup_base_dir.glob("session_*"):
            if session_dir.is_dir():
                dir_mtime = session_dir.stat().st_mtime
                if dir_mtime < cutoff_time:
                    try:
                        shutil.rmtree(session_dir)
                        removed_count += 1
                        logger.debug(f"   Removed old backup: {session_dir.name}")
                    except Exception as e:
                        logger.warning(f"   Failed to remove {session_dir.name}: {e}")
        
        if removed_count > 0:
            logger.info(f"✅ Cleanup complete: {removed_count} old backup sessions removed")
        else:
            logger.info("✅ Cleanup complete: no old backups to remove")
        
        return removed_count

def create_backup_manager() -> JSONBackupManager:
    """
    Factory function to create a backup manager instance.
    
    Returns:
        JSONBackupManager: Configured backup manager
    """
    return JSONBackupManager()

def backup_before_scraping(league_name: str = None) -> JSONBackupManager:
    """
    Convenience function to backup files before scraping operations.
    
    Args:
        league_name: Specific league to backup, or None for all leagues
        
    Returns:
        JSONBackupManager: The backup manager used
    """
    backup_manager = create_backup_manager()
    
    if league_name:
        league_dir = f"data/leagues/{league_name.upper()}"
        backup_manager.backup_league_files(league_dir)
    else:
        backup_manager.backup_all_leagues()
    
    # Log backup summary
    summary = backup_manager.get_backup_summary()
    logger.info(f"📊 Backup Summary:")
    logger.info(f"   Files backed up: {summary['total_files']}")
    logger.info(f"   Total size: {summary['total_size_mb']:.1f}MB")
    logger.info(f"   Leagues: {', '.join(summary['leagues_backed_up'])}")
    
    return backup_manager

if __name__ == "__main__":
    # Test the backup manager
    print("🧪 Testing JSON Backup Manager")
    print("=" * 50)
    
    # Test backing up all leagues
    backup_manager = backup_before_scraping()
    
    # Show summary
    summary = backup_manager.get_backup_summary()
    print(f"\n📊 Test Results:")
    print(f"  Session: {summary['session_timestamp']}")
    print(f"  Files: {summary['total_files']}")
    print(f"  Size: {summary['total_size_mb']:.1f}MB")
    print(f"  Leagues: {summary['leagues_backed_up']}")
    print(f"  Directory: {summary['backup_directory']}")
    
    print("\n✅ JSON Backup Manager test completed!")