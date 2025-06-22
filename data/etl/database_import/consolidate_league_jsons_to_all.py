#!/usr/bin/env python3
"""
League Data Consolidation Script

This script consolidates JSON data from individual league folders into a single 'all' directory.
It creates backups of existing files, clears the consolidated files, then appends data from each league folder.

Usage:
    python consolidate_league_data.py

Process:
1. Create timestamped backup of existing files in data/leagues/all/
2. Clear all existing JSON files in data/leagues/all/
3. For each league folder in data/leagues/:
   - Read JSON files (match_history.json, players.json, schedules.json, series_stats.json, player_history.json)
   - Append data to corresponding files in data/leagues/all/
"""

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Define the base directory and target files
# Navigate up four levels: data/etl/database_import -> data/etl -> data -> project_root
BASE_DIR = Path(__file__).parent.parent.parent.parent / "data" / "leagues"
ALL_DIR = BASE_DIR / "all"
BACKUP_DIR = (
    Path(__file__).parent.parent.parent.parent / "data" / "backups" / "league_data"
)  # Centralized backup location
TARGET_FILES = [
    "match_history.json",
    "players.json",
    "schedules.json",
    "series_stats.json",
    "player_history.json",
]


def ensure_directory_exists(directory: Path) -> None:
    """Ensure the target directory exists."""
    directory.mkdir(parents=True, exist_ok=True)
    logger.info(f"Ensured directory exists: {directory}")


def create_backup() -> None:
    """Create a timestamped backup of existing files in a dedicated backup directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = BACKUP_DIR / f"backup_{timestamp}"

    logger.info(f"Creating backup in: {backup_dir}")

    # Create backup directory
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Copy existing files to backup
    files_backed_up = 0
    for filename in TARGET_FILES:
        source_file = ALL_DIR / filename
        backup_file = backup_dir / filename

        if source_file.exists():
            try:
                shutil.copy2(source_file, backup_file)
                logger.info(f"  Backed up: {filename}")
                files_backed_up += 1
            except Exception as e:
                logger.error(f"  Error backing up {filename}: {e}")
        else:
            logger.info(f"  File {filename} does not exist, skipping backup")

    logger.info(f"Backup complete: {files_backed_up} files backed up to {backup_dir}")


def clear_target_files() -> None:
    """Clear all target JSON files in the 'all' directory."""
    logger.info("Clearing existing consolidated files...")

    for filename in TARGET_FILES:
        target_file = ALL_DIR / filename
        try:
            # Write empty list to each JSON file
            with open(target_file, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)
            logger.info(f"Cleared: {filename}")
        except Exception as e:
            logger.error(f"Error clearing {filename}: {e}")


def get_league_folders() -> List[Path]:
    """Get all league folders (excluding 'all' directory)."""
    league_folders = []

    for item in BASE_DIR.iterdir():
        if (
            item.is_dir()
            and item.name != "all"
            and not item.name.startswith(".")
            and not item.name.startswith("backup_")
        ):
            league_folders.append(item)

    logger.info(f"Found league folders: {[f.name for f in league_folders]}")
    return league_folders


def read_json_file(file_path: Path) -> List[Dict[Any, Any]]:
    """Read and return JSON data from file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure data is a list
            if not isinstance(data, list):
                logger.warning(f"Data in {file_path} is not a list, wrapping in list")
                data = [data]
            return data
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in {file_path}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return []


def append_to_consolidated_file(
    filename: str, data: List[Dict[Any, Any]], league_name: str
) -> None:
    """Append data to the consolidated file in the 'all' directory."""
    target_file = ALL_DIR / filename

    try:
        # Read existing data
        existing_data = []
        if target_file.exists():
            existing_data = read_json_file(target_file)

        # Add league identifier to each record
        for record in data:
            if isinstance(record, dict):
                record["source_league"] = league_name

        # Combine data
        combined_data = existing_data + data

        # Write back to file
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(combined_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Appended {len(data)} records from {league_name} to {filename}")

    except Exception as e:
        logger.error(f"Error appending to {filename}: {e}")


def process_league_folder(league_folder: Path) -> None:
    """Process all JSON files in a league folder."""
    league_name = league_folder.name
    logger.info(f"Processing league: {league_name}")

    for filename in TARGET_FILES:
        source_file = league_folder / filename

        if source_file.exists():
            logger.info(f"  Processing {filename}")
            data = read_json_file(source_file)
            if data:
                append_to_consolidated_file(filename, data, league_name)
            else:
                logger.warning(f"  No data found in {source_file}")
        else:
            logger.info(f"  File {filename} not found in {league_name}, skipping")


def main():
    """Main function to consolidate league data."""
    logger.info("Starting league data consolidation...")

    # Ensure the 'all' directory exists
    ensure_directory_exists(ALL_DIR)

    # Create backup of existing files
    create_backup()

    # Clear existing consolidated files
    clear_target_files()

    # Get all league folders
    league_folders = get_league_folders()

    if not league_folders:
        logger.warning("No league folders found!")
        return

    # Process each league folder
    for league_folder in league_folders:
        process_league_folder(league_folder)

    # Log summary
    logger.info("Consolidation complete! Summary of consolidated files:")
    for filename in TARGET_FILES:
        target_file = ALL_DIR / filename
        if target_file.exists():
            try:
                data = read_json_file(target_file)
                logger.info(f"  {filename}: {len(data)} total records")
            except Exception as e:
                logger.error(f"  {filename}: Error reading for summary - {e}")


if __name__ == "__main__":
    main()
