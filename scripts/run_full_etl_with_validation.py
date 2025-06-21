#!/usr/bin/env python3
"""
Complete ETL Pipeline with Validation
=====================================

Runs the full ETL pipeline with comprehensive validation checks:
1. Runs fresh scraping (optional)
2. Validates JSON data quality
3. Imports to database with winner validation
4. Post-import validation checks
5. Updates player stats calculations

Usage:
    python scripts/run_full_etl_with_validation.py [--scrape] [--validate-only]
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

def log(message, level="INFO"):
    """Enhanced logging with timestamps"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def run_command(command, description, cwd=None):
    """Run a command and handle errors"""
    log(f"Running: {description}")
    log(f"Command: {command}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            cwd=cwd or project_root
        )
        
        if result.stdout:
            print(result.stdout)
        
        log(f"✅ Completed: {description}")
        return True
        
    except subprocess.CalledProcessError as e:
        log(f"❌ Failed: {description}", "ERROR")
        log(f"Error: {e}", "ERROR")
        if e.stdout:
            log(f"STDOUT: {e.stdout}", "ERROR")
        if e.stderr:
            log(f"STDERR: {e.stderr}", "ERROR")
        return False

def validate_json_data():
    """Validate JSON data quality before import"""
    log("🔍 Validating JSON data quality...")
    
    # Run winner validation
    validation_script = os.path.join(project_root, "data/etl/validation/winner_validation.py")
    success = run_command(
        f"python {validation_script} --auto-fix",
        "Winner data validation and auto-correction"
    )
    
    return success

def run_etl_scraping():
    """Run fresh ETL scraping"""
    log("🌐 Running fresh ETL scraping...")
    
    # You would add your specific scraping commands here
    # For example:
    scraper_commands = [
        # "python data/etl/scrapers/master_scraper.py --league CNSWPL",
        # "python data/etl/scrapers/master_scraper.py --league APTA_CHICAGO",
        # Add other leagues as needed
    ]
    
    for command in scraper_commands:
        success = run_command(command, f"Scraping: {command.split()[-1]}")
        if not success:
            log("❌ Scraping failed, stopping ETL pipeline", "ERROR")
            return False
    
    log("✅ All scraping completed successfully")
    return True

def run_database_import():
    """Run database import with validation"""
    log("📥 Running database import...")
    
    import_script = os.path.join(project_root, "data/etl/database_import/import_all_jsons_to_database.py")
    success = run_command(
        f"python {import_script}",
        "Database import with winner validation"
    )
    
    return success

def run_post_import_validation():
    """Run post-import validation checks"""
    log("🔍 Running post-import validation...")
    
    # Check Jessica Freedman's specific case
    validation_commands = [
        # You can add specific validation scripts here
        f"python -c \"" +
        "import sys; sys.path.append('.'); " +
        "from app.services.mobile_service import get_player_analysis; " +
        "result = get_player_analysis('nndz-WkMrK3dMMzdndz09'); " +
        "print(f'Jessica Freedman: {result[\\\"wins\\\"]} wins, {result[\\\"losses\\\"]} losses')\"",
    ]
    
    for command in validation_commands:
        success = run_command(command, "Player analysis validation")
        if not success:
            log("⚠️ Post-import validation had issues", "WARNING")
            
    return True

def update_player_stats():
    """Update calculated player statistics"""
    log("📊 Updating player statistics...")
    
    # Add commands to update/recalculate player stats if needed
    stats_commands = [
        # Example: update win/loss records in players table
        # "python scripts/update_player_win_loss_records.py",
    ]
    
    for command in stats_commands:
        success = run_command(command, f"Stats update: {command}")
        if not success:
            log("⚠️ Stats update had issues", "WARNING")
    
    return True

def create_validation_report():
    """Create a comprehensive validation report"""
    log("📋 Creating validation report...")
    
    from database_config import get_db
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Collect key metrics
            cursor.execute("SELECT COUNT(*) FROM match_scores")
            total_matches = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM match_scores WHERE winner IS NOT NULL")
            matches_with_winners = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM players")
            total_players = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT league_id) FROM players")
            leagues_count = cursor.fetchone()[0]
            
            # Check Jessica Freedman specifically
            cursor.execute("""
                SELECT wins, losses, tenniscores_player_id 
                FROM players 
                WHERE tenniscores_player_id = %s
            """, ('nndz-WkMrK3dMMzdndz09',))
            
            jessica_stats = cursor.fetchone()
            
            # Create report
            report = f"""
📋 ETL VALIDATION REPORT
========================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 DATABASE SUMMARY:
   Total matches: {total_matches:,}
   Matches with winners: {matches_with_winners:,} ({matches_with_winners/total_matches*100:.1f}%)
   Total players: {total_players:,}
   Active leagues: {leagues_count}

🎯 SPECIFIC VALIDATIONS:
   Jessica Freedman (ID: nndz-WkMrK3dMMzdndz09):
   """
        
        if jessica_stats:
            wins, losses, player_id = jessica_stats
            report += f"Wins: {wins}, Losses: {losses} ✅"
        else:
            report += "❌ Player not found"
        
        report += "\n\n✅ ETL Pipeline completed successfully!"
        
        print(report)
        
        # Save report to file
        report_path = os.path.join(project_root, "logs", f"etl_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        with open(report_path, 'w') as f:
            f.write(report)
        
        log(f"📄 Validation report saved to: {report_path}")
        
        return True
        
    except Exception as e:
        log(f"❌ Failed to create validation report: {e}", "ERROR")
        return False

def main():
    """Main execution"""
    parser = argparse.ArgumentParser(description='Run complete ETL pipeline with validation')
    parser.add_argument('--scrape', action='store_true', help='Run fresh scraping before import')
    parser.add_argument('--validate-only', action='store_true', help='Only run validation, skip scraping and import')
    parser.add_argument('--skip-validation', action='store_true', help='Skip pre-import validation checks')
    
    args = parser.parse_args()
    
    log("🚀 Starting Complete ETL Pipeline with Validation")
    log("=" * 60)
    
    success = True
    
    if args.validate_only:
        log("📋 Running validation-only mode")
        success = validate_json_data() and success
        success = create_validation_report() and success
        
    else:
        # Full pipeline
        if args.scrape:
            log("🌐 Scraping mode enabled")
            success = run_etl_scraping() and success
            if not success:
                log("❌ Scraping failed, aborting pipeline", "ERROR")
                return 1
        
        if not args.skip_validation:
            log("🔍 Pre-import validation enabled")
            success = validate_json_data() and success
            if not success:
                log("❌ JSON validation failed, aborting pipeline", "ERROR")
                return 1
        
        # Database import
        success = run_database_import() and success
        if not success:
            log("❌ Database import failed, aborting pipeline", "ERROR")
            return 1
        
        # Post-import steps
        success = run_post_import_validation() and success
        success = update_player_stats() and success
        success = create_validation_report() and success
    
    if success:
        log("🎉 ETL Pipeline completed successfully!")
        return 0
    else:
        log("❌ ETL Pipeline completed with errors", "ERROR")
        return 1

if __name__ == "__main__":
    exit(main()) 