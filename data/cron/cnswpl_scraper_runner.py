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

def run_step(description, command):
    print(f"\n=== Running: {description} ===")
    start_time = datetime.now()
    
    try:
        # Run command with real-time output display and capture for stats
        result = subprocess.run(command, check=True)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Extract stats from the command output (we'll get this from the logs)
        stats = ""
        # Note: Since we're not capturing output, we'll rely on the command's own logging
        # The individual scrapers already print their stats, so we'll see them in real-time
        
        success_message = f"✅ {description} completed successfully ({duration:.1f}s)"
        print(success_message)
        
        # Send SMS notification
        sms_message = f"🔄 Rally CNSWPL Scraper Runner\n\n{success_message}"
        send_sms_notification(ADMIN_PHONE, sms_message)
        
        return True
        
    except subprocess.CalledProcessError as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        error_message = f"❌ {description} failed ({duration:.1f}s)\nError: {e.stderr or str(e)}"
        print(error_message)
        
        # Send SMS notification for failure
        sms_message = f"🚨 Rally CNSWPL Scraper Runner\n\n{error_message}"
        send_sms_notification(ADMIN_PHONE, sms_message)
        
        raise

def main():
    start_time = datetime.now()
    
    # Send starting notification
    start_message = f"🚀 Rally CNSWPL Full Runner Started\n\nTime: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\nLeague: CNSWPL\n\nRunning full scrape → import (Players, Scores, Stats)..."
    print(f"\n=== {start_message} ===")
    send_sms_notification(ADMIN_PHONE, start_message)
    
    try:
        # Players
        run_step("Scrape CNSWPL Players", ["python3", "data/etl/scrapers/cnswpl/cnswpl_scrape_players_simple.py"])
        run_step("Import CNSWPL Players", ["python3", "data/etl/import/import_players.py", "CNSWPL"])

        # Scores (using --weeks 1 to only scrape most recent week)
        run_step("Scrape CNSWPL Match Scores", ["python3", "data/etl/scrapers/cnswpl_scrape_match_scores.py", "cnswpl", "--weeks", "1"])
        run_step("Import CNSWPL Match Scores", ["python3", "data/etl/import/import_match_scores.py", "CNSWPL"])

        # Stats
        run_step("Scrape CNSWPL Series Stats", ["python3", "data/etl/scrapers/cnswpl_scrape_stats.py"])
        run_step("Import CNSWPL Series Stats", ["python3", "data/etl/import/import_stats.py", "CNSWPL"])

        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        success_message = f"🎉 Rally CNSWPL Full Runner Completed Successfully!\n\nTotal Duration: {total_duration:.1f}s\nLeague: CNSWPL\nCompleted: 6/6 steps (Full Suite)\n\nFull scrape → import completed successfully."
        print(f"\n=== {success_message} ===")
        send_sms_notification(ADMIN_PHONE, success_message)
        
    except Exception as e:
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        error_message = f"💥 Rally CNSWPL Full Runner Failed!\n\nTotal Duration: {total_duration:.1f}s\nLeague: CNSWPL\nError: {str(e)}"
        print(f"\n=== {error_message} ===")
        send_sms_notification(ADMIN_PHONE, error_message)
        
        raise

if __name__ == "__main__":
    main()

