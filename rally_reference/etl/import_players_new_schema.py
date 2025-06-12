#!/usr/bin/env python3
"""
Rally Player Import ETL - Refactored Schema
Updated to work with the new schema where players table contains league-specific records
"""
import json
import os
import sys
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database_models import (
    Player, League, Club, Series, ClubLeague, SeriesLeague
)
from database_config import get_db_engine

logger = logging.getLogger(__name__)

# Create session factory
engine = get_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_or_create_league(league_name: str, db_session) -> League:
    """Get existing league or create new one"""
    # Normalize league name for consistent lookup
    league_mappings = {
        'APTA Chicago': 'APTA_CHICAGO',
        'APTA_CHICAGO': 'APTA_CHICAGO',
        'Chicago': 'APTA_CHICAGO',
        'NSTF': 'NSTF',
        'North Shore Tennis Foundation': 'NSTF',
        'APTA National': 'APTA_NATIONAL',
        'APTA_NATIONAL': 'APTA_NATIONAL'
    }
    
    league_id = league_mappings.get(league_name, league_name.upper().replace(' ', '_'))
    
    league = db_session.query(League).filter(
        League.league_id == league_id
    ).first()
    
    if not league:
        league = League(
            league_id=league_id,
            league_name=league_name,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db_session.add(league)
        db_session.flush()
        logger.info(f"Created new league: {league_name} ({league_id})")
    
    return league

def get_or_create_club(club_name: str, db_session) -> Club:
    """Get existing club or create new one"""
    club = db_session.query(Club).filter(
        Club.name.ilike(club_name)
    ).first()
    
    if not club:
        club = Club(
            name=club_name,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db_session.add(club)
        db_session.flush()
        logger.info(f"Created new club: {club_name}")
    
    return club

def get_or_create_series(series_name: str, db_session) -> Series:
    """Get existing series or create new one"""
    series = db_session.query(Series).filter(
        Series.name.ilike(series_name)
    ).first()
    
    if not series:
        series = Series(
            name=series_name,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db_session.add(series)
        db_session.flush()
        logger.info(f"Created new series: {series_name}")
    
    return series

def ensure_club_league_association(club: Club, league: League, db_session):
    """Ensure club-league association exists"""
    existing = db_session.query(ClubLeague).filter(
        and_(
            ClubLeague.club_id == club.id,
            ClubLeague.league_id == league.id
        )
    ).first()
    
    if not existing:
        association = ClubLeague(
            club_id=club.id,
            league_id=league.id,
            created_at=datetime.now()
        )
        db_session.add(association)
        logger.debug(f"Created club-league association: {club.name} <-> {league.league_name}")

def ensure_series_league_association(series: Series, league: League, db_session):
    """Ensure series-league association exists"""
    existing = db_session.query(SeriesLeague).filter(
        and_(
            SeriesLeague.series_id == series.id,
            SeriesLeague.league_id == league.id
        )
    ).first()
    
    if not existing:
        association = SeriesLeague(
            series_id=series.id,
            league_id=league.id,
            created_at=datetime.now()
        )
        db_session.add(association)
        logger.debug(f"Created series-league association: {series.name} <-> {league.league_name}")

def parse_numeric_value(value: Any) -> Optional[float]:
    """Safely parse numeric values from JSON data"""
    if value is None or value == '':
        return None
    
    try:
        # Handle string values that might have commas or other formatting
        if isinstance(value, str):
            # Remove commas and convert to float
            cleaned = value.replace(',', '').strip()
            if cleaned == '' or cleaned.lower() in ['null', 'none', 'n/a']:
                return None
            return float(cleaned)
        
        return float(value)
    except (ValueError, TypeError):
        logger.warning(f"Could not parse numeric value: {value}")
        return None

def import_players_from_json(json_file_path: str, dry_run: bool = False) -> Dict[str, Any]:
    """
    Import players from JSON file into the refactored schema
    
    Expected JSON structure:
    [
        {
            "League": "APTA Chicago",
            "Series": "Chicago 38", 
            "Club": "Winter Club",
            "Location ID": "some_id",
            "Player ID": "nndz-WlNlOXg3ci9qQT09",
            "First Name": "John",
            "Last Name": "Doe", 
            "PTI": "85.5",
            "Wins": "12",
            "Losses": "8",
            "Win %": "60.0",
            "Captain": "Yes"
        }
    ]
    """
    
    if not os.path.exists(json_file_path):
        return {
            'success': False,
            'error': f'File not found: {json_file_path}'
        }
    
    logger.info(f"Starting player import from {json_file_path}")
    
    # Load JSON data
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            player_data = json.load(f)
    except Exception as e:
        return {
            'success': False,
            'error': f'Failed to load JSON file: {str(e)}'
        }
    
    if not isinstance(player_data, list):
        return {
            'success': False,
            'error': 'JSON file must contain an array of player records'
        }
    
    logger.info(f"Loaded {len(player_data)} player records from JSON")
    
    # Track statistics
    stats = {
        'total_records': len(player_data),
        'players_created': 0,
        'players_updated': 0,
        'leagues_created': 0,
        'clubs_created': 0,
        'series_created': 0,
        'errors': [],
        'skipped_records': 0
    }
    
    if dry_run:
        logger.info("DRY RUN MODE - No actual database changes will be made")
        return analyze_json_data(player_data)
    
    db_session = SessionLocal()
    
    try:
        # Track entities created in this session
        leagues_cache = {}
        clubs_cache = {}  
        series_cache = {}
        
        for i, record in enumerate(player_data, 1):
            try:
                # Extract and validate required fields
                league_name = record.get('League', '').strip()
                series_name = record.get('Series', '').strip()
                club_name = record.get('Club', '').strip()
                player_id = record.get('Player ID', '').strip()
                first_name = record.get('First Name', '').strip()
                last_name = record.get('Last Name', '').strip()
                
                if not all([league_name, series_name, club_name, player_id, first_name, last_name]):
                    logger.warning(f"Record {i}: Missing required fields, skipping")
                    stats['skipped_records'] += 1
                    stats['errors'].append(f"Record {i}: Missing required fields")
                    continue
                
                # Get or create league (with caching)
                if league_name not in leagues_cache:
                    leagues_cache[league_name] = get_or_create_league(league_name, db_session)
                    if leagues_cache[league_name].created_at == leagues_cache[league_name].updated_at:
                        stats['leagues_created'] += 1
                
                league = leagues_cache[league_name]
                
                # Get or create club (with caching)
                if club_name not in clubs_cache:
                    clubs_cache[club_name] = get_or_create_club(club_name, db_session)
                    if clubs_cache[club_name].created_at == clubs_cache[club_name].updated_at:
                        stats['clubs_created'] += 1
                
                club = clubs_cache[club_name]
                
                # Get or create series (with caching)
                if series_name not in series_cache:
                    series_cache[series_name] = get_or_create_series(series_name, db_session)
                    if series_cache[series_name].created_at == series_cache[series_name].updated_at:
                        stats['series_created'] += 1
                
                series = series_cache[series_name]
                
                # Ensure associations exist
                ensure_club_league_association(club, league, db_session)
                ensure_series_league_association(series, league, db_session)
                
                # Parse statistical fields
                pti = parse_numeric_value(record.get('PTI'))
                wins = int(parse_numeric_value(record.get('Wins', 0)) or 0)
                losses = int(parse_numeric_value(record.get('Losses', 0)) or 0)
                win_percentage = parse_numeric_value(record.get('Win %'))
                captain_status = record.get('Captain', '').strip()
                
                # Calculate win percentage if not provided
                if win_percentage is None and (wins > 0 or losses > 0):
                    total_games = wins + losses
                    if total_games > 0:
                        win_percentage = (wins / total_games) * 100
                
                # Check if player record already exists for this league
                existing_player = db_session.query(Player).filter(
                    and_(
                        Player.tenniscores_player_id == player_id,
                        Player.league_id == league.id
                    )
                ).first()
                
                if existing_player:
                    # Update existing player
                    existing_player.first_name = first_name
                    existing_player.last_name = last_name
                    existing_player.club_id = club.id
                    existing_player.series_id = series.id
                    existing_player.pti = pti
                    existing_player.wins = wins
                    existing_player.losses = losses
                    existing_player.win_percentage = win_percentage
                    existing_player.captain_status = captain_status
                    existing_player.is_active = True
                    existing_player.updated_at = datetime.now()
                    
                    stats['players_updated'] += 1
                    logger.debug(f"Updated player: {first_name} {last_name} ({player_id}) in {league_name}")
                    
                else:
                    # Create new player record
                    new_player = Player(
                        tenniscores_player_id=player_id,
                        first_name=first_name,
                        last_name=last_name,
                        league_id=league.id,
                        club_id=club.id,
                        series_id=series.id,
                        pti=pti,
                        wins=wins,
                        losses=losses,
                        win_percentage=win_percentage,
                        captain_status=captain_status,
                        is_active=True,
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    
                    db_session.add(new_player)
                    stats['players_created'] += 1
                    logger.debug(f"Created player: {first_name} {last_name} ({player_id}) in {league_name}")
                
                # Commit every 100 records for better memory management
                if i % 100 == 0:
                    db_session.commit()
                    logger.info(f"Processed {i}/{len(player_data)} records...")
                    
            except Exception as e:
                logger.error(f"Error processing record {i}: {str(e)}")
                stats['errors'].append(f"Record {i}: {str(e)}")
                continue
        
        # Final commit
        db_session.commit()
        
        logger.info(f"Import completed successfully!")
        logger.info(f"Players created: {stats['players_created']}")
        logger.info(f"Players updated: {stats['players_updated']}")
        logger.info(f"Leagues created: {stats['leagues_created']}")
        logger.info(f"Clubs created: {stats['clubs_created']}")
        logger.info(f"Series created: {stats['series_created']}")
        logger.info(f"Records skipped: {stats['skipped_records']}")
        logger.info(f"Errors: {len(stats['errors'])}")
        
        return {
            'success': True,
            'stats': stats,
            'message': f"Successfully imported {stats['players_created']} new players and updated {stats['players_updated']} existing players"
        }
        
    except Exception as e:
        db_session.rollback()
        logger.error(f"Import failed: {str(e)}")
        return {
            'success': False,
            'error': f'Import failed: {str(e)}',
            'stats': stats
        }
        
    finally:
        db_session.close()

def analyze_json_data(player_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze JSON data without making database changes (dry run)
    """
    analysis = {
        'total_records': len(player_data),
        'leagues': set(),
        'clubs': set(),
        'series': set(),
        'unique_players': set(),
        'sample_records': player_data[:5] if len(player_data) > 5 else player_data,
        'field_analysis': {},
        'validation_errors': []
    }
    
    required_fields = ['League', 'Series', 'Club', 'Player ID', 'First Name', 'Last Name']
    optional_fields = ['PTI', 'Wins', 'Losses', 'Win %', 'Captain']
    
    for i, record in enumerate(player_data, 1):
        # Check required fields
        missing_fields = [field for field in required_fields if not record.get(field, '').strip()]
        if missing_fields:
            analysis['validation_errors'].append(f"Record {i}: Missing fields: {missing_fields}")
            continue
        
        # Collect unique values
        league = record.get('League', '').strip()
        club = record.get('Club', '').strip()
        series = record.get('Series', '').strip()
        player_id = record.get('Player ID', '').strip()
        
        if league:
            analysis['leagues'].add(league)
        if club:
            analysis['clubs'].add(club)
        if series:
            analysis['series'].add(series)
        if player_id:
            analysis['unique_players'].add(player_id)
    
    # Convert sets to sorted lists for JSON serialization
    analysis['leagues'] = sorted(list(analysis['leagues']))
    analysis['clubs'] = sorted(list(analysis['clubs']))
    analysis['series'] = sorted(list(analysis['series']))
    analysis['unique_players_count'] = len(analysis['unique_players'])
    del analysis['unique_players']  # Don't include the full set
    
    # Field analysis
    for field in required_fields + optional_fields:
        values = [record.get(field) for record in player_data if record.get(field)]
        analysis['field_analysis'][field] = {
            'total_records': len(values),
            'unique_values': len(set(values)),
            'sample_values': list(set(values))[:10]  # Show up to 10 sample values
        }
    
    logger.info("=== DRY RUN ANALYSIS ===")
    logger.info(f"Total records: {analysis['total_records']}")
    logger.info(f"Unique leagues: {len(analysis['leagues'])}")
    logger.info(f"Unique clubs: {len(analysis['clubs'])}")
    logger.info(f"Unique series: {len(analysis['series'])}")
    logger.info(f"Unique players: {analysis['unique_players_count']}")
    logger.info(f"Validation errors: {len(analysis['validation_errors'])}")
    
    return {
        'success': True,
        'dry_run': True,
        'analysis': analysis
    }

def main():
    """Main function for command line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Import players from JSON file')
    parser.add_argument('json_file', help='Path to JSON file containing player data')
    parser.add_argument('--dry-run', action='store_true', help='Analyze data without making changes')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run import
    result = import_players_from_json(args.json_file, dry_run=args.dry_run)
    
    if result['success']:
        print("✅ Import completed successfully!")
        if 'stats' in result:
            stats = result['stats']
            print(f"   Players created: {stats['players_created']}")
            print(f"   Players updated: {stats['players_updated']}")
            print(f"   Records skipped: {stats['skipped_records']}")
            if stats['errors']:
                print(f"   Errors: {len(stats['errors'])}")
        elif 'analysis' in result:
            analysis = result['analysis']
            print(f"   Total records: {analysis['total_records']}")
            print(f"   Unique players: {analysis['unique_players_count']}")
            print(f"   Leagues: {len(analysis['leagues'])}")
            print(f"   Clubs: {len(analysis['clubs'])}")
            print(f"   Series: {len(analysis['series'])}")
    else:
        print(f"❌ Import failed: {result['error']}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 