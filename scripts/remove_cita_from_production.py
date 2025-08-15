#!/usr/bin/env python3
"""
Remove CITA Data from Production
===============================

Safely remove all CITA league data from production database.
This includes league, series, teams, players, matches, and user associations.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import sys
from datetime import datetime

class CITARemover:
    def __init__(self):
        self.prod_url = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"
        self.cita_league_id = 4784  # CITA league ID
        self.deleted_counts = {}
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def connect(self):
        """Connect to production database"""
        try:
            self.conn = psycopg2.connect(self.prod_url, cursor_factory=RealDictCursor)
            self.cursor = self.conn.cursor()
            self.log("✅ Connected to production database")
            return True
        except Exception as e:
            self.log(f"❌ Failed to connect: {e}", "ERROR")
            return False
    
    def analyze_cita_data(self):
        """Analyze what CITA data exists"""
        self.log("🔍 Analyzing CITA data for removal")
        
        # Check league
        self.cursor.execute("SELECT * FROM leagues WHERE id = %s", (self.cita_league_id,))
        league = self.cursor.fetchone()
        if league:
            self.log(f"📊 Found CITA league: {league['league_name']} (ID: {league['id']})")
        else:
            self.log("⚠️ CITA league not found", "WARNING")
            return False
        
        # Count series
        self.cursor.execute("SELECT COUNT(*) as count FROM series WHERE league_id = %s", (self.cita_league_id,))
        series_count = self.cursor.fetchone()['count']
        self.log(f"📊 CITA series to remove: {series_count}")
        
        # Count teams
        self.cursor.execute("""
            SELECT COUNT(*) as count 
            FROM teams t 
            JOIN series s ON t.series_id = s.id 
            WHERE s.league_id = %s
        """, (self.cita_league_id,))
        teams_count = self.cursor.fetchone()['count']
        self.log(f"📊 CITA teams to remove: {teams_count}")
        
        # Count players
        self.cursor.execute("""
            SELECT COUNT(*) as count 
            FROM players p 
            WHERE p.league_id = %s
        """, (self.cita_league_id,))
        players_count = self.cursor.fetchone()['count']
        self.log(f"📊 CITA players to remove: {players_count}")
        
        # Count matches
        self.cursor.execute("""
            SELECT COUNT(*) as count 
            FROM match_scores ms 
            WHERE ms.league_id = %s
        """, (self.cita_league_id,))
        matches_count = self.cursor.fetchone()['count']
        self.log(f"📊 CITA matches to remove: {matches_count}")
        
        # Count series stats
        self.cursor.execute("""
            SELECT COUNT(*) as count 
            FROM series_stats ss 
            WHERE ss.league_id = %s
        """, (self.cita_league_id,))
        series_stats_count = self.cursor.fetchone()['count']
        self.log(f"📊 CITA series_stats to remove: {series_stats_count}")
        
        # Count user associations
        self.cursor.execute("""
            SELECT COUNT(*) as count 
            FROM user_player_associations upa 
            JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id 
            WHERE p.league_id = %s
        """, (self.cita_league_id,))
        associations_count = self.cursor.fetchone()['count']
        self.log(f"📊 CITA user associations to remove: {associations_count}")
        
        # Count series_leagues (by series)
        self.cursor.execute("""
            SELECT COUNT(*) as count 
            FROM series_leagues sl 
            WHERE sl.series_id IN (
                SELECT id FROM series WHERE league_id = %s
            )
        """, (self.cita_league_id,))
        series_leagues_by_series_count = self.cursor.fetchone()['count']
        self.log(f"📊 CITA series_leagues (by series) to remove: {series_leagues_by_series_count}")
        
        # Count series_leagues (by league)
        self.cursor.execute("""
            SELECT COUNT(*) as count 
            FROM series_leagues sl 
            WHERE sl.league_id = %s
        """, (self.cita_league_id,))
        series_leagues_by_league_count = self.cursor.fetchone()['count']
        self.log(f"📊 CITA series_leagues (by league) to remove: {series_leagues_by_league_count}")
        
        # Count club_leagues
        self.cursor.execute("""
            SELECT COUNT(*) as count 
            FROM club_leagues cl 
            WHERE cl.league_id = %s
        """, (self.cita_league_id,))
        club_leagues_count = self.cursor.fetchone()['count']
        self.log(f"📊 CITA club_leagues to remove: {club_leagues_count}")
        
        total_records = (series_count + teams_count + players_count + 
                        matches_count + series_stats_count + associations_count + 
                        series_leagues_by_series_count + series_leagues_by_league_count + 
                        club_leagues_count + 1)  # +1 for league
        
        self.log(f"📊 TOTAL CITA RECORDS TO REMOVE: {total_records}")
        
        return total_records > 0
    
    def remove_cita_data(self, dry_run=False):
        """Remove all CITA data in correct order (respecting foreign keys)"""
        if dry_run:
            self.log("🔄 DRY RUN MODE - No changes will be made")
        else:
            self.log("🚀 LIVE MODE - Removing CITA data")
        
        try:
            # Order matters due to foreign key constraints
            removal_steps = [
                {
                    'name': 'user_player_associations',
                    'query': """
                        DELETE FROM user_player_associations 
                        WHERE tenniscores_player_id IN (
                            SELECT tenniscores_player_id FROM players WHERE league_id = %s
                        )
                    """,
                    'params': (self.cita_league_id,)
                },
                {
                    'name': 'series_leagues (by series)',
                    'query': """
                        DELETE FROM series_leagues 
                        WHERE series_id IN (
                            SELECT id FROM series WHERE league_id = %s
                        )
                    """,
                    'params': (self.cita_league_id,)
                },
                {
                    'name': 'series_leagues (by league)',
                    'query': """
                        DELETE FROM series_leagues 
                        WHERE league_id = %s
                    """,
                    'params': (self.cita_league_id,)
                },
                {
                    'name': 'club_leagues',
                    'query': """
                        DELETE FROM club_leagues 
                        WHERE league_id = %s
                    """,
                    'params': (self.cita_league_id,)
                },
                {
                    'name': 'user_contexts (CITA teams)',
                    'query': """
                        DELETE FROM user_contexts 
                        WHERE team_id IN (
                            SELECT t.id FROM teams t 
                            JOIN series s ON t.series_id = s.id 
                            WHERE s.league_id = %s
                        )
                    """,
                    'params': (self.cita_league_id,)
                },
                {
                    'name': 'user_contexts (CITA league)',
                    'query': """
                        DELETE FROM user_contexts 
                        WHERE league_id = %s
                    """,
                    'params': (self.cita_league_id,)
                },
                {
                    'name': 'match_scores',
                    'query': """
                        DELETE FROM match_scores 
                        WHERE league_id = %s
                    """,
                    'params': (self.cita_league_id,)
                },
                {
                    'name': 'series_stats',
                    'query': """
                        DELETE FROM series_stats 
                        WHERE league_id = %s
                    """,
                    'params': (self.cita_league_id,)
                },

                {
                    'name': 'players',
                    'query': """
                        DELETE FROM players 
                        WHERE league_id = %s
                    """,
                    'params': (self.cita_league_id,)
                },
                {
                    'name': 'teams',
                    'query': """
                        DELETE FROM teams 
                        WHERE series_id IN (
                            SELECT id FROM series WHERE league_id = %s
                        )
                    """,
                    'params': (self.cita_league_id,)
                },
                {
                    'name': 'series',
                    'query': """
                        DELETE FROM series 
                        WHERE league_id = %s
                    """,
                    'params': (self.cita_league_id,)
                },
                {
                    'name': 'leagues',
                    'query': """
                        DELETE FROM leagues 
                        WHERE id = %s
                    """,
                    'params': (self.cita_league_id,)
                }
            ]
            
            for step in removal_steps:
                if dry_run:
                    # Just count what would be deleted
                    count_query = step['query'].replace('DELETE FROM', 'SELECT COUNT(*) as count FROM')
                    self.cursor.execute(count_query, step['params'])
                    count = self.cursor.fetchone()['count']
                    self.log(f"🔄 DRY RUN: Would delete {count} records from {step['name']}")
                else:
                    # Actually delete
                    self.cursor.execute(step['query'], step['params'])
                    deleted = self.cursor.rowcount
                    self.deleted_counts[step['name']] = deleted
                    self.log(f"✅ Deleted {deleted} records from {step['name']}")
            
            if not dry_run:
                self.conn.commit()
                self.log("✅ All CITA data removal committed")
            else:
                self.log("🔄 DRY RUN COMPLETED - No changes made")
                
        except Exception as e:
            self.log(f"❌ Error during removal: {e}", "ERROR")
            if not dry_run:
                self.conn.rollback()
            raise
    
    def verify_removal(self):
        """Verify that CITA data has been completely removed"""
        self.log("🔍 Verifying CITA data removal")
        
        # Check if league still exists
        self.cursor.execute("SELECT COUNT(*) as count FROM leagues WHERE id = %s", (self.cita_league_id,))
        league_count = self.cursor.fetchone()['count']
        
        # Check if any series still reference CITA
        self.cursor.execute("SELECT COUNT(*) as count FROM series WHERE league_id = %s", (self.cita_league_id,))
        series_count = self.cursor.fetchone()['count']
        
        # Check if any players still reference CITA
        self.cursor.execute("SELECT COUNT(*) as count FROM players WHERE league_id = %s", (self.cita_league_id,))
        players_count = self.cursor.fetchone()['count']
        
        # Check if any matches still reference CITA
        self.cursor.execute("SELECT COUNT(*) as count FROM match_scores WHERE league_id = %s", (self.cita_league_id,))
        matches_count = self.cursor.fetchone()['count']
        
        # Check remaining leagues
        self.cursor.execute("SELECT id, league_name FROM leagues ORDER BY league_name")
        remaining_leagues = self.cursor.fetchall()
        
        self.log("📊 Verification Results:")
        self.log(f"  - CITA league remaining: {league_count}")
        self.log(f"  - CITA series remaining: {series_count}")
        self.log(f"  - CITA players remaining: {players_count}")
        self.log(f"  - CITA matches remaining: {matches_count}")
        self.log(f"  - Remaining leagues: {len(remaining_leagues)}")
        
        for league in remaining_leagues:
            self.log(f"    • {league['league_name']} (ID: {league['id']})")
        
        success = (league_count == 0 and series_count == 0 and 
                  players_count == 0 and matches_count == 0)
        
        if success:
            self.log("✅ CITA data completely removed!")
            total_deleted = sum(self.deleted_counts.values())
            self.log(f"📊 Total records deleted: {total_deleted}")
            for table, count in self.deleted_counts.items():
                if count > 0:
                    self.log(f"  - {table}: {count}")
        else:
            self.log("❌ CITA data removal incomplete", "ERROR")
        
        return success
    
    def run_removal(self, dry_run=False):
        """Run the complete CITA removal process"""
        if dry_run:
            self.log("🔄 STARTING CITA DATA ANALYSIS (DRY RUN)")
        else:
            self.log("🚀 STARTING CITA DATA REMOVAL (LIVE MODE)")
        
        if not self.connect():
            return False
        
        try:
            has_data = self.analyze_cita_data()
            if not has_data:
                self.log("✅ No CITA data found - nothing to remove")
                return True
            
            self.remove_cita_data(dry_run)
            
            if not dry_run:
                success = self.verify_removal()
                if success:
                    self.log("✅ CITA REMOVAL COMPLETED SUCCESSFULLY")
                else:
                    self.log("⚠️ CITA REMOVAL PARTIALLY COMPLETED", "WARNING")
                return success
            else:
                return True
                
        except Exception as e:
            self.log(f"❌ Removal failed with error: {e}", "ERROR")
            return False
        finally:
            self.conn.close()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Remove CITA data from production')
    parser.add_argument('--dry-run', action='store_true', help='Analyze without making changes')
    args = parser.parse_args()
    
    print("🗑️  PRODUCTION CITA DATA REMOVER")
    print("=" * 50)
    
    remover = CITARemover()
    success = remover.run_removal(dry_run=args.dry_run)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
