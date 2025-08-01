#!/usr/bin/env python3
"""
Master Scraper Script for Rally Platform
========================================

Runs all scrapers for all discovered leagues in the correct order with SMS notifications:
1. Scrape stats for each league
2. Scrape match scores for each league
3. Scrape players for each league
4. Scrape schedules for each league

Sends detailed status messages to admin (7732138911) after each step.
Sends immediate failure notifications if any scraper fails.

Usage:
    python data/etl/scrapers/master_scraper.py [--environment staging|production]
    python data/etl/scrapers/master_scraper.py --environment staging
"""

import argparse
import logging
import os
import sys
import subprocess
import time
import warnings
from datetime import datetime
from pathlib import Path

# Suppress deprecation warnings - CRITICAL for production stability
warnings.filterwarnings("ignore", category=UserWarning, module="_distutils_hack")
warnings.filterwarnings("ignore", category=UserWarning, module="setuptools")
warnings.filterwarnings("ignore", category=UserWarning, module="pkg_resources")

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# Import enhanced scraper functionality
try:
    from data.etl.scrapers.stealth_browser import create_enhanced_scraper, add_throttling_to_loop
except ImportError:
    # Fallback if stealth_browser not available
    create_enhanced_scraper = None
    add_throttling_to_loop = lambda: time.sleep(2)

# Configure logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/master_scraper.log"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)

# Import SMS notification service
try:
    from app.services.notifications_service import send_sms
except ImportError:
    logger.warning("SMS service not available, notifications will be logged only")
    send_sms = None

ADMIN_PHONE = "17732138911"

