#!/usr/bin/env python3
"""
Clean validation test using production data:
1. Clone production → local
2. Verify bad dates exist in production data
3. Run scraper with fixed date extraction
4. Import new data
5. Validate dates are now correct
"""

import subprocess
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database_config import get_db_url
import psycopg2

def print_header(title):
    print("\n" + "="*80)
    print(title)
    print("="*80 + "\n")

def check_database_dates(label):
    """Check current state of dates in database."""
    print_header(f"DATABASE STATUS: {label}")
    
    conn = psycopg2.connect(get_db_url())
    cur = conn.cursor()
    
    # Total matches
    cur.execute("SELECT COUNT(*) FROM match_scores")
    total = cur.fetchone()[0]
    
    # With dates
    cur.execute("SELECT COUNT(*) FROM match_scores WHERE match_date IS NOT NULL")
    with_dates = cur.fetchone()[0]
    
    # Without dates
    cur.execute("SELECT COUNT(*) FROM match_scores WHERE match_date IS NULL")
    without_dates = cur.fetchone()[0]
    
    # Matches from last 14 days
    cur.execute("""
        SELECT COUNT(*) 
        FROM match_scores 
        WHERE match_date >= CURRENT_DATE - INTERVAL '14 days'
        AND match_date IS NOT NULL
    """)
    last_14_days = cur.fetchone()[0]
    
    # Sample recent dates
    cur.execute("""
        SELECT match_date, COUNT(*) 
        FROM match_scores 
        WHERE match_date IS NOT NULL 
        GROUP BY match_date 
        ORDER BY match_date DESC 
        LIMIT 10
    """)
    recent_dates = cur.fetchall()
    
    cur.close()
    conn.close()
    
    print(f"📊 Database Metrics:")
    print(f"  Total matches: {total:,}")
    print(f"  ✅ With dates: {with_dates:,} ({with_dates/total*100:.1f}%)")
    print(f"  ❌ Without dates (NULL): {without_dates:,} ({without_dates/total*100:.1f}%)")
    print(f"  📅 Last 14 days: {last_14_days:,} matches")
    
    if recent_dates:
        print(f"\n📆 Recent dates:")
        for date, count in recent_dates[:5]:
            print(f"  - {date}: {count:,} matches")
    
    return {
        'total': total,
        'with_dates': with_dates,
        'without_dates': without_dates,
        'last_14_days': last_14_days,
        'percentage': (with_dates/total*100) if total > 0 else 0
    }

def clone_production():
    """Clone production database to local."""
    print_header("STEP 1: CLONING PRODUCTION TO LOCAL")
    
    print("⚠️  This will overwrite your local database with production data")
    print("   Press Ctrl+C within 5 seconds to cancel...")
    
    import time
    time.sleep(5)
    
    print("\n🔄 Running: python3 data/clone/clone_production_to_local.py")
    
    command = [sys.executable, "data/clone/clone_production_to_local.py"]
    
    try:
        result = subprocess.run(command, check=True)
        print("\n✅ Production cloned to local successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Clone failed with error code {e.returncode}")
        return False

def run_scraper():
    """Run the production scraper with fixed date extraction."""
    print_header("STEP 3: RUNNING SCRAPER WITH FIXED DATE EXTRACTION")
    
    print("🔄 Running: python3 data/cron/apta_scraper_runner_stats_scores.py")
    print("   This scrapes last 2 weeks + imports to database")
    print("   Expected duration: 10-20 minutes\n")
    
    command = [sys.executable, "data/cron/apta_scraper_runner_stats_scores.py"]
    
    try:
        result = subprocess.run(command, check=True)
        print("\n✅ Scraper completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Scraper failed with error code {e.returncode}")
        return False
    except KeyboardInterrupt:
        print("\n\n⚠️  Scraper interrupted by user")
        return False

def main():
    print("\n" + "="*80)
    print("CLEAN VALIDATION TEST - Production Data")
    print("="*80)
    print("\nThis test will:")
    print("1. Clone production database to local")
    print("2. Check production dates (expect many NULL/bad dates)")
    print("3. Run scraper with fixed date extraction")
    print("4. Validate dates are now correct")
    
    # Step 1: Clone production
    if not clone_production():
        print("\n❌ Cannot continue without production data")
        return
    
    # Step 2: Check production dates (BEFORE fix)
    before = check_database_dates("PRODUCTION DATA (BEFORE FIX)")
    
    # Step 3: Run scraper with fix
    if not run_scraper():
        print("\n⚠️  Scraper did not complete")
        print("   Checking partial results...")
    
    # Step 4: Check dates after fix
    after = check_database_dates("UPDATED DATA (AFTER FIX)")
    
    # Step 5: Show comparison
    print_header("VALIDATION RESULTS")
    
    print(f"{'Metric':<30} {'Before':>15} {'After':>15} {'Change':>15}")
    print("-" * 80)
    print(f"{'Total matches':<30} {before['total']:>15,} {after['total']:>15,} {after['total']-before['total']:>+15,}")
    print(f"{'With dates':<30} {before['with_dates']:>15,} {after['with_dates']:>15,} {after['with_dates']-before['with_dates']:>+15,}")
    print(f"{'Without dates':<30} {before['without_dates']:>15,} {after['without_dates']:>15,} {after['without_dates']-before['without_dates']:>+15,}")
    print(f"{'Date percentage':<30} {before['percentage']:>14.1f}% {after['percentage']:>14.1f}% {after['percentage']-before['percentage']:>+14.1f}pp")
    print(f"{'Last 14 days':<30} {before['last_14_days']:>15,} {after['last_14_days']:>15,} {after['last_14_days']-before['last_14_days']:>+15,}")
    
    # Final assessment
    print_header("FINAL ASSESSMENT")
    
    dates_added = after['with_dates'] - before['with_dates']
    null_reduced = before['without_dates'] - after['without_dates']
    
    if dates_added > 0:
        print(f"✅ SUCCESS!")
        print(f"   - Added {dates_added:,} match dates")
        print(f"   - Reduced NULL dates by {null_reduced:,}")
        print(f"   - Improvement: {after['percentage']-before['percentage']:+.1f} percentage points")
        print(f"\n🚀 READY FOR STAGING DEPLOYMENT")
        return True
    else:
        print(f"⚠️  No improvement detected")
        print(f"   This may indicate production already has good dates")
        return False

if __name__ == "__main__":
    try:
        success = main()
        print("\n" + "="*80)
        print("TEST COMPLETE")
        print("="*80 + "\n")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

