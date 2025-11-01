#!/usr/bin/env python3
"""
League Directory Manager for Rally Scrapers
==========================================

Standardizes league directory naming and prevents redundant directories.
Ensures consistent mapping from league subdomains to directory names.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Standard league directory mapping
# Maps subdomain inputs to consistent directory names
LEAGUE_DIRECTORY_MAPPING = {
    # APTA Chicago variants
    "aptachicago": "APTA_CHICAGO",
    "apta_chicago": "APTA_CHICAGO", 
    "apta": "APTA_CHICAGO",
    "chicago": "APTA_CHICAGO",
    
    # NSTF variants
    "nstf": "NSTF",
    
    # CNSWPL variants
    "cnswpl": "CNSWPL",
    "cns": "CNSWPL",
    

}

# Reverse mapping for lookups
DIRECTORY_TO_SUBDOMAIN = {
    "APTA_CHICAGO": "aptachicago",
    "NSTF": "nstf", 
    "CNSWPL": "cnswpl",


}

class LeagueDirectoryManager:
    """Manages consistent league directory naming and creation."""
    
    def __init__(self, base_leagues_dir: str = None):
        """
        Initialize the directory manager.
        
        Args:
            base_leagues_dir: Base directory for all league data. 
                             If None, checks CNSWPL_CRON_VARIABLE env var, 
                             otherwise defaults to "data/leagues"
        """
        if base_leagues_dir is None:
            # Check for environment variable (for Railway volumes, etc.)
            base_leagues_dir = os.getenv("CNSWPL_CRON_VARIABLE", "data/leagues")
        
        self.base_leagues_dir = Path(base_leagues_dir)
        try:
            self.base_leagues_dir.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError) as e:
            # Log warning but don't crash - directory may exist or permissions issue
            logger.warning(f"⚠️ Could not create directory {self.base_leagues_dir}: {e}")
            # Continue with existing directory if it exists
            if not self.base_leagues_dir.exists():
                # Fallback to relative path if absolute path fails
                logger.warning(f"⚠️ Falling back to relative path: data/leagues")
                self.base_leagues_dir = Path("data/leagues")
                self.base_leagues_dir.mkdir(parents=True, exist_ok=True)
        
    def get_standard_directory_name(self, league_input: str) -> str:
        """
        Get the standardized directory name for a league.
        
        Args:
            league_input: Input league name/subdomain (e.g., "aptachicago", "APTACHICAGO")
            
        Returns:
            str: Standardized directory name (e.g., "APTA_CHICAGO")
        """
        # Normalize input to lowercase
        normalized_input = league_input.lower().strip()
        
        # Check direct mapping first
        if normalized_input in LEAGUE_DIRECTORY_MAPPING:
            return LEAGUE_DIRECTORY_MAPPING[normalized_input]
        
        # Handle legacy cases where input might already be in directory format
        for dir_name in DIRECTORY_TO_SUBDOMAIN.keys():
            if normalized_input == dir_name.lower():
                return dir_name
        
        # Fallback: use uppercase of input (for unknown leagues)
        logger.warning(f"⚠️ Unknown league '{league_input}', using fallback directory name")
        return league_input.upper()
    
    def get_league_directory_path(self, league_input: str) -> Path:
        """
        Get the full path to a league's data directory.
        
        Args:
            league_input: League name/subdomain
            
        Returns:
            Path: Full path to league directory
        """
        dir_name = self.get_standard_directory_name(league_input)
        return self.base_leagues_dir / dir_name
    
    def create_league_directory(self, league_input: str) -> Path:
        """
        Create a league directory if it doesn't exist.
        
        Args:
            league_input: League name/subdomain
            
        Returns:
            Path: Path to the created directory
        """
        league_dir = self.get_league_directory_path(league_input)
        league_dir.mkdir(parents=True, exist_ok=True)
        
        logger.debug(f"📁 League directory: {league_input} → {league_dir}")
        return league_dir
    
    def get_file_path(self, league_input: str, filename: str) -> Path:
        """
        Get the full path to a file within a league directory.
        
        Args:
            league_input: League name/subdomain
            filename: Name of the file (e.g., "match_history.json")
            
        Returns:
            Path: Full path to the file
        """
        league_dir = self.create_league_directory(league_input)
        return league_dir / filename
    
    def migrate_legacy_directory(self, old_dir_name: str, new_dir_name: str = None) -> bool:
        """
        Migrate data from a legacy directory to the standardized name.
        
        Args:
            old_dir_name: Old directory name (e.g., "APTACHICAGO")
            new_dir_name: New directory name (auto-determined if None)
            
        Returns:
            bool: True if migration was performed
        """
        old_dir = self.base_leagues_dir / old_dir_name
        
        if not old_dir.exists():
            logger.debug(f"📁 Legacy directory doesn't exist: {old_dir}")
            return False
        
        # Determine new directory name
        if new_dir_name is None:
            # Try to map the old name to a standard name
            new_dir_name = self.get_standard_directory_name(old_dir_name)
        
        new_dir = self.base_leagues_dir / new_dir_name
        
        # Skip if they're the same
        if old_dir == new_dir:
            logger.debug(f"📁 Directory names are the same, no migration needed: {old_dir}")
            return False
        
        logger.info(f"🔄 Migrating legacy directory: {old_dir_name} → {new_dir_name}")
        
        try:
            # Create new directory if it doesn't exist
            new_dir.mkdir(parents=True, exist_ok=True)
            
            # Move all files from old to new directory
            files_moved = 0
            for file_path in old_dir.iterdir():
                if file_path.is_file():
                    new_file_path = new_dir / file_path.name
                    
                    # If file exists in new location, merge or skip
                    if new_file_path.exists():
                        logger.warning(f"⚠️ File already exists in target: {file_path.name}")
                        # For JSON files, we could implement merging logic here
                        # For now, skip to avoid data loss
                        continue
                    
                    # Move the file
                    file_path.rename(new_file_path)
                    files_moved += 1
                    logger.debug(f"   Moved: {file_path.name}")
                elif file_path.is_dir():
                    # Recursively move subdirectories
                    new_subdir = new_dir / file_path.name
                    file_path.rename(new_subdir)
                    logger.debug(f"   Moved directory: {file_path.name}")
            
            # Remove old directory if empty
            if not any(old_dir.iterdir()):
                old_dir.rmdir()
                logger.info(f"✅ Removed empty legacy directory: {old_dir_name}")
            else:
                logger.warning(f"⚠️ Legacy directory not empty, keeping: {old_dir_name}")
            
            logger.info(f"✅ Migration complete: {files_moved} files moved to {new_dir_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            return False
    
    def audit_directories(self) -> Dict[str, Dict]:
        """
        Audit all league directories and identify issues.
        
        Returns:
            Dict: Audit results with directories and recommendations
        """
        audit_results = {
            "standard_directories": [],
            "legacy_directories": [],
            "unknown_directories": [],
            "recommendations": []
        }
        
        if not self.base_leagues_dir.exists():
            return audit_results
        
        for dir_path in self.base_leagues_dir.iterdir():
            if not dir_path.is_dir() or dir_path.name.startswith('.'):
                continue
            
            dir_name = dir_path.name
            
            # Check if it's a standard directory
            if dir_name in DIRECTORY_TO_SUBDOMAIN:
                audit_results["standard_directories"].append({
                    "name": dir_name,
                    "path": str(dir_path),
                    "subdomain": DIRECTORY_TO_SUBDOMAIN[dir_name]
                })
            
            # Check if it's a known legacy directory
            elif dir_name.lower() in ["aptachicago"]:
                standard_name = self.get_standard_directory_name(dir_name)
                audit_results["legacy_directories"].append({
                    "name": dir_name,
                    "path": str(dir_path),
                    "standard_name": standard_name
                })
                audit_results["recommendations"].append(
                    f"Migrate {dir_name} → {standard_name}"
                )
            
            # Unknown directories
            else:
                audit_results["unknown_directories"].append({
                    "name": dir_name,
                    "path": str(dir_path)
                })
        
        return audit_results
    
    def fix_all_legacy_directories(self) -> int:
        """
        Automatically fix all detected legacy directories.
        
        Returns:
            int: Number of directories fixed
        """
        audit = self.audit_directories()
        fixed_count = 0
        
        for legacy_dir in audit["legacy_directories"]:
            if self.migrate_legacy_directory(legacy_dir["name"], legacy_dir["standard_name"]):
                fixed_count += 1
        
        return fixed_count

# Global instance for convenience
_directory_manager = None

def get_directory_manager() -> LeagueDirectoryManager:
    """Get the global directory manager instance."""
    global _directory_manager
    if _directory_manager is None:
        _directory_manager = LeagueDirectoryManager()
    return _directory_manager

def get_league_directory_path(league_input: str) -> str:
    """
    Convenience function to get a league directory path.
    
    Args:
        league_input: League name/subdomain
        
    Returns:
        str: Path to league directory
    """
    manager = get_directory_manager()
    return str(manager.get_league_directory_path(league_input))

def get_league_file_path(league_input: str, filename: str) -> str:
    """
    Convenience function to get a league file path.
    
    Args:
        league_input: League name/subdomain
        filename: Name of the file
        
    Returns:
        str: Path to the file
    """
    manager = get_directory_manager()
    return str(manager.get_file_path(league_input, filename))

def build_league_data_dir(league_id: str) -> str:
    """
    Legacy compatibility function for build_league_data_dir.
    
    Args:
        league_id: League identifier
        
    Returns:
        str: Path to league directory
    """
    return get_league_directory_path(league_id)

if __name__ == "__main__":
    # Test the directory manager
    print("🧪 Testing League Directory Manager")
    print("=" * 50)
    
    manager = LeagueDirectoryManager()
    
    # Test standardization
    test_inputs = ["aptachicago", "APTACHICAGO", "apta", "nstf", "NSTF"]
    
    print("\n📁 Directory Standardization:")
    for test_input in test_inputs:
        standard_name = manager.get_standard_directory_name(test_input)
        print(f"  {test_input:15} → {standard_name}")
    
    # Test audit
    print("\n🔍 Directory Audit:")
    audit = manager.audit_directories()
    
    print(f"  Standard directories: {len(audit['standard_directories'])}")
    for dir_info in audit['standard_directories']:
        print(f"    ✅ {dir_info['name']} ({dir_info['subdomain']})")
    
    print(f"  Legacy directories: {len(audit['legacy_directories'])}")
    for dir_info in audit['legacy_directories']:
        print(f"    🔄 {dir_info['name']} → {dir_info['standard_name']}")
    
    print(f"  Unknown directories: {len(audit['unknown_directories'])}")
    for dir_info in audit['unknown_directories']:
        print(f"    ❓ {dir_info['name']}")
    
    if audit['recommendations']:
        print(f"\n💡 Recommendations:")
        for rec in audit['recommendations']:
            print(f"    {rec}")
    
    print("\n✅ League Directory Manager test completed!")