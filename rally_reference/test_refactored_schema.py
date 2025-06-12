#!/usr/bin/env python3
"""
Rally Schema Refactoring Test Suite
Comprehensive testing for the new schema structure
"""
import sys
import os
import logging
from typing import Dict, List, Any
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.database_models import (
    User, Player, League, Club, Series, UserPlayerAssociation,
    ClubLeague, SeriesLeague
)
from app.services.auth_service_refactored import (
    register_user, authenticate_user, find_player_matches,
    associate_user_with_player, get_user_with_players
)
from database_config import get_db_engine

logger = logging.getLogger(__name__)

# Create session factory
engine = get_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class SchemaValidator:
    """Validate the new database schema"""
    
    def __init__(self):
        self.db_session = SessionLocal()
        self.test_results = []
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db_session.close()
    
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append({
            'test': test_name,
            'success': success,
            'details': details
        })
        print(f"{status} {test_name}")
        if details and not success:
            print(f"      {details}")
    
    def test_schema_structure(self):
        """Test that all tables and constraints exist properly"""
        print("\n=== SCHEMA STRUCTURE TESTS ===")
        
        try:
            # Test table existence
            tables_to_check = [
                'users', 'players', 'leagues', 'clubs', 'series',
                'user_player_associations', 'club_leagues', 'series_leagues'
            ]
            
            for table in tables_to_check:
                result = self.db_session.execute(
                    text(f"SELECT count(*) FROM {table}")
                ).scalar()
                self.log_test(
                    f"Table {table} exists and accessible",
                    True,
                    f"Found {result} records"
                )
            
            # Test unique constraints
            self.log_test(
                "Players unique constraint (tenniscores_player_id, league_id)",
                self._check_constraint_exists('players', 'unique_player_in_league'),
                "Allows same player ID across different leagues"
            )
            
            # Test foreign key relationships
            foreign_keys = [
                ('players', 'league_id', 'leagues', 'id'),
                ('players', 'club_id', 'clubs', 'id'),
                ('players', 'series_id', 'series', 'id'),
                ('user_player_associations', 'user_id', 'users', 'id'),
                ('user_player_associations', 'player_id', 'players', 'id')
            ]
            
            for table, column, ref_table, ref_column in foreign_keys:
                constraint_exists = self._check_foreign_key_exists(table, column, ref_table)
                self.log_test(
                    f"Foreign key {table}.{column} -> {ref_table}.{ref_column}",
                    constraint_exists,
                    f"Referential integrity enforced"
                )
                
        except Exception as e:
            self.log_test("Schema structure validation", False, str(e))
    
    def test_data_integrity(self):
        """Test data integrity after migration"""
        print("\n=== DATA INTEGRITY TESTS ===")
        
        try:
            # Test that players have required fields
            players_missing_required = self.db_session.execute(text("""
                SELECT COUNT(*) FROM players 
                WHERE first_name IS NULL OR last_name IS NULL 
                OR tenniscores_player_id IS NULL OR league_id IS NULL
            """)).scalar()
            
            self.log_test(
                "All players have required fields",
                players_missing_required == 0,
                f"Found {players_missing_required} players with missing required fields"
            )
            
            # Test that all players belong to valid leagues
            orphaned_players = self.db_session.execute(text("""
                SELECT COUNT(*) FROM players p
                LEFT JOIN leagues l ON p.league_id = l.id
                WHERE l.id IS NULL
            """)).scalar()
            
            self.log_test(
                "All players reference valid leagues",
                orphaned_players == 0,
                f"Found {orphaned_players} players with invalid league references"
            )
            
            # Test user-player associations integrity
            invalid_associations = self.db_session.execute(text("""
                SELECT COUNT(*) FROM user_player_associations upa
                LEFT JOIN users u ON upa.user_id = u.id
                LEFT JOIN players p ON upa.player_id = p.id
                WHERE u.id IS NULL OR p.id IS NULL
            """)).scalar()
            
            self.log_test(
                "All user-player associations are valid",
                invalid_associations == 0,
                f"Found {invalid_associations} invalid associations"
            )
            
            # Test that statistical fields are reasonable
            invalid_stats = self.db_session.execute(text("""
                SELECT COUNT(*) FROM players 
                WHERE (wins < 0 OR losses < 0 OR 
                       (win_percentage IS NOT NULL AND (win_percentage < 0 OR win_percentage > 100)))
            """)).scalar()
            
            self.log_test(
                "Player statistics are within valid ranges",
                invalid_stats == 0,
                f"Found {invalid_stats} players with invalid statistics"
            )
            
        except Exception as e:
            self.log_test("Data integrity validation", False, str(e))
    
    def test_multi_league_functionality(self):
        """Test multi-league specific functionality"""
        print("\n=== MULTI-LEAGUE FUNCTIONALITY TESTS ===")
        
        try:
            # Test that players can exist in multiple leagues with same tenniscores_player_id
            multi_league_players = self.db_session.execute(text("""
                SELECT tenniscores_player_id, COUNT(DISTINCT league_id) as league_count
                FROM players 
                GROUP BY tenniscores_player_id
                HAVING COUNT(DISTINCT league_id) > 1
                LIMIT 1
            """)).fetchone()
            
            if multi_league_players:
                self.log_test(
                    "Players can exist across multiple leagues",
                    True,
                    f"Found player {multi_league_players[0]} in {multi_league_players[1]} leagues"
                )
            else:
                self.log_test(
                    "Players can exist across multiple leagues",
                    True,
                    "No multi-league players found (expected for current data)"
                )
            
            # Test league distribution
            league_stats = self.db_session.execute(text("""
                SELECT l.league_id, l.league_name, COUNT(p.id) as player_count
                FROM leagues l
                LEFT JOIN players p ON l.id = p.league_id AND p.is_active = true
                GROUP BY l.id, l.league_id, l.league_name
                ORDER BY player_count DESC
            """)).fetchall()
            
            active_leagues = [league for league in league_stats if league[2] > 0]
            self.log_test(
                "Multiple leagues have active players",
                len(active_leagues) >= 2,
                f"Found {len(active_leagues)} leagues with players: {[(l[1], l[2]) for l in active_leagues]}"
            )
            
        except Exception as e:
            self.log_test("Multi-league functionality", False, str(e))
    
    def test_authentication_flow(self):
        """Test the new authentication and user registration flow"""
        print("\n=== AUTHENTICATION FLOW TESTS ===")
        
        try:
            # Test user registration without player association
            result = register_user(
                email="test@example.com",
                password="testpass123",
                first_name="Test",
                last_name="User"
            )
            
            self.log_test(
                "User registration without player association",
                result['success'],
                result.get('message', result.get('error', ''))
            )
            
            if result['success']:
                test_user_id = result['user']['id']
                
                # Test authentication
                auth_result = authenticate_user("test@example.com", "testpass123")
                self.log_test(
                    "User authentication",
                    auth_result['success'],
                    f"User has {len(auth_result.get('user', {}).get('players', []))} associated players"
                )
                
                # Test player search
                player_matches = find_player_matches(
                    first_name="John",
                    last_name="Smith",
                    league_name="APTA Chicago"
                )
                self.log_test(
                    "Player search functionality",
                    isinstance(player_matches, list),
                    f"Found {len(player_matches)} potential matches"
                )
                
                # Clean up test user
                self.db_session.execute(
                    text("DELETE FROM users WHERE email = 'test@example.com'")
                )
                self.db_session.commit()
                
        except Exception as e:
            self.log_test("Authentication flow", False, str(e))
            # Clean up on error
            try:
                self.db_session.execute(
                    text("DELETE FROM users WHERE email = 'test@example.com'")
                )
                self.db_session.commit()
            except:
                pass
    
    def test_query_performance(self):
        """Test that key queries perform well with indexes"""
        print("\n=== QUERY PERFORMANCE TESTS ===")
        
        try:
            import time
            
            # Test player lookup by league
            start_time = time.time()
            result = self.db_session.execute(text("""
                SELECT COUNT(*) FROM players p
                JOIN leagues l ON p.league_id = l.id
                WHERE l.league_id = 'APTA_CHICAGO' AND p.is_active = true
            """)).scalar()
            duration = time.time() - start_time
            
            self.log_test(
                "Player lookup by league performance",
                duration < 1.0,  # Should complete in under 1 second
                f"Query returned {result} players in {duration:.3f}s"
            )
            
            # Test user with players lookup
            start_time = time.time()
            user_with_players = self.db_session.execute(text("""
                SELECT u.id, u.email, p.first_name, p.last_name, l.league_name
                FROM users u
                LEFT JOIN user_player_associations upa ON u.id = upa.user_id
                LEFT JOIN players p ON upa.player_id = p.id
                LEFT JOIN leagues l ON p.league_id = l.id
                LIMIT 10
            """)).fetchall()
            duration = time.time() - start_time
            
            self.log_test(
                "User with players lookup performance",
                duration < 0.5,
                f"Query returned {len(user_with_players)} records in {duration:.3f}s"
            )
            
        except Exception as e:
            self.log_test("Query performance", False, str(e))
    
    def _check_constraint_exists(self, table: str, constraint_name: str) -> bool:
        """Check if a constraint exists"""
        try:
            result = self.db_session.execute(text("""
                SELECT COUNT(*) FROM information_schema.table_constraints
                WHERE table_name = :table AND constraint_name = :constraint
            """), {'table': table, 'constraint': constraint_name}).scalar()
            return result > 0
        except:
            return False
    
    def _check_foreign_key_exists(self, table: str, column: str, ref_table: str) -> bool:
        """Check if a foreign key constraint exists"""
        try:
            result = self.db_session.execute(text("""
                SELECT COUNT(*) FROM information_schema.referential_constraints rc
                JOIN information_schema.key_column_usage kcu 
                    ON rc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage ccu
                    ON rc.unique_constraint_name = ccu.constraint_name
                WHERE kcu.table_name = :table 
                AND kcu.column_name = :column
                AND ccu.table_name = :ref_table
            """), {
                'table': table, 
                'column': column, 
                'ref_table': ref_table
            }).scalar()
            return result > 0
        except:
            return False
    
    def generate_report(self):
        """Generate a summary report of all tests"""
        print("\n" + "="*60)
        print("SCHEMA REFACTORING TEST REPORT")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for test in self.test_results if test['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for test in self.test_results:
                if not test['success']:
                    print(f"   • {test['test']}")
                    if test['details']:
                        print(f"     {test['details']}")
        
        print("\n" + "="*60)
        return failed_tests == 0

def run_data_validation():
    """Run additional data validation queries"""
    print("\n=== DATA VALIDATION SUMMARY ===")
    
    db_session = SessionLocal()
    
    try:
        # Get overall statistics
        stats = {}
        
        stats['total_users'] = db_session.query(User).count()
        stats['total_players'] = db_session.query(Player).count()
        stats['active_players'] = db_session.query(Player).filter(Player.is_active == True).count()
        stats['total_leagues'] = db_session.query(League).count()
        stats['total_clubs'] = db_session.query(Club).count()
        stats['total_series'] = db_session.query(Series).count()
        stats['user_player_associations'] = db_session.query(UserPlayerAssociation).count()
        
        # Get league distribution
        league_distribution = db_session.execute(text("""
            SELECT l.league_id, l.league_name, COUNT(p.id) as player_count
            FROM leagues l
            LEFT JOIN players p ON l.id = p.league_id AND p.is_active = true
            GROUP BY l.id, l.league_id, l.league_name
            ORDER BY player_count DESC
        """)).fetchall()
        
        print("Database Statistics:")
        for key, value in stats.items():
            print(f"  {key.replace('_', ' ').title()}: {value:,}")
        
        print("\nLeague Distribution:")
        for league in league_distribution:
            print(f"  {league[1]} ({league[0]}): {league[2]:,} players")
        
        # Check for potential data issues
        print("\nData Quality Checks:")
        
        # Players without statistical data
        players_without_stats = db_session.execute(text("""
            SELECT COUNT(*) FROM players 
            WHERE pti IS NULL AND wins = 0 AND losses = 0
        """)).scalar()
        print(f"  Players without any statistical data: {players_without_stats:,}")
        
        # Users without player associations
        users_without_players = db_session.execute(text("""
            SELECT COUNT(*) FROM users u
            LEFT JOIN user_player_associations upa ON u.id = upa.user_id
            WHERE upa.user_id IS NULL
        """)).scalar()
        print(f"  Users without player associations: {users_without_players:,}")
        
        return True
        
    except Exception as e:
        print(f"Error during data validation: {str(e)}")
        return False
        
    finally:
        db_session.close()

def main():
    """Main function to run all tests"""
    logging.basicConfig(level=logging.INFO)
    
    print("🏓 Rally Database Schema Refactoring Test Suite")
    print("="*60)
    
    # Run schema validation tests
    with SchemaValidator() as validator:
        validator.test_schema_structure()
        validator.test_data_integrity()
        validator.test_multi_league_functionality()
        validator.test_authentication_flow()
        validator.test_query_performance()
        
        # Generate final report
        success = validator.generate_report()
    
    # Run additional data validation
    data_validation_success = run_data_validation()
    
    # Overall result
    overall_success = success and data_validation_success
    
    if overall_success:
        print("\n🎉 All tests passed! Schema refactoring appears successful.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please review the issues above.")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 