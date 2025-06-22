#!/usr/bin/env python3
"""
Debug script to identify the exact issue with availability updates
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import timedelta

from database_utils import execute_query, execute_query_one
from utils.date_utils import date_to_db_timestamp


def debug_availability_update():
    """Debug the availability update process step by step"""

    # Test parameters (adjust these to match your actual test case)
    player_name = "Ross Freedman"  # Adjust to your name
    match_date = "2024-09-24"
    availability_status = 1  # 1 = available
    series = "Beginner"  # Adjust to your series

    print(f"=== DEBUGGING AVAILABILITY UPDATE ===")
    print(f"Player: {player_name}")
    print(f"Date: {match_date}")
    print(f"Status: {availability_status}")
    print(f"Series: {series}")

    try:
        # Step 1: Check series lookup
        print(f"\n1. Looking up series '{series}'...")
        series_record = execute_query_one(
            "SELECT id FROM series WHERE name = %(series)s", {"series": series}
        )

        if not series_record:
            print(f"❌ Series '{series}' not found")
            return False

        series_id = series_record["id"]
        print(f"✅ Series found with ID: {series_id}")

        # Step 2: Test date conversion
        print(f"\n2. Converting date '{match_date}'...")
        try:
            date_obj = date_to_db_timestamp(match_date)
            print(f"✅ Date converted: {match_date} -> {date_obj}")
        except Exception as e:
            print(f"❌ Date conversion failed: {e}")
            return False

        # Step 3: Check for existing record
        print(f"\n3. Checking for existing record...")
        existing_record = execute_query_one(
            """
            SELECT id, availability_status, match_date
            FROM player_availability 
            WHERE player_name = %(player)s 
            AND series_id = %(series_id)s 
            AND DATE(match_date AT TIME ZONE 'UTC') = DATE(%(date)s AT TIME ZONE 'UTC')
            """,
            {"player": player_name.strip(), "series_id": series_id, "date": date_obj},
        )

        if existing_record:
            print(
                f"✅ Found existing record: ID={existing_record['id']}, Status={existing_record['availability_status']}"
            )

            # Update the record
            print(f"\n4. Updating existing record...")
            result = execute_query(
                """
                UPDATE player_availability 
                SET availability_status = %(status)s, updated_at = NOW()
                WHERE id = %(id)s
                """,
                {"status": availability_status, "id": existing_record["id"]},
            )
            print(f"✅ Update executed")

        else:
            print(f"ℹ️ No existing record found")

            # Check for discrepant dates
            print(f"\n4. Checking for discrepant dates...")

            one_day_earlier = date_obj - timedelta(days=1)
            earlier_record = execute_query_one(
                """
                SELECT id, match_date, availability_status 
                FROM player_availability 
                WHERE player_name = %(player)s 
                AND series_id = %(series_id)s 
                AND DATE(match_date AT TIME ZONE 'UTC') = DATE(%(date)s AT TIME ZONE 'UTC')
                """,
                {
                    "player": player_name.strip(),
                    "series_id": series_id,
                    "date": one_day_earlier,
                },
            )

            if earlier_record:
                print(
                    f"🔧 Found discrepant record one day earlier: ID={earlier_record['id']}"
                )

                # Update the discrepant record
                result = execute_query(
                    """
                    UPDATE player_availability 
                    SET match_date = %(correct_date)s, availability_status = %(status)s, updated_at = NOW()
                    WHERE id = %(id)s
                    """,
                    {
                        "correct_date": date_obj,
                        "status": availability_status,
                        "id": earlier_record["id"],
                    },
                )
                print(f"✅ Discrepant record corrected")

            else:
                # Create new record
                print(f"\n5. Creating new record...")
                result = execute_query(
                    """
                    INSERT INTO player_availability (player_name, match_date, availability_status, series_id, updated_at)
                    VALUES (%(player)s, %(date)s, %(status)s, %(series_id)s, NOW())
                    """,
                    {
                        "player": player_name.strip(),
                        "date": date_obj,
                        "status": availability_status,
                        "series_id": series_id,
                    },
                )
                print(f"✅ New record created")

        # Step 5: Verify the operation
        print(f"\n6. Verifying the operation...")
        verification_record = execute_query_one(
            """
            SELECT availability_status, match_date
            FROM player_availability 
            WHERE player_name = %(player)s 
            AND series_id = %(series_id)s 
            AND DATE(match_date AT TIME ZONE 'UTC') = DATE(%(date)s AT TIME ZONE 'UTC')
            """,
            {"player": player_name.strip(), "series_id": series_id, "date": date_obj},
        )

        if verification_record:
            print(f"✅ Verification successful!")
            print(f"   Status: {verification_record['availability_status']}")
            print(f"   Date: {verification_record['match_date']}")
            return True
        else:
            print(f"❌ Verification failed - record not found after operation")

            # Debug: show all records for this player/series
            print(
                f"\n🔍 Debugging: All records for {player_name} in series {series_id}:"
            )
            all_records = execute_query(
                """
                SELECT id, match_date, availability_status, 
                       DATE(match_date AT TIME ZONE 'UTC') as utc_date
                FROM player_availability 
                WHERE player_name = %(player)s 
                AND series_id = %(series_id)s
                ORDER BY match_date DESC
                """,
                {"player": player_name.strip(), "series_id": series_id},
            )

            if all_records:
                for record in all_records:
                    print(
                        f"   ID={record['id']}, Date={record['match_date']}, UTC Date={record['utc_date']}, Status={record['availability_status']}"
                    )
            else:
                print(f"   No records found for this player/series")

            return False

    except Exception as e:
        print(f"❌ Error during debug: {e}")
        import traceback

        print(traceback.format_exc())
        return False


if __name__ == "__main__":
    debug_availability_update()
