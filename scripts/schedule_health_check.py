#!/usr/bin/env python3
"""
Schedule Data Health Check
==========================

Comprehensive health check for schedule data to detect issues early.
This script monitors data quality and sends alerts when issues are detected.

Usage:
    python3 scripts/schedule_health_check.py [--alert] [--detailed]
"""

import sys
import os
import argparse
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from database_utils import execute_query, execute_query_one

# Import SMS notification service if available
try:
    from app.services.notifications_service import send_sms
    SMS_AVAILABLE = True
except ImportError:
    SMS_AVAILABLE = False
    print("⚠️ SMS service not available, alerts will be logged only")

ADMIN_PHONE = "17732138911"

class ScheduleHealthChecker:
    """Comprehensive schedule data health checker"""
    
    def __init__(self, alert_mode=False, detailed_mode=False):
        self.alert_mode = alert_mode
        self.detailed_mode = detailed_mode
        self.health_score = 100
        self.issues = []
        self.warnings = []
        
    def check_teams_without_schedule(self):
        """Check for teams missing schedule data"""
        print("🔍 Checking teams without schedule data...")
        
        query = """
            SELECT t.team_name, t.league_id, l.league_name, COUNT(s.id) as schedule_count
            FROM teams t
            LEFT JOIN schedule s ON (t.id = s.home_team_id OR t.id = s.away_team_id)
            LEFT JOIN leagues l ON t.league_id = l.id
            GROUP BY t.id, t.team_name, t.league_id, l.league_name
            HAVING COUNT(s.id) = 0
            ORDER BY l.league_name, t.team_name
        """
        
        result = execute_query(query)
        
        if result:
            print(f"❌ Found {len(result)} teams without schedule data")
            self.health_score -= len(result) * 2  # -2 points per missing team
            
            if self.detailed_mode:
                for team in result:
                    print(f"  - {team['team_name']} ({team['league_name']})")
            
            self.issues.append(f"{len(result)} teams missing schedule data")
        else:
            print("✅ All teams have schedule data")
        
        return result
    
    def check_schedule_records_with_null_team_id(self):
        """Check for schedule records with NULL team_id values"""
        print("🔍 Checking schedule records with NULL team_id...")
        
        query = """
            SELECT COUNT(*) as count
            FROM schedule
            WHERE home_team_id IS NULL AND away_team_id IS NULL
        """
        
        result = execute_query_one(query)
        null_count = result['count'] if result else 0
        
        if null_count > 0:
            print(f"❌ Found {null_count} schedule records with NULL team_id")
            self.health_score -= null_count * 0.5  # -0.5 points per NULL record
            
            if self.detailed_mode:
                # Get sample records
                sample_query = """
                    SELECT match_date, home_team, away_team, league_id
                    FROM schedule
                    WHERE home_team_id IS NULL AND away_team_id IS NULL
                    LIMIT 5
                """
                samples = execute_query(sample_query)
                for sample in samples:
                    print(f"  - {sample['match_date']}: {sample['home_team']} vs {sample['away_team']}")
            
            self.issues.append(f"{null_count} schedule records with NULL team_id")
        else:
            print("✅ No schedule records with NULL team_id")
        
        return null_count
    
    def check_duplicate_schedule_records(self):
        """Check for duplicate schedule records"""
        print("🔍 Checking for duplicate schedule records...")
        
        query = """
            SELECT match_date, home_team, away_team, league_id, COUNT(*) as count
            FROM schedule
            GROUP BY match_date, home_team, away_team, league_id
            HAVING COUNT(*) > 1
            ORDER BY count DESC
        """
        
        result = execute_query(query)
        
        if result:
            total_duplicates = sum(record['count'] - 1 for record in result)
            print(f"❌ Found {len(result)} groups of duplicate records ({total_duplicates} total duplicates)")
            self.health_score -= total_duplicates * 0.1  # -0.1 points per duplicate
            
            if self.detailed_mode:
                for record in result[:5]:  # Show top 5
                    print(f"  - {record['match_date']}: {record['home_team']} vs {record['away_team']} ({record['count']} duplicates)")
            
            self.issues.append(f"{total_duplicates} duplicate schedule records")
        else:
            print("✅ No duplicate schedule records found")
        
        return len(result)
    
    def check_orphaned_schedule_records(self):
        """Check for orphaned schedule records (invalid team references)"""
        print("🔍 Checking for orphaned schedule records...")
        
        query = """
            SELECT COUNT(*) as count
            FROM schedule s
            LEFT JOIN teams t1 ON s.home_team_id = t1.id
            LEFT JOIN teams t2 ON s.away_team_id = t2.id
            WHERE (s.home_team_id IS NOT NULL AND t1.id IS NULL)
               OR (s.away_team_id IS NOT NULL AND t2.id IS NULL)
        """
        
        result = execute_query_one(query)
        orphaned_count = result['count'] if result else 0
        
        if orphaned_count > 0:
            print(f"❌ Found {orphaned_count} orphaned schedule records")
            self.health_score -= orphaned_count * 1  # -1 point per orphaned record
            
            if self.detailed_mode:
                # Get sample orphaned records
                sample_query = """
                    SELECT s.match_date, s.home_team, s.away_team, s.home_team_id, s.away_team_id
                    FROM schedule s
                    LEFT JOIN teams t1 ON s.home_team_id = t1.id
                    LEFT JOIN teams t2 ON s.away_team_id = t2.id
                    WHERE (s.home_team_id IS NOT NULL AND t1.id IS NULL)
                       OR (s.away_team_id IS NOT NULL AND t2.id IS NULL)
                    LIMIT 5
                """
                samples = execute_query(sample_query)
                for sample in samples:
                    print(f"  - {sample['match_date']}: {sample['home_team']} vs {sample['away_team']}")
            
            self.issues.append(f"{orphaned_count} orphaned schedule records")
        else:
            print("✅ No orphaned schedule records found")
        
        return orphaned_count
    
    def check_schedule_coverage_by_league(self):
        """Check schedule coverage by league"""
        print("🔍 Checking schedule coverage by league...")
        
        query = """
            SELECT 
                l.league_name,
                COUNT(DISTINCT t.id) as total_teams,
                COUNT(DISTINCT CASE WHEN s.id IS NOT NULL THEN t.id END) as teams_with_schedule,
                ROUND(
                    COUNT(DISTINCT CASE WHEN s.id IS NOT NULL THEN t.id END) * 100.0 / 
                    COUNT(DISTINCT t.id), 2
                ) as coverage_percentage
            FROM leagues l
            JOIN teams t ON l.id = t.league_id
            LEFT JOIN schedule s ON (t.id = s.home_team_id OR t.id = s.away_team_id)
            GROUP BY l.id, l.league_name
            ORDER BY coverage_percentage ASC
        """
        
        result = execute_query(query)
        
        coverage_issues = []
        for league in result:
            coverage = league['coverage_percentage']
            if coverage < 95:  # Alert if less than 95% coverage
                print(f"⚠️ {league['league_name']}: {coverage}% coverage ({league['teams_with_schedule']}/{league['total_teams']} teams)")
                self.health_score -= float(100 - coverage) * 0.5  # -0.5 points per percentage point below 100%
                coverage_issues.append(f"{league['league_name']}: {coverage}% coverage")
            else:
                print(f"✅ {league['league_name']}: {coverage}% coverage")
        
        if coverage_issues:
            self.warnings.append(f"Low coverage in leagues: {', '.join(coverage_issues)}")
        
        return result
    
    def check_recent_schedule_activity(self):
        """Check for recent schedule activity"""
        print("🔍 Checking recent schedule activity...")
        
        query = """
            SELECT 
                COUNT(*) as total_matches,
                MIN(match_date) as earliest_date,
                MAX(match_date) as latest_date
            FROM schedule
            WHERE match_date >= CURRENT_DATE - INTERVAL '30 days'
        """
        
        result = execute_query_one(query)
        
        if result and result['total_matches'] > 0:
            print(f"✅ Recent activity: {result['total_matches']} matches in last 30 days")
            print(f"   Date range: {result['earliest_date']} to {result['latest_date']}")
        else:
            print("⚠️ No recent schedule activity found")
            self.health_score -= 10  # -10 points for no recent activity
            self.warnings.append("No recent schedule activity")
        
        return result
    
    def calculate_health_score(self):
        """Calculate overall health score"""
        # Ensure health score doesn't go below 0
        self.health_score = max(0, self.health_score)
        
        # Determine health status
        if self.health_score >= 90:
            status = "🟢 EXCELLENT"
        elif self.health_score >= 75:
            status = "🟡 GOOD"
        elif self.health_score >= 50:
            status = "🟠 FAIR"
        else:
            status = "🔴 POOR"
        
        return self.health_score, status
    
    def send_alert(self, message):
        """Send alert if in alert mode"""
        if not self.alert_mode:
            return
        
        if SMS_AVAILABLE:
            try:
                send_sms(ADMIN_PHONE, f"Rally Schedule Health Alert: {message}")
                print(f"📱 Alert sent to {ADMIN_PHONE}")
            except Exception as e:
                print(f"❌ Failed to send SMS alert: {e}")
        else:
            print(f"📱 Alert (SMS not available): {message}")
    
    def run_health_check(self):
        """Run comprehensive health check"""
        print("🎯 Schedule Data Health Check")
        print("=" * 50)
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Run all health checks
        missing_teams = self.check_teams_without_schedule()
        null_team_records = self.check_schedule_records_with_null_team_id()
        duplicate_records = self.check_duplicate_schedule_records()
        orphaned_records = self.check_orphaned_schedule_records()
        self.check_schedule_coverage_by_league()
        recent_activity = self.check_recent_schedule_activity()
        
        # Calculate final health score
        health_score, status = self.calculate_health_score()
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 HEALTH CHECK SUMMARY")
        print("=" * 50)
        print(f"🏥 Overall Health Score: {health_score}/100 {status}")
        print(f"📊 Teams missing schedule data: {len(missing_teams)}")
        print(f"📊 Records with NULL team_id: {null_team_records}")
        print(f"📊 Duplicate record groups: {duplicate_records}")
        print(f"📊 Orphaned records: {orphaned_records}")
        
        if self.issues:
            print(f"\n❌ Issues Found ({len(self.issues)}):")
            for issue in self.issues:
                print(f"  - {issue}")
        
        if self.warnings:
            print(f"\n⚠️ Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        # Send alert if health is poor
        if health_score < 75:
            alert_message = f"Health score: {health_score}/100. Issues: {len(self.issues)}"
            self.send_alert(alert_message)
        
        return health_score, self.issues, self.warnings

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Schedule Data Health Check")
    parser.add_argument("--alert", action="store_true", help="Send SMS alerts for issues")
    parser.add_argument("--detailed", action="store_true", help="Show detailed issue information")
    
    args = parser.parse_args()
    
    # Run health check
    checker = ScheduleHealthChecker(alert_mode=args.alert, detailed_mode=args.detailed)
    health_score, issues, warnings = checker.run_health_check()
    
    # Exit with error code if issues found
    if issues:
        print(f"\n❌ Health check failed with {len(issues)} issues")
        sys.exit(1)
    else:
        print(f"\n✅ Health check passed (score: {health_score}/100)")
        sys.exit(0)

if __name__ == "__main__":
    main() 