class MasterScraper:
    """Master scraper that orchestrates all scraping processes"""
    
    # Legacy hardcoded leagues for backward compatibility
    LEGACY_LEAGUES = ["APTA_CHICAGO", "NSTF", "CNSWPL", "CITA"]
    
    # League name mapping for case-insensitive input
    LEAGUE_MAPPING = {
        "APTACHICAGO": "APTA_CHICAGO",
        "aptachicago": "APTA_CHICAGO",
        "NSTF": "NSTF",
        "nstf": "NSTF",
        "CNSWPL": "CNSWPL",
        "cnswpl": "CNSWPL",
        "CITA": "CITA",
        "cita": "CITA"
    }
    
    # League subdomain mapping
    LEAGUE_SUBDOMAINS = {
        "APTA_CHICAGO": "aptachicago",
        "NSTF": "nstf", 
        "CNSWPL": "cnswpl",
        "CITA": "cita"
    }
    
    def __init__(self, environment=None, league=None):
        self.environment = environment or self._detect_environment()
        self.league = league
        self.start_time = datetime.now()
        self.results = {}
        self.failures = []
        
        # Initialize enhanced scraper with request volume tracking and proxy retry logic
        if create_enhanced_scraper:
            self.scraper_enhancements = create_enhanced_scraper(
                scraper_name="Master Scraper",
                estimated_requests=800,  # Conservative estimate for all scrapers
                cron_frequency="daily"
            )
            # Test proxy connectivity with retry logic
            proxy_working = self._test_proxy_connectivity()
            if not proxy_working:
                logger.warning("⚠️ Proxy connectivity issues detected - scraping may be limited")
                # Don't abort immediately, but track for escalation
                self.proxy_issues_detected = True
            else:
                self.proxy_issues_detected = False
        else:
            self.scraper_enhancements = None
            self.proxy_issues_detected = False
        
        # Discover available leagues dynamically
        self.available_leagues = self._discover_available_leagues()
        
        # Build scraping steps dynamically based on league parameter
        self.scraping_steps = self._build_scraping_steps()
    
    def _detect_environment(self) -> str:
        """Detect current environment automatically"""
        # Check for Railway environment
        if os.getenv('RAILWAY_ENVIRONMENT'):
            railway_env = os.getenv('RAILWAY_ENVIRONMENT_NAME', '').lower()
            if 'production' in railway_env:
                return 'production'
            elif 'staging' in railway_env:
                return 'staging'
            else:
                # Default to staging for Railway
                return 'staging'
        
        # Check for /app directory (Railway indicator)
        if os.path.exists('/app'):
            return 'production'
        
        # Check for common production indicators
        if os.getenv('DATABASE_URL') and 'railway' in os.getenv('DATABASE_URL', '').lower():
            return 'production'
        
        # Check for local development indicators
        if os.path.exists('.env') or os.path.exists('venv') or os.path.exists('.venv'):
            return 'local'
        
        # Check if we're in a development directory structure
        if os.path.exists('data/etl') and os.path.exists('app') and os.path.exists('static'):
            return 'local'
        
        # Default to staging for unknown environments
        return 'staging'
    
    def _test_proxy_connectivity(self):
        """Test proxy connectivity with automatic retry logic"""
        import requests
        import time
        
        max_retries = 3
        retry_delay = 10  # 10 seconds between retries (much faster)
        
        logger.info("🔍 Testing proxy connectivity and IP rotation capabilities...")
        logger.info("📡 Using Decodo residential proxy service with automatic rotation")
        
        for attempt in range(max_retries):
            try:
                # Import and use the proxy manager
                from data.etl.scrapers.proxy_manager import get_proxy_rotator
                rotator = get_proxy_rotator()
                
                # Test proxy connectivity using the proxy manager's validation
                ip_info = rotator.validate_ip()
                
                if ip_info:
                    current_ip = ip_info.get('proxy', {}).get('ip', 'unknown')
                    country = ip_info.get('country', {}).get('code', 'Unknown')
                    city = ip_info.get('city', {}).get('name', 'Unknown')
                    
                    logger.info(f"✅ Proxy connectivity test successful (attempt {attempt + 1}/{max_retries})")
                    logger.info(f"🌐 Current IP Address: {current_ip}")
                    logger.info(f"📍 Location: {city}, {country} (Residential Proxy)")
                    logger.info(f"🔒 Connection: Encrypted HTTPS via Decodo")
                    logger.info(f"🏢 ISP: {ip_info.get('isp', {}).get('isp', 'Unknown')}")
                    
                    # Test IP rotation using the proxy manager's built-in validation
                    time.sleep(1)  # Brief delay
                    rotator._rotate_ip()  # Force rotation
                    
                    # Use the proxy manager's validation instead of httpbin
                    ip_info = rotator.validate_ip()
                    if ip_info:
                        new_ip = ip_info.get('proxy', {}).get('ip', 'unknown')
                        if new_ip != current_ip:
                            logger.info(f"✅ IP rotation successful: {current_ip} → {new_ip}")
                            logger.info(f"🔄 Rotation mechanism: Automatic port switching")
                            logger.info(f"⏱️ Rotation interval: Every 30 requests or 10 minutes")
                            return True
                        else:
                            logger.warning(f"⚠️ IP rotation failed - IP stuck on: {current_ip}")
                            logger.warning(f"🔧 Possible causes: Proxy service issue or rate limiting")
                            if attempt == max_retries - 1:
                                self._send_urgent_proxy_alert("IP rotation failure", f"IP stuck on {current_ip}")
                                return False
                    else:
                        logger.warning(f"⚠️ IP rotation validation failed")
                        logger.warning(f"🔍 Validation method: Decodo internal API")
                        logger.warning(f"💡 This may indicate temporary proxy service issues")
                        
                else:
                    logger.warning(f"⚠️ Proxy connectivity test failed (attempt {attempt + 1}/{max_retries})")
                    logger.warning(f"🔍 Validation method: Decodo internal API")
                    logger.warning(f"💡 This may indicate temporary proxy service issues")
                    
            except Exception as e:
                logger.warning(f"⚠️ Proxy connectivity test failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
            
            if attempt < max_retries - 1:
                logger.info(f"⏳ Waiting {retry_delay} seconds before retry...")
                logger.info(f"🔄 Retry {attempt + 2}/{max_retries} will test different proxy endpoint")
                time.sleep(retry_delay)
        
        # All attempts failed
        self._send_urgent_proxy_alert("Proxy connectivity failure", "All proxy connectivity tests failed")
        logger.warning("⚠️ All proxy connectivity tests failed. Scraping may be limited or blocked.")
        logger.info("💡 Proxy services often have temporary outages. Try again in a few minutes.")
        logger.info("🔧 Troubleshooting: Check proxy credentials, network connectivity, or try later")
        logger.info("📞 Admin notification sent for immediate attention")
        return False
    
    def _get_status_description(self, status_code):
        """Get descriptive text for HTTP status codes"""
        descriptions = {
            200: "Success - Proxy working correctly",
            400: "Bad Request - Invalid proxy configuration",
            401: "Unauthorized - Invalid proxy credentials",
            403: "Forbidden - Access denied by proxy service",
            404: "Not Found - Test URL unavailable",
            429: "Too Many Requests - Rate limited",
            500: "Internal Server Error - Proxy service issue",
            502: "Bad Gateway - Proxy service unavailable",
            503: "Service Unavailable - Proxy service overloaded",
            504: "Gateway Timeout - Proxy service timeout"
        }
        return descriptions.get(status_code, f"Unknown error (code {status_code})")
    
    def _send_urgent_proxy_alert(self, alert_type, details):
        """Send urgent alert to admin about proxy/IP rotation issues"""
        urgent_message = f"🚨 URGENT: {alert_type}\n\n"
        urgent_message += f"Environment: {self.environment}\n"
        urgent_message += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        urgent_message += f"Details: {details}\n\n"
        urgent_message += "⚠️ Scraping operations may be blocked or limited.\n"
        urgent_message += "🔧 Immediate action required to restore proxy service."
        
        logger.error(f"🚨 URGENT PROXY ALERT: {alert_type}")
        logger.error(f"Details: {details}")
        
        # Send urgent SMS notification
        try:
            if send_sms:
                send_sms(ADMIN_PHONE, urgent_message)
                logger.info("📱 Urgent proxy alert sent to admin")
            else:
                logger.info("📱 Urgent proxy alert (mock): " + urgent_message[:100] + "...")
        except Exception as e:
            logger.error(f"❌ Failed to send urgent proxy alert: {e}")
        
        # Also log to file for persistence
        alert_log_file = f"logs/proxy_alerts_{datetime.now().strftime('%Y%m%d')}.log"
        try:
            with open(alert_log_file, 'a') as f:
                f.write(f"[{datetime.now()}] {alert_type}: {details}\n")
        except Exception as e:
            logger.error(f"❌ Failed to log proxy alert: {e}")
    
    def _should_retry_proxy_step(self, step_name):
        """Determine if a step should be retried after proxy failure"""
        # Track retry attempts per step
        if not hasattr(self, '_proxy_retry_counts'):
            self._proxy_retry_counts = {}
        
        if step_name not in self._proxy_retry_counts:
            self._proxy_retry_counts[step_name] = 0
        
        # Allow up to 2 retries per step
        max_retries = 2
        if self._proxy_retry_counts[step_name] < max_retries:
            self._proxy_retry_counts[step_name] += 1
            logger.info(f"🔄 Proxy retry attempt {self._proxy_retry_counts[step_name]}/{max_retries} for {step_name}")
            return True
        else:
            logger.warning(f"⚠️ Max proxy retries ({max_retries}) reached for {step_name}")
            
            # Check if we should abort the entire scraping process
            if self._should_abort_due_to_proxy_issues():
                self._send_urgent_proxy_alert(
                    "CRITICAL: Scraping abort due to proxy issues",
                    f"Multiple steps failed due to proxy issues. Aborting scraping process."
                )
                logger.error("🚨 CRITICAL: Aborting scraping process due to persistent proxy issues")
                return False
            
            return False
    
    def _should_abort_due_to_proxy_issues(self):
        """Determine if scraping should be aborted due to critical proxy issues"""
        # Count total proxy failures
        total_proxy_failures = len(self._proxy_retry_counts)
        failed_steps = len([step for step, count in self._proxy_retry_counts.items() if count >= 2])
        
        # Abort if more than 50% of steps have proxy issues or if we have proxy issues from startup
        abort_threshold = len(self.scraping_steps) * 0.5
        
        if failed_steps >= abort_threshold or (self.proxy_issues_detected and failed_steps >= 2):
            logger.error(f"🚨 CRITICAL: {failed_steps}/{len(self.scraping_steps)} steps failed due to proxy issues")
            logger.error(f"🚨 Abort threshold: {abort_threshold}, Failed steps: {failed_steps}")
            return True
        
        return False
    
    def _discover_available_leagues(self):
        """Dynamically discover available leagues from data/leagues/ directory"""
        try:
            # Get the project root directory
            project_root = Path(__file__).parent.parent.parent.parent
            leagues_dir = project_root / "data" / "leagues"
            
            if not leagues_dir.exists():
                logger.warning(f"Leagues directory not found: {leagues_dir}")
                logger.info("Falling back to legacy hardcoded leagues")
                return self.LEGACY_LEAGUES
            
            # Discover league directories (excluding 'all' directory)
            available_leagues = []
            for item in leagues_dir.iterdir():
                if item.is_dir() and item.name != "all" and not item.name.startswith("."):
                    available_leagues.append(item.name)
            
            if not available_leagues:
                logger.warning("No league directories found, falling back to legacy leagues")
                return self.LEGACY_LEAGUES
            
            # Sort for consistent ordering
            available_leagues.sort()
            logger.info(f"Discovered {len(available_leagues)} leagues: {', '.join(available_leagues)}")
            return available_leagues
            
        except Exception as e:
            logger.error(f"Error discovering leagues: {e}")
            logger.info("Falling back to legacy hardcoded leagues")
            return self.LEGACY_LEAGUES
    
    def _get_league_subdomain(self, league_id):
        """Get subdomain for a league ID"""
        return self.LEAGUE_SUBDOMAINS.get(league_id, league_id.lower())
    
    def _build_scraping_steps(self):
        """Build scraping steps based on league parameter"""
        steps = []
        
        # Add scraping steps based on league parameter
        if self.league:
            # Single league mode - normalize league name
            normalized_league = self.LEAGUE_MAPPING.get(self.league, self.league)
            if normalized_league not in self.available_leagues:
                raise ValueError(f"Invalid league: {self.league}. Available leagues: {', '.join(self.available_leagues)}")
            
            league_subdomain = self._get_league_subdomain(normalized_league)
            
            # Step 1: Scrape stats
            steps.append({
                "name": f"Scrape Stats - {normalized_league}",
                "script": "scrape_stats.py",
                "args": [league_subdomain],
                "description": f"Scrape team statistics for {normalized_league}"
            })
            
            # Step 2: Scrape match scores
            steps.append({
                "name": f"Scrape Match Scores - {normalized_league}",
                "script": "scrape_match_scores.py",
                "args": [league_subdomain],
                "description": f"Scrape match scores and results for {normalized_league}"
            })
            
            # Step 3: Scrape players
            steps.append({
                "name": f"Scrape Players - {normalized_league}",
                "script": "scrape_players.py",
                "args": [league_subdomain],
                "description": f"Scrape player data for {normalized_league}"
            })
            
            # Step 4: Scrape schedules
            steps.append({
                "name": f"Scrape Schedules - {normalized_league}",
                "script": "scrape_schedule.py",
                "args": [league_subdomain],
                "description": f"Scrape team schedules for {normalized_league}"
            })
        else:
            # All leagues mode - create steps for each league
            for league_id in self.available_leagues:
                league_subdomain = self._get_league_subdomain(league_id)
                
                # Step 1: Scrape stats
                steps.append({
                    "name": f"Scrape Stats - {league_id}",
                    "script": "scrape_stats.py",
                    "args": [league_subdomain],
                    "description": f"Scrape team statistics for {league_id}"
                })
                
                # Step 2: Scrape match scores
                steps.append({
                    "name": f"Scrape Match Scores - {league_id}",
                    "script": "scrape_match_scores.py",
                    "args": [league_subdomain],
                    "description": f"Scrape match scores and results for {league_id}"
                })
                
                # Step 3: Scrape players
                steps.append({
                    "name": f"Scrape Players - {league_id}",
                    "script": "scrape_players.py",
                    "args": [league_subdomain],
                    "description": f"Scrape player data for {league_id}"
                })
                
                # Step 4: Scrape schedules
                steps.append({
                    "name": f"Scrape Schedules - {league_id}",
                    "script": "scrape_schedule.py",
                    "args": [league_subdomain],
                    "description": f"Scrape team schedules for {league_id}"
                })
        
        return steps
    
    def send_notification(self, message, is_failure=False):
        """Send SMS notification to admin"""
        try:
            if send_sms:
                send_sms(ADMIN_PHONE, message)
                logger.info(f"📱 SMS sent to admin: {message[:100]}...")
            else:
                logger.info(f"📱 SMS notification (mock): {message}")
        except Exception as e:
            logger.error(f"❌ Failed to send SMS: {e}")
    
    def run_scraping_step(self, step):
        """Run a single scraping step with enhanced stealth functionality"""
        step_name = step["name"]
        script_path = step["script"]
        args = step["args"]
        description = step["description"]
        
        logger.info(f"🚀 Starting: {step_name}")
        logger.info(f"📝 Description: {description}")
        logger.info(f"🔧 Script: {script_path}")
        logger.info(f"⚙️ Arguments: {args}")
        
        # Track request and add throttling before step execution
        if self.scraper_enhancements:
            self.scraper_enhancements.track_request(f"step_{step_name.lower().replace(' ', '_')}")
            add_throttling_to_loop()
        
        # Build command - handle both local and Docker environments
        script_dir = os.path.dirname(os.path.abspath(__file__))
        local_script_path = os.path.join(script_dir, script_path)
        
        if os.path.exists(local_script_path):
            cmd = ["python3", local_script_path] + args
        else:
            raise FileNotFoundError(f"Script not found: {local_script_path}")
        
        start_time = datetime.now()
        
        try:
            # Run the scraping script with real-time output
            print(f"🚀 Starting subprocess: {' '.join(cmd)}")
            print("=" * 60)
            
            # Use Popen to get real-time output
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                universal_newlines=True,
                bufsize=1
            )
            
            # Capture output in real-time
            output_lines = []
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    print(output.rstrip())
                    output_lines.append(output)
            
            # Wait for completion and get return code
            return_code = process.poll()
            result = subprocess.CompletedProcess(
                args=cmd,
                returncode=return_code,
                stdout=''.join(output_lines),
                stderr=''
            )
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            if result.returncode == 0:
                # Success
                success_msg = f"✅ {step_name} completed successfully in {duration}"
                logger.info(success_msg)
                
                # Send success notification
                notification = f"Rally Scraper: {step_name} ✅\nDuration: {duration}\nEnvironment: {self.environment}"
                self.send_notification(notification)
                
                self.results[step_name] = {
                    "status": "success",
                    "duration": duration,
                    "output": result.stdout,
                    "error": result.stderr
                }
                
                return True
            else:
                # Check if failure is proxy-related
                error_output = result.stderr.lower()
                if any(proxy_error in error_output for proxy_error in ['proxy', 'connection', 'timeout', 'unavailable']):
                    logger.warning(f"⚠️ {step_name} failed due to proxy issues")
                    logger.info("💡 Proxy services often have temporary outages. Consider retrying in a few minutes.")
                    
                    # Add proxy retry logic
                    if self._should_retry_proxy_step(step_name):
                        logger.info(f"🔄 Retrying {step_name} after proxy failure...")
                        time.sleep(5)  # Wait 5 seconds before retry (much faster)
                        return self.run_scraping_step(step)  # Recursive retry
                    else:
                        # Max retries reached - send urgent alert
                        self._send_urgent_proxy_alert(
                            "Scraping step proxy failure", 
                            f"Step '{step_name}' failed after max proxy retries. Error: {result.stderr[:200]}"
                        )
                
                # Failure
                error_msg = f"❌ {step_name} failed after {duration}"
                logger.error(error_msg)
                logger.error(f"Error output: {result.stderr}")
                
                # Send immediate failure notification
                failure_notification = f"🚨 Rally Scraper FAILURE: {step_name}\nError: {result.stderr[:200]}...\nEnvironment: {self.environment}"
                self.send_notification(failure_notification, is_failure=True)
                
                self.results[step_name] = {
                    "status": "failed",
                    "duration": duration,
                    "output": result.stdout,
                    "error": result.stderr
                }
                
                self.failures.append(step_name)
                return False
                
        except subprocess.TimeoutExpired:
            # Timeout
            timeout_msg = f"⏰ {step_name} timed out after 2 hours"
            logger.error(timeout_msg)
            
            timeout_notification = f"⏰ Rally Scraper TIMEOUT: {step_name}\nEnvironment: {self.environment}"
            self.send_notification(timeout_notification, is_failure=True)
            
            self.results[step_name] = {
                "status": "timeout",
                "duration": "2 hours+",
                "output": "",
                "error": "Script timed out after 2 hours"
            }
            
            self.failures.append(step_name)
            return False
            
        except Exception as e:
            # Unexpected error
            error_msg = f"💥 {step_name} failed with unexpected error: {e}"
            logger.error(error_msg)
            
            error_notification = f"💥 Rally Scraper ERROR: {step_name}\nError: {str(e)}\nEnvironment: {self.environment}"
            self.send_notification(error_notification, is_failure=True)
            
            self.results[step_name] = {
                "status": "error",
                "duration": "unknown",
                "output": "",
                "error": str(e)
            }
            
            self.failures.append(step_name)
            return False
    
    def run_all_scrapers(self):
        """Run all scraping steps in order"""
        logger.info("🎯 Master Scraper Script Starting")
        logger.info("=" * 60)
        logger.info(f"🌍 Environment: {self.environment}")
        league_info = f"League: {self.league}" if self.league else f"All Leagues ({', '.join(self.available_leagues)})"
        logger.info(f"🏆 {league_info}")
        logger.info(f"📱 Admin Phone: {ADMIN_PHONE}")
        logger.info(f"🕐 Start Time: {self.start_time}")
        logger.info("=" * 60)
        
        # Send start notification
        league_info = f"League: {self.league}" if self.league else f"All Leagues ({', '.join(self.available_leagues)})"
        start_notification = f"🚀 Rally Master Scraper Starting\n{league_info}\nEnvironment: {self.environment}\nTime: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}"
        self.send_notification(start_notification)
        
        # Run each scraping step
        for i, step in enumerate(self.scraping_steps, 1):
            logger.info(f"\n📋 Step {i}/{len(self.scraping_steps)}: {step['name']}")
            logger.info("-" * 50)
            
            success = self.run_scraping_step(step)
            
            if not success:
                logger.warning(f"⚠️ {step['name']} failed, but continuing with next step...")
                
                # Check if we should abort due to critical proxy issues
                if hasattr(self, '_proxy_retry_counts') and self._should_abort_due_to_proxy_issues():
                    logger.error("🚨 CRITICAL: Aborting scraping process due to persistent proxy issues")
                    self._send_urgent_proxy_alert(
                        "CRITICAL: Scraping process aborted",
                        f"Aborted after {i}/{len(self.scraping_steps)} steps due to proxy issues"
                    )
                    # Add remaining steps as failures
                    for remaining_step in self.scraping_steps[i:]:
                        self.failures.append(remaining_step['name'])
                        self.results[remaining_step['name']] = {
                            "status": "aborted",
                            "duration": "0:00:00",
                            "output": "",
                            "error": "Process aborted due to proxy issues"
                        }
                    break
            
            # Brief pause between steps
            if i < len(self.scraping_steps):
                logger.info("⏳ Pausing 10 seconds before next step...")
                time.sleep(10)
        
        # Generate final summary
        self.generate_final_summary()
    
    def generate_final_summary(self):
        """Generate and send final summary"""
        end_time = datetime.now()
        total_duration = end_time - self.start_time
        
        # Count results
        total_steps = len(self.scraping_steps)
        successful_steps = len([r for r in self.results.values() if r["status"] == "success"])
        failed_steps = len(self.failures)
        
        # Create summary
        league_info = f"League: {self.league}" if self.league else f"All Leagues ({', '.join(self.available_leagues)})"
        summary_lines = [
            "📊 Rally Master Scraper Summary",
            league_info,
            f"Environment: {self.environment}",
            f"Total Duration: {total_duration}",
            f"Steps: {successful_steps}/{total_steps} successful",
            f"Failures: {failed_steps}"
        ]
        
        if self.failures:
            summary_lines.append(f"Failed Steps: {', '.join(self.failures)}")
        
        summary = "\n".join(summary_lines)
        
        # Log summary
        logger.info("\n" + "=" * 60)
        logger.info("📊 FINAL SUMMARY")
        logger.info("=" * 60)
        logger.info(summary)
        
        # Send final notification
        if failed_steps == 0:
            final_notification = f"🎉 Rally Scraper Complete!\n{league_info}\n{successful_steps}/{total_steps} steps successful\nDuration: {total_duration}\nEnvironment: {self.environment}"
        else:
            final_notification = f"⚠️ Rally Scraper Complete with Issues\n{league_info}\n{successful_steps}/{total_steps} steps successful\nFailures: {', '.join(self.failures)}\nDuration: {total_duration}\nEnvironment: {self.environment}"
        
        self.send_notification(final_notification)
        
        # Log enhanced session summary if available
        if self.scraper_enhancements:
            self.scraper_enhancements.log_session_summary()
        
        # Save detailed results to file
        self.save_detailed_results()
    
    def save_detailed_results(self):
        """Save detailed results to log file"""
        results_file = f"logs/master_scraper_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(results_file, 'w') as f:
            f.write("Rally Master Scraper Detailed Results\n")
            f.write(f"{league_info}\n")
            f.write(f"Environment: {self.environment}\n")
            f.write(f"Start Time: {self.start_time}\n")
            f.write(f"End Time: {datetime.now()}\n")
            f.write(f"Total Duration: {datetime.now() - self.start_time}\n\n")
            
            for step_name, result in self.results.items():
                f.write(f"Step: {step_name}\n")
                f.write(f"Status: {result['status']}\n")
                f.write(f"Duration: {result['duration']}\n")
                f.write(f"Output: {result['output'][:500]}...\n")
                if result['error']:
                    f.write(f"Error: {result['error']}\n")
                f.write("-" * 30 + "\n")
        
        logger.info(f"📄 Detailed results saved to: {results_file}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Master Scraper Script")
    parser.add_argument(
        "--environment",
        choices=["local", "staging", "production"],
        help="Environment to run scrapers for (auto-detected if not specified)"
    )
    parser.add_argument(
        "league",
        nargs="?",
        help="Specific league subdomain to scrape (e.g., aptachicago, nstf, cnswpl, cita). If not provided, all discovered leagues will be scraped."
    )
    
    args = parser.parse_args()
    
    try:
        # Create and run master scraper
        scraper = MasterScraper(
            environment=args.environment,
            league=args.league
        )
        scraper.run_all_scrapers()
        
        # Exit with appropriate code
        if scraper.failures:
            logger.error(f"❌ Master scraper completed with {len(scraper.failures)} failures")
            sys.exit(1)
        else:
            logger.info("✅ Master scraper completed successfully")
            sys.exit(0)
            
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 