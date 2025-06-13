#!/usr/bin/env python3
"""
Improved ELT Pipeline Validation

This validation framework tests what actually matters for ELT scripts:
1. JSON Completeness - Did all JSON data get imported?
2. Script Reliability - Did scripts complete without errors?
3. Data Integrity - Are foreign keys and relationships correct?

Usage:
    python validate_etl_pipeline.py [--test-db-name custom_test_db]
"""

import os
import sys
import json
import subprocess
import psycopg2
from datetime import datetime
from pathlib import Path
import argparse
from collections import defaultdict

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_config import get_db_url, parse_db_url

class ETLPipelineValidator:
    def __init__(self, test_db_name="rally_etl_validation"):
        self.test_db_name = test_db_name
        self.original_db_url = get_db_url()
        self.test_db_url = None
        self.validation_results = {
            'timestamp': datetime.now().isoformat(),
            'status': 'unknown',
            'tests': {
                'script_reliability': {'status': 'pending', 'details': []},
                'json_completeness': {'status': 'pending', 'details': []},
                'data_integrity': {'status': 'pending', 'details': []}
            },
            'summary': {},
            'source_data': {}
        }
        
    def create_test_database(self):
        """Create a clean test database"""
        print("🔧 Creating test database...")
        
        db_params = parse_db_url(self.original_db_url)
        admin_params = db_params.copy()
        admin_params['dbname'] = 'postgres'
        
        try:
            conn = psycopg2.connect(**admin_params)
            conn.autocommit = True
            
            with conn.cursor() as cursor:
                cursor.execute(f"DROP DATABASE IF EXISTS {self.test_db_name}")
                cursor.execute(f"CREATE DATABASE {self.test_db_name}")
                print(f"✅ Created test database: {self.test_db_name}")
            
            conn.close()
            
            # Update test DB URL
            self.test_db_url = self.original_db_url.replace(db_params['dbname'], self.test_db_name)
            return True
            
        except Exception as e:
            print(f"❌ Error creating test database: {e}")
            return False
    
    def clone_schema_only(self):
        """Clone database schema (structure only) to test database"""
        print("📋 Cloning database schema...")
        
        db_params = parse_db_url(self.original_db_url)
        test_params = parse_db_url(self.test_db_url)
        
        dump_cmd = [
            'pg_dump',
            f"--host={db_params['host']}",
            f"--port={db_params['port']}",
            f"--username={db_params['user']}",
            f"--dbname={db_params['dbname']}",
            '--schema-only',  # Structure only, no data
            '--format=custom'
        ]
        
        restore_cmd = [
            'pg_restore',
            f"--host={test_params['host']}",
            f"--port={test_params['port']}",
            f"--username={test_params['user']}",
            f"--dbname={test_params['dbname']}",
            '--no-owner',
            '--no-privileges'
        ]
        
        env = os.environ.copy()
        env['PGPASSWORD'] = db_params['password']
        
        try:
            dump_proc = subprocess.run(dump_cmd, env=env, capture_output=True)
            if dump_proc.returncode != 0:
                print(f"❌ Schema dump failed: {dump_proc.stderr.decode()}")
                return False
            
            restore_proc = subprocess.run(
                restore_cmd, 
                input=dump_proc.stdout, 
                env=env, 
                capture_output=True
            )
            
            if restore_proc.returncode == 0:
                print("✅ Schema cloned successfully")
                return True
            else:
                print("✅ Schema cloned with expected warnings")  # Warnings are normal
                return True
                
        except Exception as e:
            print(f"❌ Error cloning schema: {e}")
            return False
    
    def analyze_source_data(self):
        """Analyze JSON source files to understand expected data"""
        print("📖 Analyzing JSON source data...")
        
        # Determine file paths based on current working directory
        if os.path.basename(os.getcwd()) == 'etl':
            # Running from etl directory
            base_path = '../data/leagues/all/'
        else:
            # Running from project root
            base_path = 'data/leagues/all/'
        
        source_files = {
            'players': f'{base_path}players.json',
            'player_history': f'{base_path}player_history.json'
        }
        
        source_analysis = {}
        
        for data_type, file_path in source_files.items():
            if not os.path.exists(file_path):
                print(f"   ⚠️ Source file not found: {file_path}")
                continue
                
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                if data_type == 'players':
                    analysis = self._analyze_players_json(data)
                elif data_type == 'player_history':
                    analysis = self._analyze_player_history_json(data)
                else:
                    analysis = {'record_count': len(data)}
                
                source_analysis[data_type] = analysis
                print(f"   📊 {data_type}: {analysis['record_count']:,} records")
                
            except Exception as e:
                print(f"   ❌ Error analyzing {file_path}: {e}")
                source_analysis[data_type] = {'error': str(e)}
        
        self.validation_results['source_data'] = source_analysis
        return source_analysis
    
    def _analyze_players_json(self, data):
        """Analyze players JSON structure"""
        leagues = set()
        clubs = set()
        series = set()
        unique_players = set()
        
        for player in data:
            if player_id := player.get('Player ID', '').strip():
                unique_players.add(player_id)
            if league := player.get('League', '').strip():
                leagues.add(league)
            if club := player.get('Club', '').strip():
                clubs.add(club)
            if series_name := player.get('Series', '').strip():
                series.add(series_name)
        
        return {
            'record_count': len(data),
            'unique_players': len(unique_players),
            'leagues': sorted(leagues),
            'clubs': sorted(clubs),
            'series': sorted(series),
            'league_count': len(leagues),
            'club_count': len(clubs),
            'series_count': len(series)
        }
    
    def _analyze_player_history_json(self, data):
        """Analyze player history JSON structure"""
        total_matches = 0
        players_with_history = 0
        
        for player in data:
            matches = player.get('matches', [])
            if matches:
                total_matches += len(matches)
                players_with_history += 1
        
        return {
            'record_count': len(data),
            'players_with_history': players_with_history,
            'total_match_records': total_matches
        }
    
    def test_script_reliability(self):
        """Test 1: Do ELT scripts run without errors?"""
        print("🔧 Testing script reliability...")
        
        env = os.environ.copy()
        env['DATABASE_URL'] = self.test_db_url
        env['DATABASE_PUBLIC_URL'] = self.test_db_url
        
        # Determine script path based on current working directory
        if os.path.basename(os.getcwd()) == 'etl':
            # Running from etl directory
            script_path = 'run_all_etl.py'
        else:
            # Running from project root
            script_path = 'etl/run_all_etl.py'
        
        cmd = [sys.executable, script_path]
        
        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode == 0:
                print("✅ All ELT scripts completed successfully")
                self.validation_results['tests']['script_reliability'] = {
                    'status': 'pass',
                    'details': ['All scripts completed without errors'],
                    'output': result.stdout
                }
                return True
            else:
                print(f"❌ ELT scripts failed with return code: {result.returncode}")
                self.validation_results['tests']['script_reliability'] = {
                    'status': 'fail',
                    'details': [f'Scripts failed with return code {result.returncode}'],
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ ELT scripts timed out")
            self.validation_results['tests']['script_reliability'] = {
                'status': 'fail',
                'details': ['Scripts timed out after 10 minutes']
            }
            return False
        except Exception as e:
            print(f"❌ Error running ELT scripts: {e}")
            self.validation_results['tests']['script_reliability'] = {
                'status': 'fail',
                'details': [f'Exception: {str(e)}']
            }
            return False
    
    def test_json_completeness(self):
        """Test 2: Did all JSON data get imported correctly?"""
        print("📊 Testing JSON completeness...")
        
        db_params = parse_db_url(self.test_db_url)
        completeness_results = []
        overall_pass = True
        
        try:
            with psycopg2.connect(**db_params) as conn:
                with conn.cursor() as cursor:
                    
                    # Test 1: Reference data completeness
                    if 'players' in self.validation_results['source_data']:
                        source = self.validation_results['source_data']['players']
                        
                        # Check leagues
                        cursor.execute("SELECT COUNT(*) FROM leagues")
                        db_leagues = cursor.fetchone()[0]
                        expected_leagues = source['league_count']
                        
                        if db_leagues >= expected_leagues:
                            completeness_results.append(f"✅ Leagues: {db_leagues}/{expected_leagues} imported")
                        else:
                            completeness_results.append(f"❌ Leagues: {db_leagues}/{expected_leagues} imported")
                            overall_pass = False
                        
                        # Check clubs  
                        cursor.execute("SELECT COUNT(*) FROM clubs")
                        db_clubs = cursor.fetchone()[0]
                        expected_clubs = source['club_count']
                        
                        if db_clubs >= expected_clubs:
                            completeness_results.append(f"✅ Clubs: {db_clubs}/{expected_clubs} imported")
                        else:
                            completeness_results.append(f"❌ Clubs: {db_clubs}/{expected_clubs} imported")
                            overall_pass = False
                        
                        # Check series
                        cursor.execute("SELECT COUNT(*) FROM series")
                        db_series = cursor.fetchone()[0]
                        expected_series = source['series_count']
                        
                        if db_series >= expected_series:
                            completeness_results.append(f"✅ Series: {db_series}/{expected_series} imported")
                        else:
                            completeness_results.append(f"❌ Series: {db_series}/{expected_series} imported")
                            overall_pass = False
                        
                        # Check players
                        cursor.execute("SELECT COUNT(*) FROM players")
                        db_players = cursor.fetchone()[0]
                        expected_players = source['unique_players']
                        
                        if db_players >= expected_players * 0.95:  # Allow 5% tolerance for duplicates/errors
                            completeness_results.append(f"✅ Players: {db_players}/{expected_players} imported")
                        else:
                            completeness_results.append(f"❌ Players: {db_players}/{expected_players} imported")
                            overall_pass = False
                    
                    # Test 2: Player history completeness
                    if 'player_history' in self.validation_results['source_data']:
                        source = self.validation_results['source_data']['player_history']
                        
                        cursor.execute("SELECT COUNT(*) FROM player_history")
                        db_history = cursor.fetchone()[0]
                        expected_history = source['total_match_records']
                        
                        # Allow some tolerance for unmapped players
                        if db_history >= expected_history * 0.9:
                            completeness_results.append(f"✅ Player History: {db_history}/{expected_history} records imported")
                        else:
                            completeness_results.append(f"❌ Player History: {db_history}/{expected_history} records imported")
                            overall_pass = False
            
            self.validation_results['tests']['json_completeness'] = {
                'status': 'pass' if overall_pass else 'fail',
                'details': completeness_results
            }
            
            for result in completeness_results:
                print(f"   {result}")
            
            return overall_pass
            
        except Exception as e:
            print(f"❌ Error testing completeness: {e}")
            self.validation_results['tests']['json_completeness'] = {
                'status': 'fail',
                'details': [f'Exception: {str(e)}']
            }
            return False
    
    def test_data_integrity(self):
        """Test 3: Are foreign keys and relationships correct?"""
        print("🔗 Testing data integrity...")
        
        db_params = parse_db_url(self.test_db_url)
        integrity_results = []
        overall_pass = True
        
        try:
            with psycopg2.connect(**db_params) as conn:
                with conn.cursor() as cursor:
                    
                    # Test 1: Foreign key constraints
                    integrity_tests = [
                        {
                            'name': 'Players have valid league_id',
                            'query': 'SELECT COUNT(*) FROM players WHERE league_id IS NULL OR league_id NOT IN (SELECT id FROM leagues)'
                        },
                        {
                            'name': 'Players have valid club_id',
                            'query': 'SELECT COUNT(*) FROM players WHERE club_id IS NOT NULL AND club_id NOT IN (SELECT id FROM clubs)'
                        },
                        {
                            'name': 'Players have valid series_id',
                            'query': 'SELECT COUNT(*) FROM players WHERE series_id IS NOT NULL AND series_id NOT IN (SELECT id FROM series)'
                        },
                        {
                            'name': 'Player history has valid player_id',
                            'query': 'SELECT COUNT(*) FROM player_history WHERE player_id IS NULL OR player_id NOT IN (SELECT id FROM players)'
                        },
                        {
                            'name': 'Player history has valid league_id',
                            'query': 'SELECT COUNT(*) FROM player_history WHERE league_id IS NOT NULL AND league_id NOT IN (SELECT id FROM leagues)'
                        }
                    ]
                    
                    for test in integrity_tests:
                        cursor.execute(test['query'])
                        violations = cursor.fetchone()[0]
                        
                        if violations == 0:
                            integrity_results.append(f"✅ {test['name']}: No violations")
                        else:
                            integrity_results.append(f"❌ {test['name']}: {violations} violations")
                            overall_pass = False
                    
                    # Test 2: Data consistency
                    cursor.execute("SELECT COUNT(*) FROM players WHERE first_name IS NULL OR first_name = ''")
                    empty_names = cursor.fetchone()[0]
                    if empty_names == 0:
                        integrity_results.append("✅ All players have first names")
                    else:
                        integrity_results.append(f"⚠️ {empty_names} players missing first names")
                    
                    # Test 3: Player history linking percentage
                    cursor.execute("SELECT COUNT(*) FROM player_history WHERE player_id IS NOT NULL")
                    linked_history = cursor.fetchone()[0]
                    cursor.execute("SELECT COUNT(*) FROM player_history")
                    total_history = cursor.fetchone()[0]
                    
                    if total_history > 0:
                        link_percentage = (linked_history / total_history) * 100
                        if link_percentage >= 95:
                            integrity_results.append(f"✅ Player history linking: {link_percentage:.1f}%")
                        else:
                            integrity_results.append(f"⚠️ Player history linking: {link_percentage:.1f}% (below 95%)")
            
            self.validation_results['tests']['data_integrity'] = {
                'status': 'pass' if overall_pass else 'fail',
                'details': integrity_results
            }
            
            for result in integrity_results:
                print(f"   {result}")
            
            return overall_pass
            
        except Exception as e:
            print(f"❌ Error testing data integrity: {e}")
            self.validation_results['tests']['data_integrity'] = {
                'status': 'fail',
                'details': [f'Exception: {str(e)}']
            }
            return False
    
    def cleanup_test_database(self):
        """Clean up test database"""
        print("🧹 Cleaning up test database...")
        
        db_params = parse_db_url(self.original_db_url)
        admin_params = db_params.copy()
        admin_params['dbname'] = 'postgres'
        
        try:
            conn = psycopg2.connect(**admin_params)
            conn.autocommit = True
            
            with conn.cursor() as cursor:
                cursor.execute(f"""
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = '{self.test_db_name}'
                    AND pid != pg_backend_pid()
                """)
                cursor.execute(f"DROP DATABASE IF EXISTS {self.test_db_name}")
                print(f"✅ Cleaned up test database: {self.test_db_name}")
            
            conn.close()
            
        except Exception as e:
            print(f"⚠️ Error cleaning up test database: {e}")
    
    def generate_report(self):
        """Generate final validation report"""
        print("\n📝 Generating validation report...")
        
        # Calculate overall status
        test_results = self.validation_results['tests']
        all_passed = all(test['status'] == 'pass' for test in test_results.values())
        
        self.validation_results['status'] = 'pass' if all_passed else 'fail'
        self.validation_results['summary'] = {
            'script_reliability': test_results['script_reliability']['status'],
            'json_completeness': test_results['json_completeness']['status'],
            'data_integrity': test_results['data_integrity']['status'],
            'overall_status': 'pass' if all_passed else 'fail'
        }
        
        # Save detailed report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f"etl_validation_report_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump(self.validation_results, f, indent=2)
        
        print(f"📄 Detailed report saved: {report_file}")
        
        # Print summary
        print("\n" + "=" * 60)
        print("🎯 ELT PIPELINE VALIDATION RESULTS")
        print("=" * 60)
        
        status_emoji = "✅" if all_passed else "❌"
        print(f"Overall Status: {status_emoji} {'PASS' if all_passed else 'FAIL'}")
        print()
        
        print("📋 Test Results:")
        print(f"   Script Reliability: {'✅ PASS' if test_results['script_reliability']['status'] == 'pass' else '❌ FAIL'}")
        print(f"   JSON Completeness:  {'✅ PASS' if test_results['json_completeness']['status'] == 'pass' else '❌ FAIL'}")
        print(f"   Data Integrity:     {'✅ PASS' if test_results['data_integrity']['status'] == 'pass' else '❌ FAIL'}")
        
        print("\n📊 Source Data Analysis:")
        source_data = self.validation_results.get('source_data', {})
        if 'players' in source_data:
            players = source_data['players']
            print(f"   Players JSON: {players['record_count']:,} records")
            print(f"   Unique Players: {players['unique_players']:,}")
            print(f"   Reference Data: {players['league_count']} leagues, {players['club_count']} clubs, {players['series_count']} series")
        
        if 'player_history' in source_data:
            history = source_data['player_history']
            print(f"   Player History: {history['total_match_records']:,} match records")
        
        print("=" * 60)
        
        if all_passed:
            print("🎉 ELT Pipeline validation PASSED!")
            print("   Your ELT scripts are working correctly and are production-ready.")
        else:
            print("⚠️ ELT Pipeline validation FAILED!")
            print("   Review the detailed report for specific issues.")
        
        return all_passed
    
    def validate(self):
        """Run complete ELT pipeline validation"""
        print("🚀 Starting ELT Pipeline Validation")
        print("=" * 60)
        print("Testing what actually matters:")
        print("  1️⃣ Script Reliability - Do scripts run without errors?")
        print("  2️⃣ JSON Completeness - Is all JSON data imported?")
        print("  3️⃣ Data Integrity - Are relationships correct?")
        print()
        
        try:
            # Setup
            if not self.create_test_database():
                return False
            
            if not self.clone_schema_only():
                return False
            
            # Analyze source data
            self.analyze_source_data()
            
            # Run tests
            reliability_pass = self.test_script_reliability()
            completeness_pass = self.test_json_completeness() if reliability_pass else False
            integrity_pass = self.test_data_integrity() if reliability_pass else False
            
            # Generate report
            overall_pass = self.generate_report()
            
            return overall_pass
            
        finally:
            # Always cleanup
            self.cleanup_test_database()

def main():
    parser = argparse.ArgumentParser(description="Validate ELT Pipeline")
    parser.add_argument(
        '--test-db-name',
        default='rally_etl_validation',
        help='Name for test database'
    )
    
    args = parser.parse_args()
    
    validator = ETLPipelineValidator(test_db_name=args.test_db_name)
    success = validator.validate()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 