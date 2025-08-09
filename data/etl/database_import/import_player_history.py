#!/usr/bin/env python3
"""
FAST Player History Import - Truncate and Bulk Insert Approach

This version optimizes for speed by:
1. Truncating the player_history table
2. Bulk inserting all records at once
3. Only processing players that exist in the database

Performance: ~30 seconds instead of 30+ minutes
"""

import json
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add the project root to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
sys.path.insert(0, project_root)

project_root = Path(project_root)

from database_config import get_db
from utils.league_utils import normalize_league_id

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FastPlayerHistoryETL:
    """Fast ETL class for player history - truncate and bulk insert approach"""
    
    def __init__(self):
        self.data_dir = project_root / "data" / "leagues" / "all"
        self.player_history_file = self.data_dir / "player_history.json"
        
        self.stats = {
            'total_players': 0,
            'valid_players': 0,
            'total_history_records': 0,
            'imported_history_records': 0,
            'errors': 0
        }
        
        logger.info("🚀 Fast Player History ETL initialized")
    
    def load_player_history(self) -> List[Dict]:
        """Load player history data from JSON file"""
        if not self.player_history_file.exists():
            raise FileNotFoundError(f"Player history file not found: {self.player_history_file}")
        
        logger.info(f"📖 Loading player history from {self.player_history_file}")
        
        with open(self.player_history_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            data = [data]
        
        self.stats['total_players'] = len(data)
        logger.info(f"✅ Loaded {len(data):,} player records")
        return data
    
    def get_valid_player_mapping(self, cursor) -> Dict[str, int]:
        """Get mapping of tenniscores_player_id -> database player_id for existing players"""
        logger.info("🔍 Building player ID mapping...")
        
        cursor.execute("SELECT id, tenniscores_player_id FROM players WHERE tenniscores_player_id IS NOT NULL")
        player_mapping = {row[1]: row[0] for row in cursor.fetchall()}
        
        logger.info(f"✅ Found {len(player_mapping):,} valid players in database")
        return player_mapping
    
    def parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date from various formats"""
        if not date_str:
            return None
        
        date_formats = ["%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y"]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def prepare_bulk_data(self, player_history_data: List[Dict], player_mapping: Dict[str, int]) -> List[tuple]:
        """Prepare all valid history records for bulk insert"""
        logger.info("🔧 Preparing bulk insert data...")
        
        bulk_data = []
        
        for player_record in player_history_data:
            tenniscores_player_id = player_record.get("player_id")
            if not tenniscores_player_id or tenniscores_player_id not in player_mapping:
                continue
            
            player_db_id = player_mapping[tenniscores_player_id]
            matches = player_record.get("matches", [])
            
            if matches:
                self.stats['valid_players'] += 1
                self.stats['total_history_records'] += len(matches)
            
            for match in matches:
                try:
                    date_str = match.get("date")
                    end_pti = match.get("end_pti")
                    series = match.get("series", "")
                    
                    match_date = self.parse_date(date_str)
                    if not match_date:
                        continue
                    
                    try:
                        pti_value = float(end_pti) if end_pti is not None else None
                    except (ValueError, TypeError):
                        continue
                    
                    if pti_value is None:
                        continue
                    
                    # Add to bulk data: (player_id, date, end_pti, series, created_at)
                    bulk_data.append((
                        player_db_id,
                        match_date.date(),
                        pti_value,
                        series,
                        datetime.now()
                    ))
                    
                except Exception as e:
                    logger.debug(f"Error processing match: {e}")
                    self.stats['errors'] += 1
                    continue
        
        logger.info(f"✅ Prepared {len(bulk_data):,} records for bulk insert")
        return bulk_data
    
    def import_player_history(self, player_history_data: List[Dict]):
        """Fast import using truncate + bulk insert"""
        logger.info("🚀 Starting FAST player history import...")
        
        try:
            with get_db() as conn:
                with conn.cursor() as cursor:
                    # Step 1: Get valid player mapping
                    player_mapping = self.get_valid_player_mapping(cursor)
                    
                    # Step 2: Prepare bulk data
                    bulk_data = self.prepare_bulk_data(player_history_data, player_mapping)
                    
                    if not bulk_data:
                        logger.warning("⚠️ No valid data to import")
                        return
                    
                    # Step 3: Truncate existing data
                    logger.info("🗑️ Truncating existing player_history data...")
                    cursor.execute("TRUNCATE TABLE player_history RESTART IDENTITY CASCADE")
                    
                    # Step 4: Bulk insert
                    logger.info(f"⚡ Bulk inserting {len(bulk_data):,} records...")
                    
                    # Use execute_values for maximum performance
                    from psycopg2.extras import execute_values
                    
                    execute_values(
                        cursor,
                        """
                        INSERT INTO player_history (player_id, date, end_pti, series, created_at)
                        VALUES %s
                        """,
                        bulk_data,
                        template=None,
                        page_size=1000
                    )
                    
                    self.stats['imported_history_records'] = len(bulk_data)
                    
                    # Commit all changes
                    conn.commit()
                    logger.info("✅ Bulk import completed successfully!")
                    
        except Exception as e:
            logger.error(f"❌ Error during import: {e}")
            raise
    
    def print_summary(self):
        """Print import summary"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 FAST PLAYER HISTORY IMPORT SUMMARY")
        logger.info("=" * 60)
        logger.info(f"📥 Total Players Processed: {self.stats['total_players']:,}")
        logger.info(f"✅ Valid Players Found: {self.stats['valid_players']:,}")
        logger.info(f"📈 Total History Records Available: {self.stats['total_history_records']:,}")
        logger.info(f"⚡ History Records Imported: {self.stats['imported_history_records']:,}")
        logger.info(f"❌ Errors: {self.stats['errors']:,}")
        
        if self.stats['total_players'] > 0:
            success_rate = (self.stats['valid_players'] / self.stats['total_players']) * 100
            logger.info(f"📊 Success Rate: {success_rate:.1f}%")
        
        logger.info("=" * 60 + "\n")


def main():
    """Main function"""
    etl = FastPlayerHistoryETL()
    
    try:
        start_time = datetime.now()
        
        player_history_data = etl.load_player_history()
        etl.import_player_history(player_history_data)
        etl.print_summary()
        
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"🎉 Import completed in {duration.total_seconds():.1f} seconds!")
        
    except Exception as e:
        logger.error(f"❌ Player history import failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
