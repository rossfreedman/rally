#!/usr/bin/env python3
"""
Check all schedule entries for Tennaqua in staging
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_tennaqua_schedule():
    print("🔍 Checking Tennaqua schedule entries in staging")
    print("=" * 60)
    staging_url = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"
    parsed = urlparse(staging_url)
    conn = psycopg2.connect(
        dbname=parsed.path[1:],
        user=parsed.username,
        password=parsed.password,
        host=parsed.hostname,
        port=parsed.port
    )
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, match_date, match_time, home_team, away_team
        FROM schedule
        WHERE home_team ILIKE '%Tennaqua%' OR away_team ILIKE '%Tennaqua%'
        ORDER BY match_date ASC, match_time ASC
        LIMIT 20;
    """)
    rows = cursor.fetchall()
    if rows:
        for row in rows:
            print(f"ID: {row[0]}, Date: {row[1]}, Time: {row[2]}, Home: {row[3]}, Away: {row[4]}")
    else:
        print("No schedule entries found for Tennaqua.")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_tennaqua_schedule() 