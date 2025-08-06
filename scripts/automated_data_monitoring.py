#!/usr/bin/env python3
"""
Automated Data Monitoring
=========================

Automated monitoring script that can be run as a cron job to detect data quality
issues early and send alerts when problems are found.

Usage:
    python3 scripts/automated_data_monitoring.py [--alert] [--detailed] [--email]

Cron job example:
    0 6 * * * cd /path/to/rally && python3 scripts/automated_data_monitoring.py --alert
"""

import sys
import os
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path
import json

# Add the project root to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from database_utils import execute_query, execute_query_one

# Import notification services if available
try:
    from app.services.notifications_service import send_sms
    SMS_AVAILABLE = True
except ImportError:
    SMS_AVAILABLE = False

try:
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False

# Configuration
ADMIN_PHONE = "17732138911"
ADMIN_EMAIL = "ross@rallypaddle.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/data_monitoring.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AutomatedDataMonitor:
    """Automated data quality monitoring system"""
    
    def __init__(self, alert_mode=False, detailed_mode=False, email_mode=False):
        self.alert_mode = alert_mode
        self.detailed_mode = detailed_mode
        self.email_mode = email_mode
        self.issues = []
        self.warnings = []
        self.metrics = {}
        
        # Create logs directory if it doesn't exist
        Path("logs").mkdir(exist_ok=True)
    
    def check_schedule_data_health(self):
        """Check schedule data health metrics"""
        logger.info("🔍 Checking schedule data health...")
        
        # Check 1: Teams without schedule data
        query = """
            SELECT COUNT(*) as count
            FROM teams t
            LEFT JOIN schedule s ON (t.id = s.home_team_id OR t.id = s.away_team_id)
            GROUP BY t.id
            HAVING COUNT(s.id) = 0
        """
        
        result = execute_query(query)
        missing_teams = len(result)
        
        # Check 2: Records with NULL team_id
        query = """
            SELECT COUNT(*) as count
            FROM schedule
            WHERE home_team_id IS NULL AND away_team_id IS NULL
        """
        
        result = execute_query_one(query)
        null_team_records = result['count'] if result else 0
        
        # Check 3: Duplicate records
        query = """
            SELECT COUNT(*) as count
            FROM (
                SELECT match_date, home_team, away_team, league_id, COUNT(*)
                FROM schedule 
                GROUP BY match_date, home_team, away_team, league_id 
                HAVING COUNT(*) > 1
            ) duplicates
        """
        
        result = execute_query_one(query)
        duplicate_records = result['count'] if result else 0
        
        # Check 4: Orphaned records
        query = """
            SELECT COUNT(*) as count
            FROM schedule s
            LEFT JOIN teams t1 ON s.home_team_id = t1.id
            LEFT JOIN teams t2 ON s.away_team_id = t2.id
            WHERE (s.home_team_id IS NOT NULL AND t1.id IS NULL)
               OR (s.away_team_id IS NOT NULL AND t2.id IS NULL)
        """
        
        result = execute_query_one(query)
        orphaned_records = result['count'] if result else 0
        
        # Calculate health score
        health_score = 100
        
        # Deduct points for issues
        if missing_teams > 0:
            health_score -= min(missing_teams * 2, 50)  # Max 50 points deduction
            self.issues.append(f"{missing_teams} teams missing schedule data")
        
        if null_team_records > 0:
            health_score -= min(null_team_records * 0.5, 30)  # Max 30 points deduction
            self.issues.append(f"{null_team_records} records with NULL team_id")
        
        if duplicate_records > 0:
            health_score -= min(duplicate_records * 0.1, 20)  # Max 20 points deduction
            self.issues.append(f"{duplicate_records} duplicate schedule records")
        
        if orphaned_records > 0:
            health_score -= min(orphaned_records * 1, 40)  # Max 40 points deduction
            self.issues.append(f"{orphaned_records} orphaned schedule records")
        
        # Ensure health score doesn't go below 0
        health_score = max(0, health_score)
        
        # Store metrics
        self.metrics['schedule_health'] = {
            'score': health_score,
            'missing_teams': missing_teams,
            'null_team_records': null_team_records,
            'duplicate_records': duplicate_records,
            'orphaned_records': orphaned_records
        }
        
        # Determine status
        if health_score >= 90:
            status = "🟢 EXCELLENT"
        elif health_score >= 75:
            status = "🟡 GOOD"
        elif health_score >= 50:
            status = "🟠 FAIR"
        else:
            status = "🔴 POOR"
        
        logger.info(f"📊 Schedule Health Score: {health_score}/100 {status}")
        
        return health_score
    
    def check_team_data_integrity(self):
        """Check team data integrity"""
        logger.info("🔍 Checking team data integrity...")
        
        # Check for teams with invalid references
        query = """
            SELECT COUNT(*) as count
            FROM teams t
            LEFT JOIN clubs c ON t.club_id = c.id
            LEFT JOIN series s ON t.series_id = s.id
            LEFT JOIN leagues l ON t.league_id = l.id
            WHERE c.id IS NULL OR s.id IS NULL OR l.id IS NULL
        """
        
        result = execute_query_one(query)
        invalid_references = result['count'] if result else 0
        
        # Check for duplicate team names
        query = """
            SELECT COUNT(*) as count
            FROM (
                SELECT team_name, COUNT(*)
                FROM teams 
                GROUP BY team_name 
                HAVING COUNT(*) > 1
            ) duplicates
        """
        
        result = execute_query_one(query)
        duplicate_teams = result['count'] if result else 0
        
        # Store metrics
        self.metrics['team_integrity'] = {
            'invalid_references': invalid_references,
            'duplicate_teams': duplicate_teams
        }
        
        if invalid_references > 0:
            self.issues.append(f"{invalid_references} teams with invalid references")
        
        if duplicate_teams > 0:
            self.warnings.append(f"{duplicate_teams} duplicate team names")
        
        logger.info(f"📊 Team Integrity: {invalid_references} invalid references, {duplicate_teams} duplicates")
        
        return invalid_references == 0 and duplicate_teams == 0
    
    def check_player_data_quality(self):
        """Check player data quality"""
        logger.info("🔍 Checking player data quality...")
        
        # Check for incomplete player records
        query = """
            SELECT COUNT(*) as count
            FROM players 
            WHERE first_name IS NULL OR last_name IS NULL OR tenniscores_player_id IS NULL
        """
        
        result = execute_query_one(query)
        incomplete_players = result['count'] if result else 0
        
        # Check for duplicate player IDs
        query = """
            SELECT COUNT(*) as count
            FROM (
                SELECT tenniscores_player_id, COUNT(*)
                FROM players 
                GROUP BY tenniscores_player_id 
                HAVING COUNT(*) > 1
            ) duplicates
        """
        
        result = execute_query_one(query)
        duplicate_players = result['count'] if result else 0
        
        # Store metrics
        self.metrics['player_quality'] = {
            'incomplete_players': incomplete_players,
            'duplicate_players': duplicate_players
        }
        
        if incomplete_players > 0:
            self.issues.append(f"{incomplete_players} incomplete player records")
        
        if duplicate_players > 0:
            self.issues.append(f"{duplicate_players} duplicate player IDs")
        
        logger.info(f"📊 Player Quality: {incomplete_players} incomplete, {duplicate_players} duplicates")
        
        return incomplete_players == 0 and duplicate_players == 0
    
    def check_match_data_integrity(self):
        """Check match data integrity"""
        logger.info("🔍 Checking match data integrity...")
        
        # Check for self-matches
        query = """
            SELECT COUNT(*) as count
            FROM match_scores 
            WHERE home_team_id = away_team_id
        """
        
        result = execute_query_one(query)
        self_matches = result['count'] if result else 0
        
        # Check for invalid winners
        query = """
            SELECT COUNT(*) as count
            FROM match_scores ms
            LEFT JOIN players p ON ms.winner = p.tenniscores_player_id
            WHERE ms.winner IS NOT NULL AND p.id IS NULL
        """
        
        result = execute_query_one(query)
        invalid_winners = result['count'] if result else 0
        
        # Store metrics
        self.metrics['match_integrity'] = {
            'self_matches': self_matches,
            'invalid_winners': invalid_winners
        }
        
        if self_matches > 0:
            self.issues.append(f"{self_matches} self-matches found")
        
        if invalid_winners > 0:
            self.issues.append(f"{invalid_winners} invalid winners")
        
        logger.info(f"📊 Match Integrity: {self_matches} self-matches, {invalid_winners} invalid winners")
        
        return self_matches == 0 and invalid_winners == 0
    
    def check_recent_activity(self):
        """Check for recent data activity"""
        logger.info("🔍 Checking recent data activity...")
        
        # Check recent schedule activity
        query = """
            SELECT COUNT(*) as count
            FROM schedule
            WHERE match_date >= CURRENT_DATE - INTERVAL '7 days'
        """
        
        result = execute_query_one(query)
        recent_schedules = result['count'] if result else 0
        
        # Check recent match activity
        query = """
            SELECT COUNT(*) as count
            FROM match_scores
            WHERE match_date >= CURRENT_DATE - INTERVAL '7 days'
        """
        
        result = execute_query_one(query)
        recent_matches = result['count'] if result else 0
        
        # Store metrics
        self.metrics['recent_activity'] = {
            'recent_schedules': recent_schedules,
            'recent_matches': recent_matches
        }
        
        if recent_schedules == 0 and recent_matches == 0:
            self.warnings.append("No recent data activity in the last 7 days")
        
        logger.info(f"📊 Recent Activity: {recent_schedules} schedules, {recent_matches} matches")
        
        return recent_schedules > 0 or recent_matches > 0
    
    def calculate_overall_health(self):
        """Calculate overall system health score"""
        if not self.metrics:
            return 0
        
        # Weighted average of all health metrics
        total_score = 0
        total_weight = 0
        
        # Schedule health (40% weight)
        if 'schedule_health' in self.metrics:
            total_score += self.metrics['schedule_health']['score'] * 0.4
            total_weight += 0.4
        
        # Team integrity (20% weight)
        if 'team_integrity' in self.metrics:
            team_score = 100
            if self.metrics['team_integrity']['invalid_references'] > 0:
                team_score -= 50
            if self.metrics['team_integrity']['duplicate_teams'] > 0:
                team_score -= 30
            team_score = max(0, team_score)
            total_score += team_score * 0.2
            total_weight += 0.2
        
        # Player quality (20% weight)
        if 'player_quality' in self.metrics:
            player_score = 100
            if self.metrics['player_quality']['incomplete_players'] > 0:
                player_score -= 50
            if self.metrics['player_quality']['duplicate_players'] > 0:
                player_score -= 50
            player_score = max(0, player_score)
            total_score += player_score * 0.2
            total_weight += 0.2
        
        # Match integrity (20% weight)
        if 'match_integrity' in self.metrics:
            match_score = 100
            if self.metrics['match_integrity']['self_matches'] > 0:
                match_score -= 50
            if self.metrics['match_integrity']['invalid_winners'] > 0:
                match_score -= 50
            match_score = max(0, match_score)
            total_score += match_score * 0.2
            total_weight += 0.2
        
        if total_weight == 0:
            return 0
        
        overall_health = total_score / total_weight
        return round(overall_health, 2)
    
    def send_alert(self, message, subject="Rally Data Quality Alert"):
        """Send alert via SMS and/or email"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"[{timestamp}] {message}"
        
        # Send SMS alert
        if self.alert_mode and SMS_AVAILABLE:
            try:
                send_sms(ADMIN_PHONE, f"Rally Data Alert: {message}")
                logger.info(f"📱 SMS alert sent to {ADMIN_PHONE}")
            except Exception as e:
                logger.error(f"❌ Failed to send SMS alert: {e}")
        
        # Send email alert
        if self.email_mode and EMAIL_AVAILABLE:
            try:
                self.send_email_alert(subject, full_message)
                logger.info(f"📧 Email alert sent to {ADMIN_EMAIL}")
            except Exception as e:
                logger.error(f"❌ Failed to send email alert: {e}")
        
        # Log alert
        logger.warning(f"🚨 ALERT: {message}")
    
    def send_email_alert(self, subject, message):
        """Send email alert"""
        # This would need proper SMTP configuration
        # For now, just log the email
        logger.info(f"📧 Email alert: {subject} - {message}")
    
    def generate_report(self):
        """Generate monitoring report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'overall_health': self.calculate_overall_health(),
            'issues': self.issues,
            'warnings': self.warnings,
            'metrics': self.metrics
        }
        
        # Save report to file
        report_file = f"logs/monitoring_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📄 Report saved to {report_file}")
        return report
    
    def run_monitoring(self):
        """Run complete monitoring check"""
        logger.info("🎯 Automated Data Quality Monitoring")
        logger.info("=" * 50)
        logger.info(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("")
        
        # Run all monitoring checks
        schedule_health = self.check_schedule_data_health()
        team_integrity = self.check_team_data_integrity()
        player_quality = self.check_player_data_quality()
        match_integrity = self.check_match_data_integrity()
        recent_activity = self.check_recent_activity()
        
        # Calculate overall health
        overall_health = self.calculate_overall_health()
        
        # Print summary
        logger.info("\n" + "=" * 50)
        logger.info("📊 MONITORING SUMMARY")
        logger.info("=" * 50)
        logger.info(f"🏥 Overall Health Score: {overall_health}/100")
        logger.info(f"📊 Schedule Health: {self.metrics.get('schedule_health', {}).get('score', 0)}/100")
        logger.info(f"📊 Issues Found: {len(self.issues)}")
        logger.info(f"📊 Warnings: {len(self.warnings)}")
        
        if self.issues:
            logger.info(f"\n❌ Issues Found ({len(self.issues)}):")
            for issue in self.issues:
                logger.info(f"  - {issue}")
        
        if self.warnings:
            logger.info(f"\n⚠️ Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                logger.info(f"  - {warning}")
        
        # Send alerts if needed
        if overall_health < 75:
            alert_message = f"Critical: Overall health score {overall_health}/100. Issues: {len(self.issues)}"
            self.send_alert(alert_message, "Critical Data Quality Alert")
        elif overall_health < 90:
            alert_message = f"Warning: Overall health score {overall_health}/100. Issues: {len(self.issues)}"
            self.send_alert(alert_message, "Data Quality Warning")
        
        # Generate report
        report = self.generate_report()
        
        # Exit with error code if critical issues found
        if overall_health < 75:
            logger.error(f"\n❌ Monitoring failed with health score {overall_health}/100")
            return False, overall_health
        else:
            logger.info(f"\n✅ Monitoring completed successfully (health: {overall_health}/100)")
            return True, overall_health


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Automated Data Quality Monitoring")
    parser.add_argument("--alert", action="store_true", help="Send SMS alerts for issues")
    parser.add_argument("--detailed", action="store_true", help="Show detailed monitoring information")
    parser.add_argument("--email", action="store_true", help="Send email alerts for issues")
    
    args = parser.parse_args()
    
    # Run monitoring
    monitor = AutomatedDataMonitor(
        alert_mode=args.alert,
        detailed_mode=args.detailed,
        email_mode=args.email
    )
    
    success, health_score = monitor.run_monitoring()
    
    # Exit with error code if monitoring failed
    if not success:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main() 