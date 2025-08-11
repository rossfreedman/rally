#!/usr/bin/env python3
"""
Duplicate Prevention Service
============================

Prevents duplicate player records during ETL imports by implementing
comprehensive deduplication strategies at multiple levels.

Features:
- Pre-import duplicate detection
- Upsert-based imports (UPDATE/INSERT)
- Constraint-based validation
- Post-import cleanup
- Monitoring and alerting
"""

import logging
from typing import Dict, List, Optional, Tuple, Set
from database_utils import execute_query, execute_update, execute_query_one

logger = logging.getLogger(__name__)


class DuplicatePreventionService:
    """Service to prevent and resolve duplicate player records"""
    
    def __init__(self):
        self.stats = {
            'duplicates_prevented': 0,
            'duplicates_resolved': 0,
            'upserts_performed': 0,
            'inserts_performed': 0,
            'updates_performed': 0
        }
    
    def create_upsert_constraints(self):
        """Ensure database has proper constraints to prevent duplicates"""
        
        # Check if the unique constraint exists
        constraint_check = execute_query_one("""
            SELECT constraint_name 
            FROM information_schema.table_constraints 
            WHERE table_name = 'players' 
              AND constraint_type = 'UNIQUE'
              AND constraint_name = 'unique_player_in_league_club_series'
        """)
        
        if not constraint_check:
            logger.info("Creating unique constraint to prevent duplicates...")
            try:
                execute_update("""
                    ALTER TABLE players 
                    ADD CONSTRAINT unique_player_in_league_club_series 
                    UNIQUE (tenniscores_player_id, league_id, club_id, series_id)
                """)
                logger.info("✅ Unique constraint created successfully")
            except Exception as e:
                if "already exists" not in str(e):
                    logger.warning(f"Could not create constraint: {e}")
        else:
            logger.info("✅ Unique constraint already exists")
    
    def detect_import_duplicates(self, players_data: List[Dict]) -> Dict:
        """Detect duplicates in the data to be imported"""
        
        # Check for duplicates within the import data itself
        seen_players = set()
        internal_duplicates = []
        
        for player in players_data:
            player_id = player.get('Player ID', '').strip()
            league = player.get('League', '').strip()
            club = player.get('Club', '').strip()
            series = player.get('Series', '').strip()
            
            key = (player_id, league, club, series)
            if key in seen_players:
                internal_duplicates.append({
                    'player_id': player_id,
                    'name': f"{player.get('First Name', '')} {player.get('Last Name', '')}",
                    'league': league,
                    'club': club,
                    'series': series
                })
            else:
                seen_players.add(key)
        
        # Check for duplicates against existing database records
        if players_data:
            player_ids = [p.get('Player ID', '').strip() for p in players_data if p.get('Player ID')]
            
            if player_ids:
                # Create parameter placeholders for the IN clause
                placeholders = ','.join(['%s'] * len(player_ids))
                existing_players = execute_query(f"""
                    SELECT p.tenniscores_player_id, p.first_name, p.last_name,
                           l.league_id, c.name as club_name, s.name as series_name
                    FROM players p
                    JOIN leagues l ON p.league_id = l.id
                    LEFT JOIN clubs c ON p.club_id = c.id
                    LEFT JOIN series s ON p.series_id = s.id
                    WHERE p.tenniscores_player_id IN ({placeholders})
                """, player_ids)
            else:
                existing_players = []
        else:
            existing_players = []
        
        return {
            'internal_duplicates': internal_duplicates,
            'existing_players': existing_players,
            'total_to_import': len(players_data),
            'potential_conflicts': len(existing_players)
        }
    
    def perform_upsert_import(self, players_data: List[Dict]) -> Dict:
        """Perform upsert-based import to prevent duplicates"""
        
        logger.info(f"Starting upsert import for {len(players_data)} players...")
        
        # Pre-cache lookup data for performance
        league_cache, team_cache, club_cache, series_cache = self._build_lookup_caches()
        
        results = {
            'inserted': 0,
            'updated': 0,
            'skipped': 0,
            'errors': []
        }
        
        for player in players_data:
            try:
                result = self._upsert_single_player(player, league_cache, team_cache, club_cache, series_cache)
                results[result] += 1
                
            except Exception as e:
                error_msg = f"Failed to process {player.get('First Name', '')} {player.get('Last Name', '')}: {e}"
                results['errors'].append(error_msg)
                logger.warning(error_msg)
        
        self.stats['upserts_performed'] = results['inserted'] + results['updated']
        self.stats['inserts_performed'] = results['inserted']
        self.stats['updates_performed'] = results['updated']
        
        return results
    
    def _build_lookup_caches(self) -> Tuple[Dict, Dict, Dict, Dict]:
        """Build lookup caches for performance"""
        
        # League cache
        leagues = execute_query("SELECT id, league_id FROM leagues")
        league_cache = {row['league_id']: row['id'] for row in leagues}
        
        # Team cache
        teams = execute_query("""
            SELECT t.id, t.team_name, l.league_id
            FROM teams t
            JOIN leagues l ON t.league_id = l.id
        """)
        team_cache = {(row['league_id'], row['team_name']): row['id'] for row in teams}
        
        # Club cache
        clubs = execute_query("SELECT id, name FROM clubs")
        club_cache = {row['name']: row['id'] for row in clubs}
        
        # Series cache
        series = execute_query("SELECT id, name FROM series")
        series_cache = {row['name']: row['id'] for row in series}
        
        return league_cache, team_cache, club_cache, series_cache
    
    def _upsert_single_player(self, player: Dict, league_cache: Dict, 
                             team_cache: Dict, club_cache: Dict, series_cache: Dict) -> str:
        """Upsert a single player record"""
        
        # Extract and validate player data
        tenniscores_player_id = (player.get("Player ID") or "").strip()
        first_name = (player.get("First Name") or "").strip()
        last_name = (player.get("Last Name") or "").strip()
        
        if not tenniscores_player_id or not first_name or not last_name:
            return 'skipped'
        
        # Get foreign key IDs
        league_id = player.get("League", "").strip()
        league_db_id = league_cache.get(league_id)
        if not league_db_id:
            return 'skipped'
        
        team_name = player.get("Series Mapping ID", "").strip()
        team_id = team_cache.get((league_id, team_name)) if team_name else None
        
        club_name = player.get("Club", "").strip()
        club_id = club_cache.get(club_name) if club_name else None
        
        series_name = player.get("Series", "").strip()
        series_id = series_cache.get(series_name) if series_name else None
        
        # Check if player already exists
        existing_player = execute_query_one("""
            SELECT id FROM players 
            WHERE tenniscores_player_id = %s AND league_id = %s
        """, (tenniscores_player_id, league_db_id))
        
        if existing_player:
            # Update existing player
            execute_update("""
                UPDATE players 
                SET first_name = %s, last_name = %s, team_id = %s, 
                    club_id = %s, series_id = %s, updated_at = NOW()
                WHERE id = %s
            """, (first_name, last_name, team_id, club_id, series_id, existing_player['id']))
            return 'updated'
        else:
            # Insert new player
            execute_update("""
                INSERT INTO players (tenniscores_player_id, first_name, last_name, 
                                   league_id, team_id, club_id, series_id, 
                                   is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, (tenniscores_player_id, first_name, last_name, league_db_id, 
                  team_id, club_id, series_id, True))
            return 'inserted'
    
    def check_existing_player(self, tenniscores_player_id: str, league_id: int, 
                             club_id: int = None, series_id: int = None) -> Optional[Dict]:
        """Check if a player already exists in the database"""
        try:
            existing_player = execute_query_one("""
                SELECT id, tenniscores_player_id, first_name, last_name, 
                       league_id, club_id, series_id, team_id
                FROM players 
                WHERE tenniscores_player_id = %s AND league_id = %s
            """, (tenniscores_player_id, league_id))
            
            return existing_player
        except Exception as e:
            logger.error(f"Error checking existing player {tenniscores_player_id}: {e}")
            return None
    
    def cleanup_existing_duplicates(self, league_id: str = None) -> Dict:
        """Clean up existing duplicate records in the database"""
        
        logger.info("Scanning for existing duplicate records...")
        
        # Build WHERE clause for league filter
        where_clause = ""
        params = []
        if league_id:
            where_clause = "WHERE l.league_id = %s"
            params.append(league_id)
        
        # Find duplicate players (same tenniscores_player_id in same league)
        duplicates = execute_query(f"""
            WITH duplicate_players AS (
                SELECT p.tenniscores_player_id, l.league_id, COUNT(*) as record_count
                FROM players p
                JOIN leagues l ON p.league_id = l.id
                {where_clause}
                GROUP BY p.tenniscores_player_id, l.league_id
                HAVING COUNT(*) > 1
            )
            SELECT p.id, p.tenniscores_player_id, p.first_name, p.last_name,
                   l.league_id, s.name as series_name, t.team_name,
                   p.created_at, p.updated_at
            FROM players p
            JOIN leagues l ON p.league_id = l.id
            LEFT JOIN series s ON p.series_id = s.id
            LEFT JOIN teams t ON p.team_id = t.id
            JOIN duplicate_players dp ON p.tenniscores_player_id = dp.tenniscores_player_id 
                                      AND l.league_id = dp.league_id
            ORDER BY p.tenniscores_player_id, p.created_at DESC
        """, params)
        
        # Group duplicates by player
        from collections import defaultdict
        player_groups = defaultdict(list)
        for dup in duplicates:
            key = (dup['tenniscores_player_id'], dup['league_id'])
            player_groups[key].append(dup)
        
        # Clean up duplicates - keep the most recent/complete record
        cleanup_results = {
            'groups_processed': 0,
            'records_deleted': 0,
            'records_kept': 0
        }
        
        for (player_id, league), records in player_groups.items():
            if len(records) > 1:
                # Sort by completeness score (team_id, series_id, updated_at)
                records.sort(key=lambda r: (
                    1 if r['team_name'] else 0,  # Has team
                    1 if r['series_name'] else 0,  # Has series
                    r['updated_at'] if r['updated_at'] else r['created_at']  # Most recent
                ), reverse=True)
                
                # Keep the best record, delete the rest
                best_record = records[0]
                records_to_delete = records[1:]
                
                for record in records_to_delete:
                    execute_update("DELETE FROM players WHERE id = %s", (record['id'],))
                    logger.info(f"Deleted duplicate: {record['first_name']} {record['last_name']} (ID {record['id']})")
                    cleanup_results['records_deleted'] += 1
                
                cleanup_results['records_kept'] += 1
                cleanup_results['groups_processed'] += 1
        
        self.stats['duplicates_resolved'] = cleanup_results['records_deleted']
        return cleanup_results
    
    def generate_prevention_report(self) -> Dict:
        """Generate a report on duplicate prevention activities"""
        
        return {
            'timestamp': str(datetime.now()),
            'prevention_stats': self.stats,
            'recommendations': self._get_prevention_recommendations()
        }
    
    def _get_prevention_recommendations(self) -> List[str]:
        """Get recommendations for duplicate prevention"""
        
        recommendations = []
        
        if self.stats['duplicates_resolved'] > 0:
            recommendations.append("Consider reviewing import processes to prevent future duplicates")
        
        if self.stats['upserts_performed'] > self.stats['inserts_performed']:
            recommendations.append("High update rate detected - verify data source consistency")
        
        recommendations.append("Use upsert-based imports for all future ETL operations")
        recommendations.append("Monitor duplicate prevention metrics regularly")
        
        return recommendations


def create_duplicate_prevention_enhancement():
    """Create enhanced import_players.py with duplicate prevention"""
    
    enhancement_code = '''
# Add to import_players.py - Enhanced version with duplicate prevention

from duplicate_prevention_service import DuplicatePreventionService

class EnhancedPlayersETL(PlayersETL):
    """Enhanced Players ETL with duplicate prevention"""
    
    def __init__(self):
        super().__init__()
        self.duplicate_service = DuplicatePreventionService()
    
    def import_players_with_prevention(self, json_file_path: str):
        """Import players with comprehensive duplicate prevention"""
        
        # Ensure constraints exist
        self.duplicate_service.create_upsert_constraints()
        
        # Load data
        with open(json_file_path, 'r') as f:
            players_data = json.load(f)
        
        # Detect potential duplicates
        duplicate_analysis = self.duplicate_service.detect_import_duplicates(players_data)
        
        if duplicate_analysis['internal_duplicates']:
            logger.warning(f"Found {len(duplicate_analysis['internal_duplicates'])} internal duplicates")
        
        if duplicate_analysis['potential_conflicts']:
            logger.info(f"Found {duplicate_analysis['potential_conflicts']} existing players that may be updated")
        
        # Perform upsert import
        results = self.duplicate_service.perform_upsert_import(players_data)
        
        # Clean up any remaining duplicates
        cleanup_results = self.duplicate_service.cleanup_existing_duplicates()
        
        return {
            'import_results': results,
            'cleanup_results': cleanup_results,
            'duplicate_analysis': duplicate_analysis
        }
'''
    
    return enhancement_code


if __name__ == "__main__":
    # Example usage
    from datetime import datetime
    
    service = DuplicatePreventionService()
    
    # Clean up existing duplicates
    print("🧹 Cleaning up existing duplicates...")
    cleanup_results = service.cleanup_existing_duplicates('CNSWPL')
    print(f"✅ Cleaned up {cleanup_results['records_deleted']} duplicate records")
    
    # Generate report
    report = service.generate_prevention_report()
    print(f"📊 Prevention Report: {report}")
