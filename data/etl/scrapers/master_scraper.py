#!/usr/bin/env python3
"""
Master Tennis Scraper - Runs all individual scrapers in sequence
This script orchestrates the complete data collection process for any TennisScores league.
"""

import os
import sys
import time
import traceback
from datetime import datetime, timedelta

# Add the scrapers directory to the path so we can import the scraper modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import all the individual scraper functions
try:
    from scraper_match_scores import scrape_all_matches
    from scraper_player_history import scrape_player_history
    from scraper_players import scrape_league_players
    from scraper_schedule import scrape_tennis_schedule
    from scraper_stats import scrape_all_stats

    print("✅ All scraper modules imported successfully")
except ImportError as e:
    print(f"❌ Error importing scraper modules: {e}")
    sys.exit(1)


def validate_league_subdomain(subdomain):
    """
    Validate that the league subdomain is in a reasonable format.

    Args:
        subdomain (str): The league subdomain to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if not subdomain:
        return False

    # Basic validation - should be alphanumeric with possible hyphens
    if not subdomain.replace("-", "").replace("_", "").isalnum():
        return False

    # Should be reasonable length
    if len(subdomain) < 2 or len(subdomain) > 50:
        return False

    return True


def format_duration(duration):
    """
    Format a timedelta duration into a human-readable string.

    Args:
        duration (timedelta): The duration to format

    Returns:
        str: Formatted duration string
    """
    total_seconds = int(duration.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


def run_scraper_with_error_handling(scraper_name, scraper_func, *args, **kwargs):
    """
    Run a scraper function with comprehensive error handling and timing.

    Args:
        scraper_name (str): Name of the scraper for logging
        scraper_func (callable): The scraper function to run
        *args: Arguments to pass to the scraper function
        **kwargs: Keyword arguments to pass to the scraper function

    Returns:
        tuple: (success: bool, duration: timedelta, error_message: str or None)
    """
    start_time = datetime.now()

    try:
        print(f"\n🚀 Starting {scraper_name}...")
        print(f"⏰ Start time: {start_time.strftime('%H:%M:%S')}")
        print("=" * 60)

        # Run the scraper function
        result = scraper_func(*args, **kwargs)

        end_time = datetime.now()
        duration = end_time - start_time

        print("=" * 60)
        print(f"✅ {scraper_name} completed successfully!")
        print(f"⏰ End time: {end_time.strftime('%H:%M:%S')}")
        print(f"⏱️  Duration: {format_duration(duration)}")

        return True, duration, None

    except Exception as e:
        end_time = datetime.now()
        duration = end_time - start_time
        error_message = str(e)

        print("=" * 60)
        print(f"❌ {scraper_name} failed!")
        print(f"⏰ Failure time: {end_time.strftime('%H:%M:%S')}")
        print(f"⏱️  Duration before failure: {format_duration(duration)}")
        print(f"🚨 Error: {error_message}")
        print("\n🔍 Full traceback:")
        traceback.print_exc()

        return False, duration, error_message


def run_master_scraper(league_subdomain):
    """
    Run all scrapers in sequence for the specified league.

    Args:
        league_subdomain (str): The league subdomain (e.g., 'aptachicago', 'nstf')
    """
    overall_start_time = datetime.now()

    print(f"🎾 MASTER TENNIS SCRAPER")
    print("=" * 80)
    print(f"🌐 Target League: {league_subdomain.upper()}")
    print(f"🌍 Target URL: https://{league_subdomain}.tenniscores.com")
    print(f"🕐 Session Start: {overall_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Define the scraping sequence
    # Order matters - players should be scraped first as other scrapers may depend on the player data
    scraping_sequence = [
        (
            "Player Data Scraper",
            scrape_league_players,
            [league_subdomain],
            {"get_detailed_stats": True},
        ),
        ("Match History Scraper", scrape_all_matches, [league_subdomain], {}),
        ("Schedule Scraper", scrape_tennis_schedule, [league_subdomain], {}),
        ("Team Statistics Scraper", scrape_all_stats, [league_subdomain], {}),
        ("Player History Scraper", scrape_player_history, [league_subdomain], {}),
    ]

    # Track results
    results = []
    successful_scrapers = 0
    failed_scrapers = 0
    total_duration = timedelta()

    print(f"📋 Scraping Sequence ({len(scraping_sequence)} scrapers):")
    for i, (name, _, _, _) in enumerate(scraping_sequence, 1):
        print(f"  {i}. {name}")
    print()

    # Run each scraper in sequence
    for scraper_num, (scraper_name, scraper_func, args, kwargs) in enumerate(
        scraping_sequence, 1
    ):
        scraper_start_time = datetime.now()
        elapsed_total = scraper_start_time - overall_start_time

        print(
            f"\n📊 SCRAPER {scraper_num}/{len(scraping_sequence)} | Total Elapsed: {format_duration(elapsed_total)}"
        )

        # Run the scraper with error handling
        success, duration, error_message = run_scraper_with_error_handling(
            scraper_name, scraper_func, *args, **kwargs
        )

        # Record results
        results.append(
            {
                "name": scraper_name,
                "success": success,
                "duration": duration,
                "error": error_message,
            }
        )

        total_duration += duration

        if success:
            successful_scrapers += 1
        else:
            failed_scrapers += 1

        # Progress update
        remaining_scrapers = len(scraping_sequence) - scraper_num
        if remaining_scrapers > 0:
            avg_duration = total_duration / scraper_num
            estimated_remaining = avg_duration * remaining_scrapers
            eta = datetime.now() + estimated_remaining

            print(f"\n📈 PROGRESS UPDATE:")
            print(f"  ✅ Completed: {scraper_num}/{len(scraping_sequence)} scrapers")
            print(
                f"  🎯 Success rate: {successful_scrapers}/{scraper_num} ({(successful_scrapers/scraper_num)*100:.1f}%)"
            )
            print(f"  ⏰ Estimated completion: {eta.strftime('%H:%M:%S')}")
            print(f"  ⏳ Estimated remaining: {format_duration(estimated_remaining)}")

        # Add a small delay between scrapers to be nice to the server
        if scraper_num < len(scraping_sequence):
            print(f"\n⏸️  Brief pause before next scraper...")
            time.sleep(5)

    # Calculate final results
    overall_end_time = datetime.now()
    overall_duration = overall_end_time - overall_start_time

    print(f"\n🎉 MASTER SCRAPER COMPLETE!")
    print("=" * 80)

    # Session summary
    print(f"📅 SESSION SUMMARY - {overall_end_time.strftime('%Y-%m-%d')}")
    print(f"🌐 League: {league_subdomain.upper()}")
    print(f"🕐 Start Time: {overall_start_time.strftime('%H:%M:%S')}")
    print(f"🏁 End Time: {overall_end_time.strftime('%H:%M:%S')}")
    print(f"⏱️  Total Duration: {format_duration(overall_duration)}")
    print()

    # Performance metrics
    print(f"📊 PERFORMANCE SUMMARY")
    print(
        f"✅ Successful scrapers: {successful_scrapers}/{len(scraping_sequence)} ({(successful_scrapers/len(scraping_sequence))*100:.1f}%)"
    )
    print(
        f"❌ Failed scrapers: {failed_scrapers}/{len(scraping_sequence)} ({(failed_scrapers/len(scraping_sequence))*100:.1f}%)"
    )
    print(
        f"⚡ Average time per scraper: {format_duration(total_duration / len(scraping_sequence))}"
    )
    print()

    # Detailed results
    print(f"📋 DETAILED RESULTS:")
    for i, result in enumerate(results, 1):
        status = "✅ SUCCESS" if result["success"] else "❌ FAILED"
        duration_str = format_duration(result["duration"])
        print(f"  {i}. {result['name']}: {status} ({duration_str})")
        if result["error"]:
            print(f"     Error: {result['error']}")
    print()

    # Data location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Navigate up three levels: data/etl/scrapers -> data/etl -> data -> project_root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
    data_dir = os.path.join(project_root, "data", "leagues", league_subdomain.upper())

    print(f"💾 DATA LOCATION:")
    print(f"  📁 League data saved to: {data_dir}")
    if os.path.exists(data_dir):
        try:
            files = os.listdir(data_dir)
            print(f"  📄 Generated files: {len(files)}")
            for file in sorted(files):
                file_path = os.path.join(data_dir, file)
                file_size = os.path.getsize(file_path)
                print(f"    - {file} ({file_size:,} bytes)")
        except Exception as e:
            print(f"    ⚠️  Could not list files: {e}")
    else:
        print(f"    ⚠️  Data directory not found")

    print("=" * 80)

    # Final status
    if failed_scrapers == 0:
        print(f"🎉 ALL SCRAPERS COMPLETED SUCCESSFULLY!")
        print(
            f"🏆 Complete data collection for {league_subdomain.upper()} finished in {format_duration(overall_duration)}"
        )
    else:
        print(f"⚠️  SCRAPING COMPLETED WITH {failed_scrapers} FAILURE(S)")
        print(
            f"📊 {successful_scrapers} out of {len(scraping_sequence)} scrapers completed successfully"
        )
        print(f"💡 Check the detailed results above for specific error information")

    return successful_scrapers == len(scraping_sequence)


def main():
    """Main function to run the master scraper."""
    print("🎾 TennisScores Master Scraper - Complete Data Collection Suite")
    print("=" * 70)
    print(
        "🔍 This script will run ALL scrapers in sequence for comprehensive data collection"
    )
    print("📊 Includes: Players, Matches, Schedules, Statistics, and Player History")
    print("⚡ Fully automated - no additional prompts after league selection")
    print()

    # Get league input from user
    while True:
        league_subdomain = (
            input("Enter league subdomain (e.g., 'aptachicago', 'nstf'): ")
            .strip()
            .lower()
        )

        if not league_subdomain:
            print("❌ No league subdomain provided. Please try again.")
            continue

        if not validate_league_subdomain(league_subdomain):
            print(
                "❌ Invalid league subdomain format. Please use alphanumeric characters only."
            )
            continue

        break

    target_url = f"https://{league_subdomain}.tenniscores.com"
    print(f"\n🌐 Target URL: {target_url}")

    # Confirm with user
    print(f"\n📋 SCRAPING PLAN:")
    print(f"  🌐 League: {league_subdomain.upper()}")
    print(f"  📊 Scrapers: 5 (Players, Matches, Schedules, Stats, Player History)")
    print(f"  ⏱️  Estimated time: 10-30 minutes (depends on league size)")
    print(f"  🔄 Mode: Fully automated (no additional prompts)")
    print()

    confirm = (
        input("🚀 Ready to start complete data collection? (y/N): ").strip().lower()
    )
    if confirm not in ["y", "yes"]:
        print("❌ Scraping cancelled by user.")
        return

    print(f"\n🎯 Starting complete data collection for {league_subdomain.upper()}...")
    print("💡 This process will take several minutes. Please be patient.")
    print()

    # Run the master scraper
    success = run_master_scraper(league_subdomain)

    print(f"\n{'🎉 SUCCESS!' if success else '⚠️  COMPLETED WITH ISSUES'}")
    print(
        f"Master scraping {'completed successfully' if success else 'finished with some failures'} for {league_subdomain.upper()}"
    )

    return success


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n⚠️  SCRAPING INTERRUPTED BY USER")
        print("=" * 50)
        print("🛑 Master scraper stopped by Ctrl+C")
        print("💡 Partial data may have been saved")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ CRITICAL ERROR IN MASTER SCRAPER")
        print("=" * 50)
        print(f"🚨 Error: {str(e)}")
        print("\n🔍 Full traceback:")
        traceback.print_exc()
        sys.exit(1)
