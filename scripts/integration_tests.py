#!/usr/bin/env python3
"""
Integration Tests for User-Facing Features
==========================================

End-to-end tests that verify critical user workflows function correctly
after ETL imports. These tests simulate real user interactions to ensure
the system works from a user perspective.
"""

import sys
import os
from datetime import datetime
import traceback
from typing import Dict, List, Any

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from database_utils import execute_query, execute_query_one

class IntegrationTester:
    def __init__(self):
        self.test_results = []
        self.failures = []
        self.start_time = datetime.now()
        
    def log_test(self, test_name: str, status: str, details: str = "", data: Any = None):
        """Log test result"""
        result = {
            'test': test_name,
            'status': status,  # PASS, FAIL
            'details': details,
            'data': data,
            'timestamp': datetime.now()
        }
        self.test_results.append(result)
        
        if status == 'FAIL':
            self.failures.append(result)
            
        # Print real-time results
        icon = "✅" if status == "PASS" else "❌"
        print(f"{icon} {test_name}: {status}")
        if details:
            print(f"   {details}")

    def test_my_series_page_data(self):
        """Test that my-series page can load standings data"""
        print("\n📊 TESTING MY-SERIES PAGE")
        print("=" * 40)
        
        try:
            # Simulate user accessing my-series for CNSWPL Division 12
            test_user_series = "Division 12"
            test_league_id = "CNSWPL"
            
            # Test series stats API data (what the page fetches)
            series_standings = execute_query("""
                SELECT s.team, s.points, s.matches_won, s.matches_lost,
                       l.league_id
                FROM series_stats s
                JOIN leagues l ON s.league_id = l.id
                WHERE s.series = %s AND l.league_id = %s
                ORDER BY s.points DESC, s.team ASC
            """, [test_user_series, test_league_id])
            
            if len(series_standings) >= 5:
                self.log_test(
                    "My-series standings data",
                    "PASS",
                    f"Found {len(series_standings)} teams in {test_user_series}",
                    {'team_count': len(series_standings), 'top_team': series_standings[0]['team']}
                )
                
                # Test that teams have reasonable data
                teams_with_matches = [t for t in series_standings if t['matches_won'] + t['matches_lost'] > 0]
                if len(teams_with_matches) >= len(series_standings) * 0.8:
                    self.log_test("Teams have match data", "PASS", f"{len(teams_with_matches)}/{len(series_standings)} teams have played matches")
                else:
                    self.log_test("Teams have match data", "FAIL", f"Only {len(teams_with_matches)}/{len(series_standings)} teams have match data")
                    
            elif len(series_standings) > 0:
                self.log_test(
                    "My-series standings data",
                    "FAIL",
                    f"Only {len(series_standings)} teams found in {test_user_series} (need at least 5 for realistic standings)"
                )
            else:
                self.log_test(
                    "My-series standings data",
                    "FAIL",
                    f"No teams found in {test_user_series} for {test_league_id}"
                )
                
        except Exception as e:
            self.log_test("My-series page", "FAIL", f"Error testing series data: {str(e)}")

    def test_analyze_me_page_data(self):
        """Test that analyze-me page can load player analysis data"""
        print("\n🎯 TESTING ANALYZE-ME PAGE")
        print("=" * 40)
        
        try:
            # Find a test player with sufficient match history
            test_player = execute_query_one("""
                SELECT p.tenniscores_player_id, p.first_name, p.last_name, 
                       COUNT(m.id) as match_count,
                       l.league_id, p.club_id, p.series_id
                FROM players p
                JOIN leagues l ON p.league_id = l.id
                LEFT JOIN match_scores m ON (
                    m.home_player_1_id = p.tenniscores_player_id OR 
                    m.home_player_2_id = p.tenniscores_player_id OR
                    m.away_player_1_id = p.tenniscores_player_id OR 
                    m.away_player_2_id = p.tenniscores_player_id
                )
                WHERE p.tenniscores_player_id IS NOT NULL
                GROUP BY p.tenniscores_player_id, p.first_name, p.last_name, l.league_id, p.club_id, p.series_id
                HAVING COUNT(m.id) >= 5
                ORDER BY COUNT(m.id) DESC
                LIMIT 1
            """)
            
            if test_player:
                player_name = f"{test_player['first_name']} {test_player['last_name']}"
                match_count = test_player['match_count']
                
                self.log_test(
                    "Analyze-me player data",
                    "PASS",
                    f"Found test player {player_name} with {match_count} matches"
                )
                
                # Test player statistics calculation
                player_stats = execute_query_one("""
                    SELECT 
                        COUNT(CASE WHEN ((m.home_player_1_id = %s OR m.home_player_2_id = %s) AND m.winner = 'home') OR
                                        ((m.away_player_1_id = %s OR m.away_player_2_id = %s) AND m.winner = 'away') THEN 1 END) as wins,
                        COUNT(CASE WHEN ((m.home_player_1_id = %s OR m.home_player_2_id = %s) AND m.winner = 'away') OR
                                        ((m.away_player_1_id = %s OR m.away_player_2_id = %s) AND m.winner = 'home') THEN 1 END) as losses
                    FROM match_scores m
                    WHERE m.home_player_1_id = %s OR m.home_player_2_id = %s OR
                          m.away_player_1_id = %s OR m.away_player_2_id = %s
                """, [test_player['tenniscores_player_id']] * 12)
                
                if player_stats and (player_stats['wins'] + player_stats['losses']) > 0:
                    win_rate = round((player_stats['wins'] / (player_stats['wins'] + player_stats['losses'])) * 100, 1)
                    self.log_test(
                        "Player statistics calculation",
                        "PASS",
                        f"{player_name}: {player_stats['wins']}-{player_stats['losses']} ({win_rate}%)"
                    )
                else:
                    self.log_test("Player statistics calculation", "FAIL", "Cannot calculate player win-loss record")
                    
            else:
                self.log_test("Analyze-me player data", "FAIL", "No players found with sufficient match history (need >= 5 matches)")
                
        except Exception as e:
            self.log_test("Analyze-me page", "FAIL", f"Error testing player analysis: {str(e)}")

    def test_my_team_page_data(self):
        """Test that my-team page can load team analysis data"""
        print("\n👥 TESTING MY-TEAM PAGE")
        print("=" * 40)
        
        try:
            # Find a test team with match data
            test_team = execute_query_one("""
                SELECT s.team, s.points, s.matches_won, s.matches_lost,
                       l.league_id, COUNT(m.id) as actual_matches
                FROM series_stats s
                JOIN leagues l ON s.league_id = l.id
                LEFT JOIN match_scores m ON (m.home_team = s.team OR m.away_team = s.team)
                WHERE s.matches_won + s.matches_lost > 0
                GROUP BY s.team, s.points, s.matches_won, s.matches_lost, l.league_id
                HAVING COUNT(m.id) >= 5
                ORDER BY COUNT(m.id) DESC
                LIMIT 1
            """)
            
            if test_team:
                team_name = test_team['team']
                points = test_team['points']
                record = f"{test_team['matches_won']}-{test_team['matches_lost']}"
                
                self.log_test(
                    "My-team basic data",
                    "PASS",
                    f"Team {team_name}: {points} pts, {record} record"
                )
                
                # Test team match history
                recent_matches = execute_query("""
                    SELECT match_date, home_team, away_team, winner, scores
                    FROM match_scores
                    WHERE home_team = %s OR away_team = %s
                    ORDER BY match_date DESC
                    LIMIT 5
                """, [team_name, team_name])
                
                if len(recent_matches) >= 3:
                    self.log_test(
                        "Team match history",
                        "PASS",
                        f"Found {len(recent_matches)} recent matches for {team_name}"
                    )
                else:
                    self.log_test(
                        "Team match history",
                        "FAIL",
                        f"Only {len(recent_matches)} matches found for {team_name}"
                    )
                    
            else:
                self.log_test("My-team basic data", "FAIL", "No teams found with sufficient match data")
                
        except Exception as e:
            self.log_test("My-team page", "FAIL", f"Error testing team data: {str(e)}")

    def test_availability_system(self):
        """Test that availability system has required data"""
        print("\n📅 TESTING AVAILABILITY SYSTEM")
        print("=" * 40)
        
        try:
            # Test schedule data for availability
            future_matches = execute_query_one("""
                SELECT COUNT(*) as count FROM schedule
                WHERE match_date >= CURRENT_DATE
            """)
            
            if future_matches['count'] >= 10:
                self.log_test(
                    "Future match schedule",
                    "PASS",
                    f"{future_matches['count']} future matches available for availability setting"
                )
            elif future_matches['count'] > 0:
                self.log_test(
                    "Future match schedule",
                    "FAIL",
                    f"Only {future_matches['count']} future matches (need >= 10 for realistic availability system)"
                )
            else:
                self.log_test("Future match schedule", "FAIL", "No future matches found")
            
            # Test that we can match players to teams for availability
            players_with_teams = execute_query_one("""
                SELECT COUNT(*) as count FROM players p
                JOIN teams t ON p.team_id = t.id
                WHERE p.tenniscores_player_id IS NOT NULL
            """)
            
            if players_with_teams['count'] >= 50:
                self.log_test(
                    "Players linked to teams",
                    "PASS",
                    f"{players_with_teams['count']} players properly linked to teams"
                )
            else:
                self.log_test(
                    "Players linked to teams",
                    "FAIL",
                    f"Only {players_with_teams['count']} players linked to teams"
                )
                
        except Exception as e:
            self.log_test("Availability system", "FAIL", f"Error testing availability data: {str(e)}")

    def test_player_search_functionality(self):
        """Test that player search has sufficient data"""
        print("\n🔍 TESTING PLAYER SEARCH")
        print("=" * 40)
        
        try:
            # Test total searchable players
            searchable_players = execute_query_one("""
                SELECT COUNT(*) as count FROM players
                WHERE first_name IS NOT NULL AND last_name IS NOT NULL
                AND first_name != '' AND last_name != ''
            """)
            
            if searchable_players['count'] >= 100:
                self.log_test(
                    "Searchable player database",
                    "PASS",
                    f"{searchable_players['count']:,} players available for search"
                )
            else:
                self.log_test(
                    "Searchable player database",
                    "FAIL",
                    f"Only {searchable_players['count']} searchable players"
                )
            
            # Test player data completeness
            complete_players = execute_query_one("""
                SELECT COUNT(*) as count FROM players
                WHERE first_name IS NOT NULL AND last_name IS NOT NULL
                AND club_id IS NOT NULL AND series_id IS NOT NULL
                AND league_id IS NOT NULL
            """)
            
            completeness_rate = (complete_players['count'] / searchable_players['count'] * 100) if searchable_players['count'] > 0 else 0
            
            if completeness_rate >= 90:
                self.log_test(
                    "Player data completeness",
                    "PASS",
                    f"{completeness_rate:.1f}% of players have complete profile data"
                )
            else:
                self.log_test(
                    "Player data completeness",
                    "FAIL",
                    f"Only {completeness_rate:.1f}% of players have complete data"
                )
                
        except Exception as e:
            self.log_test("Player search", "FAIL", f"Error testing player search data: {str(e)}")

    def test_league_specific_features(self):
        """Test league-specific functionality"""
        print("\n🏆 TESTING LEAGUE-SPECIFIC FEATURES")
        print("=" * 40)
        
        # Test each major league has sufficient data
        major_leagues = {
            'CNSWPL': {'min_teams': 50, 'min_players': 200},
            'APTA_CHICAGO': {'min_teams': 30, 'min_players': 150},
            'NSTF': {'min_teams': 20, 'min_players': 100}
        }
        
        for league_id, requirements in major_leagues.items():
            try:
                league_data = execute_query_one("""
                    SELECT 
                        (SELECT COUNT(*) FROM series_stats s JOIN leagues l ON s.league_id = l.id WHERE l.league_id = %s) as team_count,
                        (SELECT COUNT(*) FROM players p JOIN leagues l ON p.league_id = l.id WHERE l.league_id = %s) as player_count,
                        (SELECT COUNT(*) FROM match_scores m JOIN leagues l ON m.league_id = l.id WHERE l.league_id = %s) as match_count
                """, [league_id, league_id, league_id])
                
                if league_data:
                    team_count = league_data['team_count']
                    player_count = league_data['player_count']
                    match_count = league_data['match_count']
                    
                    if team_count >= requirements['min_teams'] and player_count >= requirements['min_players']:
                        self.log_test(
                            f"League {league_id} data",
                            "PASS",
                            f"{team_count} teams, {player_count:,} players, {match_count:,} matches"
                        )
                    else:
                        self.log_test(
                            f"League {league_id} data",
                            "FAIL",
                            f"Insufficient data: {team_count} teams (need {requirements['min_teams']}), {player_count} players (need {requirements['min_players']})"
                        )
                else:
                    self.log_test(f"League {league_id} data", "FAIL", "No data found for league")
                    
            except Exception as e:
                self.log_test(f"League {league_id}", "FAIL", f"Error testing league data: {str(e)}")

    def run_all_integration_tests(self):
        """Run all integration tests"""
        print("🧪 STARTING INTEGRATION TESTS")
        print("=" * 50)
        print(f"Timestamp: {self.start_time}")
        print("=" * 50)
        
        try:
            self.test_my_series_page_data()
            self.test_analyze_me_page_data()
            self.test_my_team_page_data()
            self.test_availability_system()
            self.test_player_search_functionality()
            self.test_league_specific_features()
            
        except Exception as e:
            self.log_test("Integration test suite", "FAIL", f"Test suite error: {str(e)}")
            print(f"❌ Test suite error: {str(e)}")
            print(traceback.format_exc())
        
        self.print_test_summary()
        return len(self.failures) == 0

    def print_test_summary(self):
        """Print test summary"""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        print("\n" + "=" * 50)
        print("🧪 INTEGRATION TEST SUMMARY")
        print("=" * 50)
        
        total_tests = len(self.test_results)
        passed = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed = len(self.failures)
        
        print(f"⏱️  Duration: {duration}")
        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        
        if failed == 0:
            print(f"\n🎉 ALL INTEGRATION TESTS PASSED!")
            print("✅ User-facing features are working correctly")
        else:
            print(f"\n🚨 {failed} INTEGRATION TESTS FAILED!")
            print("❌ User-facing features may be broken")
            
        if self.failures:
            print("\n❌ FAILED TESTS:")
            for failure in self.failures:
                print(f"   • {failure['test']}: {failure['details']}")
        
        print("\n📋 RECOMMENDATIONS:")
        if failed == 0:
            print("   ✅ Safe to deploy - all user features tested successfully")
            print("   📈 Consider running these tests regularly")
        else:
            print("   🛑 DO NOT DEPLOY until failed tests are resolved")
            print("   🔧 Check ETL data quality and run validation pipeline")
            print("   📞 Alert development team about user-facing issues")

def main():
    """Main entry point"""
    tester = IntegrationTester()
    success = tester.run_all_integration_tests()
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main()) 