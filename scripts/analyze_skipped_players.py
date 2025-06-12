#!/usr/bin/env python3
"""
Comprehensive Analysis of Skipped Players from Safe ID Mapping Migration
Provides detailed breakdown of why 533 players were skipped and actionable recommendations
"""

import psycopg2
from urllib.parse import urlparse
import logging
import sys
import os
import json
from collections import defaultdict, Counter
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_config import get_db

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

RAILWAY_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

def connect_to_railway():
    """Connect to Railway database"""
    parsed = urlparse(RAILWAY_URL)
    conn_params = {
        'dbname': parsed.path[1:],
        'user': parsed.username,
        'password': parsed.password,
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'sslmode': 'require',
        'connect_timeout': 10
    }
    return psycopg2.connect(**conn_params)

class SkippedPlayersAnalyzer:
    """Comprehensive analysis of players that were skipped during migration"""
    
    def __init__(self):
        self.local_conn = None
        self.railway_conn = None
        self.club_mapping = {}
        self.series_mapping = {}
        self.skipped_analysis = {
            'total_skipped': 0,
            'skip_reasons': {
                'unmapped_club_only': [],
                'unmapped_series_only': [],
                'both_unmapped': [],
                'other_reasons': []
            },
            'unmapped_clubs': {},
            'unmapped_series': {},
            'data_quality_analysis': {},
            'recommendations': [],
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    def connect_databases(self):
        """Establish database connections"""
        logger.info("🔌 Connecting to databases...")
        self.local_db_context = get_db()
        self.local_conn = self.local_db_context.__enter__()
        self.railway_conn = connect_to_railway()
    
    def disconnect_databases(self):
        """Close database connections"""
        if hasattr(self, 'local_db_context') and self.local_db_context:
            try:
                self.local_db_context.__exit__(None, None, None)
            except:
                pass
        if self.railway_conn:
            try:
                self.railway_conn.close()
            except:
                pass
    
    def load_existing_mappings(self):
        """Load the existing club and series mappings from the previous analysis"""
        logger.info("📋 Loading existing ID mappings...")
        
        local_cursor = self.local_conn.cursor()
        railway_cursor = self.railway_conn.cursor()
        
        # Rebuild club mappings
        local_cursor.execute("SELECT id, name FROM clubs ORDER BY name")
        local_clubs = local_cursor.fetchall()
        
        railway_cursor.execute("SELECT id, name FROM clubs ORDER BY name")
        railway_clubs = railway_cursor.fetchall()
        
        railway_by_name = {name.strip().lower(): id for id, name in railway_clubs}
        
        for local_id, local_name in local_clubs:
            name_key = local_name.strip().lower()
            if name_key in railway_by_name:
                self.club_mapping[local_id] = railway_by_name[name_key]
        
        # Rebuild series mappings
        local_cursor.execute("SELECT id, name FROM series ORDER BY name")
        local_series = local_cursor.fetchall()
        
        railway_cursor.execute("SELECT id, name FROM series ORDER BY name")
        railway_series = railway_cursor.fetchall()
        
        railway_series_by_name = {name.strip().lower(): id for id, name in railway_series}
        
        for local_id, local_name in local_series:
            name_key = local_name.strip().lower()
            if name_key in railway_series_by_name:
                self.series_mapping[local_id] = railway_series_by_name[name_key]
            else:
                self.series_mapping[local_id] = None
        
        logger.info(f"  ✅ Loaded {len(self.club_mapping)} club mappings")
        logger.info(f"  ✅ Loaded {len([v for v in self.series_mapping.values() if v is not None])} series mappings")
    
    def analyze_all_players(self):
        """Analyze all players to identify which ones would be skipped and why"""
        logger.info("🔍 Analyzing all players for skip reasons...")
        
        local_cursor = self.local_conn.cursor()
        
        # Get all players with their associated data
        local_cursor.execute("""
            SELECT p.*, c.name as club_name, s.name as series_name 
            FROM players p
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            ORDER BY p.id
        """)
        
        players = local_cursor.fetchall()
        columns = [desc[0] for desc in local_cursor.description]
        
        total_players = len(players)
        logger.info(f"  📊 Analyzing {total_players} total players...")
        
        skipped_players = []
        migrated_players = []
        
        for player_row in players:
            player_dict = dict(zip(columns, player_row))
            
            original_club_id = player_dict['club_id']
            original_series_id = player_dict['series_id']
            
            skip_reasons = []
            can_map_club = True
            can_map_series = True
            
            # Check club mapping
            if original_club_id is not None:
                if original_club_id not in self.club_mapping:
                    skip_reasons.append(f"unmapped_club_id_{original_club_id}")
                    can_map_club = False
            
            # Check series mapping
            if original_series_id is not None:
                if original_series_id not in self.series_mapping:
                    skip_reasons.append(f"unmapped_series_id_{original_series_id}")
                    can_map_series = False
                elif self.series_mapping[original_series_id] is None:
                    skip_reasons.append(f"null_mapped_series_id_{original_series_id}")
                    can_map_series = False
            
            # Categorize the player
            if skip_reasons:
                player_dict['skip_reasons'] = skip_reasons
                player_dict['can_map_club'] = can_map_club
                player_dict['can_map_series'] = can_map_series
                skipped_players.append(player_dict)
            else:
                migrated_players.append(player_dict)
        
        logger.info(f"  ✅ Analysis complete: {len(migrated_players)} migrated, {len(skipped_players)} skipped")
        return skipped_players, migrated_players
    
    def categorize_skipped_players(self, skipped_players):
        """Categorize skipped players by their skip reasons"""
        logger.info("📊 Categorizing skipped players...")
        
        for player in skipped_players:
            has_club_issue = not player['can_map_club']
            has_series_issue = not player['can_map_series']
            
            if has_club_issue and has_series_issue:
                self.skipped_analysis['skip_reasons']['both_unmapped'].append(player)
            elif has_club_issue:
                self.skipped_analysis['skip_reasons']['unmapped_club_only'].append(player)
            elif has_series_issue:
                self.skipped_analysis['skip_reasons']['unmapped_series_only'].append(player)
            else:
                self.skipped_analysis['skip_reasons']['other_reasons'].append(player)
        
        self.skipped_analysis['total_skipped'] = len(skipped_players)
        
        # Log summary
        for reason, players in self.skipped_analysis['skip_reasons'].items():
            if players:
                logger.info(f"  • {reason}: {len(players)} players")
    
    def analyze_unmapped_entities(self, skipped_players):
        """Detailed analysis of unmapped clubs and series"""
        logger.info("🏢 Analyzing unmapped clubs and series...")
        
        local_cursor = self.local_conn.cursor()
        
        # Collect unmapped club IDs and series IDs
        unmapped_club_ids = set()
        unmapped_series_ids = set()
        
        for player in skipped_players:
            if not player['can_map_club'] and player['club_id'] is not None:
                unmapped_club_ids.add(player['club_id'])
            if not player['can_map_series'] and player['series_id'] is not None:
                unmapped_series_ids.add(player['series_id'])
        
        # Get detailed club information
        if unmapped_club_ids:
            club_placeholders = ','.join(['%s'] * len(unmapped_club_ids))
            local_cursor.execute(f"""
                SELECT c.id, c.name, COUNT(p.id) as player_count
                FROM clubs c
                LEFT JOIN players p ON c.id = p.club_id
                WHERE c.id IN ({club_placeholders})
                GROUP BY c.id, c.name
                ORDER BY player_count DESC, c.name
            """, tuple(unmapped_club_ids))
            
            for club_id, club_name, player_count in local_cursor.fetchall():
                self.skipped_analysis['unmapped_clubs'][club_id] = {
                    'name': club_name,
                    'player_count': player_count,
                    'id': club_id
                }
        
        # Get detailed series information
        if unmapped_series_ids:
            series_placeholders = ','.join(['%s'] * len(unmapped_series_ids))
            local_cursor.execute(f"""
                SELECT s.id, s.name, COUNT(p.id) as player_count
                FROM series s
                LEFT JOIN players p ON s.id = p.series_id
                WHERE s.id IN ({series_placeholders})
                GROUP BY s.id, s.name
                ORDER BY player_count DESC, s.name
            """, tuple(unmapped_series_ids))
            
            for series_id, series_name, player_count in local_cursor.fetchall():
                self.skipped_analysis['unmapped_series'][series_id] = {
                    'name': series_name,
                    'player_count': player_count,
                    'id': series_id
                }
        
        logger.info(f"  📊 Found {len(self.skipped_analysis['unmapped_clubs'])} unmapped clubs")
        logger.info(f"  📊 Found {len(self.skipped_analysis['unmapped_series'])} unmapped series")
    
    def analyze_data_quality(self, skipped_players):
        """Analyze data quality patterns in skipped players"""
        logger.info("🔬 Analyzing data quality patterns...")
        
        # Analyze by club
        club_patterns = defaultdict(list)
        series_patterns = defaultdict(list)
        
        for player in skipped_players:
            club_name = player.get('club_name', 'NULL')
            series_name = player.get('series_name', 'NULL')
            
            club_patterns[club_name].append(player)
            series_patterns[series_name].append(player)
        
        # Find patterns
        self.skipped_analysis['data_quality_analysis'] = {
            'most_affected_clubs': dict(sorted(
                [(club, len(players)) for club, players in club_patterns.items()],
                key=lambda x: x[1], reverse=True
            )[:10]),
            'most_affected_series': dict(sorted(
                [(series, len(players)) for series, players in series_patterns.items()],
                key=lambda x: x[1], reverse=True
            )[:10]),
            'club_pattern_count': len(club_patterns),
            'series_pattern_count': len(series_patterns),
            'null_club_count': len(club_patterns.get('NULL', [])),
            'null_series_count': len(series_patterns.get('NULL', []))
        }
    
    def generate_recommendations(self):
        """Generate actionable recommendations based on analysis"""
        logger.info("💡 Generating recommendations...")
        
        recommendations = []
        
        # Analyze the biggest impact opportunities
        unmapped_clubs = self.skipped_analysis['unmapped_clubs']
        unmapped_series = self.skipped_analysis['unmapped_series']
        
        # Club recommendations
        if unmapped_clubs:
            total_players_affected_by_clubs = sum(club['player_count'] for club in unmapped_clubs.values())
            top_clubs = sorted(unmapped_clubs.values(), key=lambda x: x['player_count'], reverse=True)[:5]
            
            recommendations.append({
                'type': 'club_mapping',
                'priority': 'HIGH' if total_players_affected_by_clubs > 200 else 'MEDIUM',
                'title': f'Map {len(unmapped_clubs)} Missing Clubs',
                'description': f'Mapping missing clubs could recover {total_players_affected_by_clubs} additional players',
                'top_impact_clubs': [f"{club['name']} ({club['player_count']} players)" for club in top_clubs],
                'action': 'Create manual club mappings or add missing clubs to Railway'
            })
        
        # Series recommendations
        if unmapped_series:
            total_players_affected_by_series = sum(series['player_count'] for series in unmapped_series.values())
            top_series = sorted(unmapped_series.values(), key=lambda x: x['player_count'], reverse=True)[:3]
            
            recommendations.append({
                'type': 'series_mapping',
                'priority': 'HIGH' if total_players_affected_by_series > 100 else 'MEDIUM',
                'title': f'Map {len(unmapped_series)} Missing Series',
                'description': f'Mapping missing series could recover {total_players_affected_by_series} additional players',
                'top_impact_series': [f"{series['name']} ({series['player_count']} players)" for series in top_series],
                'action': 'Create manual series mappings or add missing series to Railway'
            })
        
        # Data quality recommendations
        skip_reasons = self.skipped_analysis['skip_reasons']
        if skip_reasons['both_unmapped']:
            recommendations.append({
                'type': 'data_quality',
                'priority': 'LOW',
                'title': 'Clean Up Players with Multiple Issues',
                'description': f'{len(skip_reasons["both_unmapped"])} players have both unmapped clubs and series',
                'action': 'Review and potentially exclude invalid test data'
            })
        
        self.skipped_analysis['recommendations'] = recommendations
    
    def save_detailed_report(self, filename="skipped_players_analysis.json"):
        """Save comprehensive analysis report"""
        filepath = os.path.join("scripts", filename)
        with open(filepath, 'w') as f:
            json.dump(self.skipped_analysis, f, indent=2, default=str)
        logger.info(f"📄 Detailed analysis saved to {filepath}")
        return filepath
    
    def print_executive_summary(self):
        """Print executive summary of skipped players analysis"""
        print("\n" + "="*80)
        print("📋 SKIPPED PLAYERS ANALYSIS - EXECUTIVE SUMMARY")
        print("="*80)
        
        total = self.skipped_analysis['total_skipped']
        skip_reasons = self.skipped_analysis['skip_reasons']
        
        print(f"🎯 OVERVIEW:")
        print(f"  • Total Players Skipped: {total:,}")
        print(f"  • Unmapped Club Issues: {len(skip_reasons['unmapped_club_only']) + len(skip_reasons['both_unmapped'])}")
        print(f"  • Unmapped Series Issues: {len(skip_reasons['unmapped_series_only']) + len(skip_reasons['both_unmapped'])}")
        print(f"  • Both Issues: {len(skip_reasons['both_unmapped'])}")
        
        print(f"\n📊 BREAKDOWN BY SKIP REASON:")
        for reason, players in skip_reasons.items():
            if players:
                percentage = (len(players) / total) * 100
                print(f"  • {reason.replace('_', ' ').title()}: {len(players)} ({percentage:.1f}%)")
        
        print(f"\n🏢 TOP UNMAPPED CLUBS (by player impact):")
        unmapped_clubs = sorted(
            self.skipped_analysis['unmapped_clubs'].values(),
            key=lambda x: x['player_count'], reverse=True
        )[:8]
        for club in unmapped_clubs:
            print(f"  • {club['name']}: {club['player_count']} players")
        
        print(f"\n🏆 TOP UNMAPPED SERIES (by player impact):")
        unmapped_series = sorted(
            self.skipped_analysis['unmapped_series'].values(),
            key=lambda x: x['player_count'], reverse=True
        )[:5]
        for series in unmapped_series:
            print(f"  • {series['name']}: {series['player_count']} players")
        
        print(f"\n💡 TOP RECOMMENDATIONS:")
        for i, rec in enumerate(self.skipped_analysis['recommendations'][:3], 1):
            print(f"  {i}. [{rec['priority']}] {rec['title']}")
            print(f"     {rec['description']}")
            print(f"     Action: {rec['action']}")
        
        # Calculate recovery potential
        club_recovery = sum(club['player_count'] for club in self.skipped_analysis['unmapped_clubs'].values())
        series_recovery = sum(series['player_count'] for series in self.skipped_analysis['unmapped_series'].values())
        
        print(f"\n🎯 RECOVERY POTENTIAL:")
        print(f"  • Mapping all missing clubs: +{club_recovery} players")
        print(f"  • Mapping all missing series: +{series_recovery} players")
        print(f"  • Total potential recovery: {min(club_recovery + series_recovery, total)} players")
        print(f"  • Potential final coverage: {((2431 + min(club_recovery + series_recovery, total)) / 2964 * 100):.1f}%")

def main():
    """Generate comprehensive analysis of skipped players"""
    logger.info("🔍 COMPREHENSIVE SKIPPED PLAYERS ANALYSIS")
    logger.info("="*80)
    
    analyzer = SkippedPlayersAnalyzer()
    
    try:
        analyzer.connect_databases()
        
        # Step 1: Load existing mappings
        analyzer.load_existing_mappings()
        
        # Step 2: Analyze all players
        skipped_players, migrated_players = analyzer.analyze_all_players()
        
        # Step 3: Categorize skipped players
        analyzer.categorize_skipped_players(skipped_players)
        
        # Step 4: Analyze unmapped entities
        analyzer.analyze_unmapped_entities(skipped_players)
        
        # Step 5: Analyze data quality
        analyzer.analyze_data_quality(skipped_players)
        
        # Step 6: Generate recommendations
        analyzer.generate_recommendations()
        
        # Step 7: Save detailed report
        report_path = analyzer.save_detailed_report()
        
        # Step 8: Print executive summary
        analyzer.print_executive_summary()
        
        logger.info(f"\n✅ ANALYSIS COMPLETE!")
        logger.info(f"📄 Detailed report saved to: {report_path}")
        
        return True
        
    finally:
        analyzer.disconnect_databases()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 