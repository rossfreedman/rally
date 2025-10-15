import subprocess
import os
import sys
from datetime import datetime

# Add the project root to the path so we can import config
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from config import TwilioConfig
from app.services.notifications_service import send_sms_notification

# Admin phone number for notifications
ADMIN_PHONE = "17732138911"  # Ross's phone number

def format_duration(seconds):
    """Format duration in hours and minutes instead of seconds"""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        return f"{minutes}m {remaining_seconds}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

def run_step(description, command):
    print(f"\n=== Running: {description} ===")
    start_time = datetime.now()
    
    try:
        # Run command with real-time output display and capture for stats
        result = subprocess.run(command, check=True)
        end_time = datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()
        duration_formatted = format_duration(duration_seconds)
        
        success_message = f"✅ {description} completed successfully ({duration_formatted})"
        print(success_message)
        
        # Send SMS notification
        sms_message = f"🔄 APTA All Scraper\n\n{success_message}"
        send_sms_notification(ADMIN_PHONE, sms_message)
        
        return True
        
    except subprocess.CalledProcessError as e:
        end_time = datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()
        duration_formatted = format_duration(duration_seconds)
        
        error_message = f"❌ {description} failed ({duration_formatted})\nError: {e.stderr or str(e)}"
        print(error_message)
        
        # Send SMS notification for failure
        sms_message = f"🚨 APTA All Scraper\n\n{error_message}"
        send_sms_notification(ADMIN_PHONE, sms_message)
        
        raise

def main():
    start_time = datetime.now()
    
    # Send starting notification
    start_message = f"🚀 APTA All Scraper Started\n\nTime: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\nLeague: APTA_CHICAGO\n\nScraping and importing all APTA data (players, scores, stats)..."
    print(f"\n=== {start_message} ===")
    send_sms_notification(ADMIN_PHONE, start_message)
    
    try:
        # Players
        run_step("Scrape APTA Players", ["python3", "data/etl/scrapers/apta/apta_scrape_players_simple.py", "APTA_CHICAGO"])
        run_step("Import APTA Players", ["python3", "data/etl/import/import_players.py", "APTA_CHICAGO"])

        # Scores (using --weeks 2 to scrape most recent 2 weeks)
        run_step("Scrape APTA Match Scores", ["python3", "data/etl/scrapers/apta_scrape_match_scores.py", "aptachicago", "--weeks", "2"])
        run_step("Import APTA Match Scores", ["python3", "data/etl/import/import_match_scores.py", "APTA_CHICAGO"])

        # Stats
        run_step("Scrape APTA Series Stats", ["python3", "data/etl/scrapers/scrape_stats.py", "aptachicago"])
        run_step("Import APTA Series Stats", ["python3", "data/etl/import/import_stats.py", "APTA_CHICAGO"])

        end_time = datetime.now()
        total_duration_seconds = (end_time - start_time).total_seconds()
        total_duration_formatted = format_duration(total_duration_seconds)
        
        success_message = f"✅ APTA All Scraper Completed!\n\nTotal Duration: {total_duration_formatted}\nLeague: APTA_CHICAGO\nCompleted: 6/6 steps\n\nAll APTA data (players, scores, stats) scraped and imported successfully."
        print(f"\n=== {success_message} ===")
        send_sms_notification(ADMIN_PHONE, success_message)
        
    except Exception as e:
        end_time = datetime.now()
        total_duration_seconds = (end_time - start_time).total_seconds()
        total_duration_formatted = format_duration(total_duration_seconds)
        
        error_message = f"💥 APTA All Scraper Failed!\n\nTotal Duration: {total_duration_formatted}\nLeague: APTA_CHICAGO\nError: {str(e)}"
        print(f"\n=== {error_message} ===")
        send_sms_notification(ADMIN_PHONE, error_message)
        
        raise

if __name__ == "__main__":
    main()
