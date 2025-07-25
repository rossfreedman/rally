import traceback
from datetime import date, datetime, timedelta, timezone

import pytz
from flask import jsonify, render_template, request, session

from database_utils import execute_query, execute_query_one
from routes.act.schedule import get_matches_for_user_club
from utils.auth import login_required

# Define the application timezone
APP_TIMEZONE = pytz.timezone("America/Chicago")

# Import the correct date utility function for timezone handling
from utils.date_utils import date_to_db_timestamp, normalize_date_string

# Import our date verification utilities
from utils.date_verification import (
    log_date_operation,
    verify_and_fix_date_for_storage,
    verify_date_from_database,
)


def normalize_date_for_db(date_input, target_timezone="UTC"):
    """
    DEPRECATED: Use date_to_db_timestamp from utils.date_utils instead.
    This function is kept for backward compatibility but should be replaced.

    Normalize date input to a consistent TIMESTAMPTZ format for database storage.
    After migration to TIMESTAMPTZ, always stores dates at midnight UTC to avoid timezone edge cases.

    Args:
        date_input: String date in various formats or datetime object
        target_timezone: Target timezone (defaults to 'UTC' for consistency)

    Returns:
        datetime: Timezone-aware datetime object at midnight UTC
    """
    print(
        "⚠️  Warning: Using deprecated normalize_date_for_db. Use date_to_db_timestamp instead."
    )
    try:
        print(f"Normalizing date: {date_input} (type: {type(date_input)})")

        if isinstance(date_input, str):
            # Handle multiple date formats
            if "/" in date_input:
                # Handle MM/DD/YYYY format
                dt = datetime.strptime(date_input, "%m/%d/%Y")
            else:
                # Handle YYYY-MM-DD format
                dt = datetime.strptime(date_input, "%Y-%m-%d")
        elif isinstance(date_input, datetime):
            dt = date_input
        elif hasattr(date_input, "year"):  # Handle date objects
            dt = datetime.combine(date_input, datetime.min.time())
        else:
            raise ValueError(f"Unsupported date type: {type(date_input)}")

        # Set time to midnight for consistency with TIMESTAMPTZ schema
        dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)

        # Always store as UTC timezone to avoid conversion issues
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)

        print(f"Normalized to midnight UTC: {dt}")
        return dt

    except Exception as e:
        print(f"Error normalizing date {date_input}: {str(e)}")
        raise


def get_user_player_records(user_id):
    """
    Get all player records associated with a user via the user_player_associations table.
    Returns a list of player records with their tenniscores_player_id.
    """
    try:
        player_records = execute_query(
            """
            SELECT p.id, p.tenniscores_player_id, p.first_name, p.last_name, 
                   p.series_id, s.name as series_name
            FROM user_player_associations upa
            JOIN players p ON p.tenniscores_player_id = upa.tenniscores_player_id
            JOIN series s ON s.id = p.series_id
            WHERE upa.user_id = %(user_id)s
            ORDER BY p.first_name, p.last_name
            """,
            {"user_id": user_id},
        )

        print(
            f"Found {len(player_records) if player_records else 0} player records for user {user_id}"
        )
        return player_records if player_records else []

    except Exception as e:
        print(f"❌ Error getting user player records: {str(e)}")
        return []


def get_player_availability(player_name, match_date, series, user_id=None):
    """
    Get availability for a player on a specific date using stable user_id reference.
    
    Uses the same stable reference pattern as user_player_associations:
    1. Primary: user_id + match_date (stable - never orphaned)
    2. Fallback: player_id + match_date (for backward compatibility) 
    3. Last resort: player_name + match_date (for legacy data)

    Args:
        player_name: Name of the player (used for fallback matching)
        match_date: Date of the match
        series: Series name
        user_id: User ID for stable lookup (preferred)

    Returns: 1 (available), 2 (unavailable), 3 (not sure), or 0 (not set)
    """
    try:
        print(f"Getting availability for {player_name} on {match_date} in series {series}")
        if user_id:
            print(f"Using user_id {user_id} for stable lookup")

        # Convert match_date to proper format for database query
        normalized_date = date_to_db_timestamp(match_date)
        print(f"Normalized date for query: {normalized_date}")

        # STABLE LOOKUP: Use user_id + match_date (primary method)
        if user_id:
            result = execute_query_one(
                """
                SELECT availability_status, match_date, notes
                FROM player_availability 
                WHERE user_id = %(user_id)s 
                AND DATE(match_date AT TIME ZONE 'UTC') = DATE(%(match_date)s AT TIME ZONE 'UTC')
                """,
                {
                    "user_id": user_id,
                    "match_date": normalized_date,
                },
            )
            
            if result:
                print(f"✅ Found availability via stable user_id lookup: {result}")
                status = result["availability_status"]
                notes = result.get("notes", "") or ""
                return {"status": status, "notes": notes}
            else:
                print(f"No availability found via user_id {user_id}, trying fallback methods")

        # FALLBACK 1: Use player_id + series_id (backward compatibility)
        # Get series ID for fallback lookups
        series_record = execute_query_one(
            "SELECT id FROM series WHERE name = %(series)s", {"series": series}
        )

        if not series_record:
            print(f"No series found with name: {series}")
            return {"status": 0, "notes": ""}

        series_id = series_record["id"]

        # Find player record for fallback
        player_record = None
        if user_id:
            # Try to find player via user associations
            user_players = get_user_player_records(user_id)
            for p in user_players:
                if p["series_name"] == series:
                    player_record = p
                    print(f"Found player via association: {p['first_name']} {p['last_name']} (ID: {p['tenniscores_player_id']})")
                    break

        if not player_record:
            # Final fallback: name-based player lookup
            player_record = execute_query_one(
                "SELECT id, tenniscores_player_id FROM players WHERE CONCAT(first_name, ' ', last_name) = %(player_name)s AND series_id = %(series_id)s",
                {"player_name": player_name.strip(), "series_id": series_id},
            )

        if player_record:
            internal_player_id = player_record["id"]
            print(f"Found player: internal_id={internal_player_id}")

            # FALLBACK 2: Query using player_id + series_id
            result = execute_query_one(
                """
                SELECT availability_status, match_date, notes
                FROM player_availability 
                WHERE player_id = %(player_id)s 
                AND DATE(match_date AT TIME ZONE 'UTC') = DATE(%(match_date)s AT TIME ZONE 'UTC')
                AND series_id = %(series_id)s
                """,
                {
                    "player_id": internal_player_id,
                    "match_date": normalized_date,
                    "series_id": series_id,
                },
            )

            if result:
                print(f"✅ Found availability via player_id fallback: {result}")
                status = result["availability_status"]
                notes = result.get("notes", "") or ""
                return {"status": status, "notes": notes}

        # FALLBACK 3: Name-based search (legacy compatibility)
        print(f"Trying name-based search for {player_name}")
        result = execute_query_one(
            """
            SELECT availability_status, match_date, notes
            FROM player_availability 
            WHERE player_name = %(player_name)s 
            AND DATE(match_date AT TIME ZONE 'UTC') = DATE(%(match_date)s AT TIME ZONE 'UTC')
            AND series_id = %(series_id)s
            """,
            {
                "player_name": player_name.strip(),
                "match_date": normalized_date,
                "series_id": series_id,
            },
        )

        if result:
            print(f"✅ Found availability via name-based fallback: {result}")
            status = result["availability_status"]
            notes = result.get("notes", "") or ""
            return {"status": status, "notes": notes}

        print(f"No availability found for {player_name} on {match_date}")
        return {"status": 0, "notes": ""}

    except Exception as e:
        print(f"Error getting player availability: {str(e)}")
        return {"status": 0, "notes": ""}


def update_player_availability(
    player_name, match_date, availability_status, series, user_id=None, notes=None
):
    """
    Update player availability with enhanced date verification and correction

    This function now includes a comprehensive post-storage verification system that:
    1. Stores the availability record with the intended date
    2. Verifies that the record was stored with the correct date
    3. If a discrepancy is found (most commonly one day earlier due to timezone issues):
       - Searches for records with the wrong date but correct status and player info
       - Updates the discrepant record to have the correct date
       - Verifies the correction was successful
    4. Logs all verification and correction operations for monitoring

    This addresses timezone-related date storage issues that can cause records
    to be stored with dates that are off by one day.
    """
    try:
        print(f"\n=== UPDATE PLAYER AVAILABILITY WITH VERIFICATION ===")
        print(
            f"Input - Player: {player_name}, Date: {match_date}, Status: {availability_status}, Series: {series}"
        )

        # Step 1: Verify and fix the date before storage
        corrected_date, verification_info = verify_and_fix_date_for_storage(
            input_date=match_date,
            intended_display_date=None,  # We could pass this from the frontend if needed
        )

        # Log the date verification result
        log_date_operation(
            operation="PRE_STORAGE_VERIFICATION",
            input_data=match_date,
            output_data=corrected_date,
            verification_info=verification_info,
        )

        if verification_info.get("correction_applied"):
            print(f"⚠️ Date correction applied: {match_date} -> {corrected_date}")

        # Get series ID
        series_record = execute_query_one(
            "SELECT id FROM series WHERE name = %(series)s", {"series": series}
        )

        if not series_record:
            print(f"❌ Series not found: {series}")
            return False

        series_id = series_record["id"]

        # Convert corrected date to datetime object for database storage
        # With TIMESTAMPTZ migration, we now store as midnight UTC consistently
        try:
            if isinstance(corrected_date, str):
                # Use the correct UTC conversion function
                intended_date_obj = date_to_db_timestamp(corrected_date)
                print(
                    f"Converted date for TIMESTAMPTZ storage: {corrected_date} -> {intended_date_obj}"
                )
            else:
                intended_date_obj = corrected_date
        except Exception as e:
            print(f"❌ Error converting corrected date: {e}")
            return False

        print(f"Intended date for storage: {intended_date_obj}")

        # Check if record exists using timezone-aware date comparison
        existing_record = execute_query_one(
            """
            SELECT id, availability_status, match_date
            FROM player_availability 
            WHERE player_name = %(player)s 
            AND series_id = %(series_id)s 
            AND DATE(match_date AT TIME ZONE 'UTC') = DATE(%(date)s AT TIME ZONE 'UTC')
            """,
            {
                "player": player_name.strip(),
                "series_id": series_id,
                "date": intended_date_obj,
            },
        )

        if existing_record:
            print(f"Updating existing record (ID: {existing_record['id']})")
            print(
                f"Old status: {existing_record['availability_status']} -> New status: {availability_status}"
            )

            result = execute_query(
                """
                UPDATE player_availability 
                SET availability_status = %(status)s, notes = %(notes)s, updated_at = NOW()
                WHERE id = %(id)s
                """,
                {
                    "status": availability_status,
                    "notes": notes,
                    "id": existing_record["id"],
                },
            )
        else:
            # Before creating a new record, check for discrepant dates (timezone issues)
            print(
                "No record found with intended date. Checking for date discrepancies..."
            )

            # Check one day earlier (most likely scenario)
            one_day_earlier = intended_date_obj - timedelta(days=1)
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

            # Check one day later (less likely but possible)
            one_day_later = intended_date_obj + timedelta(days=1)
            later_record = execute_query_one(
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
                    "date": one_day_later,
                },
            )

            # If we find a discrepant record, correct it instead of creating a new one
            if earlier_record:
                print(
                    f"🔧 Found record one day earlier: {one_day_earlier} (should be {intended_date_obj})"
                )
                print(f"   Correcting record ID {earlier_record['id']} date and status")

                # Update both the date and status of the discrepant record
                result = execute_query(
                    """
                    UPDATE player_availability 
                    SET match_date = %(correct_date)s, availability_status = %(status)s, updated_at = NOW()
                    WHERE id = %(id)s
                    """,
                    {
                        "correct_date": intended_date_obj,
                        "status": availability_status,
                        "id": earlier_record["id"],
                    },
                )

                # Log the pre-storage correction
                log_date_operation(
                    operation="PRE_STORAGE_CORRECTION",
                    input_data=f"discrepant_date={one_day_earlier}, intended_date={intended_date_obj}",
                    output_data=f"corrected_existing_record_id={earlier_record['id']}",
                    verification_info={
                        "discrepancy_found": True,
                        "discrepancy_type": "one_day_earlier",
                        "correction_type": "update_existing_record",
                    },
                )

            elif later_record:
                print(
                    f"🔧 Found record one day later: {one_day_later} (should be {intended_date_obj})"
                )
                print(f"   Correcting record ID {later_record['id']} date and status")

                # Update both the date and status of the discrepant record
                result = execute_query(
                    """
                    UPDATE player_availability 
                    SET match_date = %(correct_date)s, availability_status = %(status)s, updated_at = NOW()
                    WHERE id = %(id)s
                    """,
                    {
                        "correct_date": intended_date_obj,
                        "status": availability_status,
                        "id": later_record["id"],
                    },
                )

                # Log the pre-storage correction
                log_date_operation(
                    operation="PRE_STORAGE_CORRECTION",
                    input_data=f"discrepant_date={one_day_later}, intended_date={intended_date_obj}",
                    output_data=f"corrected_existing_record_id={later_record['id']}",
                    verification_info={
                        "discrepancy_found": True,
                        "discrepancy_type": "one_day_later",
                        "correction_type": "update_existing_record",
                    },
                )

            else:
                # No discrepant records found, create new record
                print("Creating new availability record")
                print(
                    f"Inserting: player={player_name.strip()}, date={intended_date_obj}, status={availability_status}, series_id={series_id}"
                )

                # Try to get the player's ID for enhanced record creation using proper associations
                player_record = None
                if user_id:
                    # Use proper user-player associations
                    user_players = get_user_player_records(user_id)
                    for p in user_players:
                        if p["series_name"] == series:
                            player_record = p
                            print(
                                f"Found player via association for new record: {p['first_name']} {p['last_name']} (ID: {p['tenniscores_player_id']})"
                            )
                            break

                if not player_record:
                    # Fallback to name-based lookup
                    try:
                        player_record = execute_query_one(
                            "SELECT id, tenniscores_player_id FROM players WHERE CONCAT(first_name, ' ', last_name) = %(player_name)s AND series_id = %(series_id)s",
                            {
                                "player_name": player_name.strip(),
                                "series_id": series_id,
                            },
                        )
                        if player_record:
                            print(
                                f"Found player via name lookup for new record: {player_record['tenniscores_player_id']}"
                            )
                    except Exception as e:
                        print(f"Could not look up player ID for new record: {e}")

                # FIXED: Always require player_id - fail fast instead of creating bad data
                if player_record:
                    internal_player_id = player_record["id"]
                    result = execute_query(
                        """
                        INSERT INTO player_availability (player_name, match_date, availability_status, series_id, player_id, notes, updated_at)
                        VALUES (%(player)s, %(date)s, %(status)s, %(series_id)s, %(player_id)s, %(notes)s, NOW())
                        """,
                        {
                            "player": player_name.strip(),
                            "date": intended_date_obj,
                            "status": availability_status,
                            "series_id": series_id,
                            "player_id": internal_player_id,
                            "notes": notes,
                        },
                    )
                    print(
                        f"✅ Created new record with internal player ID: {internal_player_id}"
                    )
                else:
                    # FIXED: Fail fast instead of creating record with NULL player_id
                    error_msg = f"❌ Cannot create availability record: Player '{player_name.strip()}' not found in series '{series}' (series_id: {series_id})"
                    print(error_msg)
                    print("Available players in this series:")
                    try:
                        available_players = execute_query(
                            "SELECT CONCAT(first_name, ' ', last_name) as full_name FROM players WHERE series_id = %s AND is_active = true ORDER BY first_name, last_name",
                            (series_id,),
                        )
                        for p in available_players[:10]:  # Show first 10
                            print(f"  - {p['full_name']}")
                        if len(available_players) > 10:
                            print(f"  ... and {len(available_players) - 10} more")
                    except Exception as e:
                        print(f"Could not list available players: {e}")

                    raise ValueError(
                        f"Player '{player_name.strip()}' not found in series '{series}'. Please verify the player name and series are correct."
                    )

        # Verify the record was stored correctly
        verification_record = execute_query_one(
            """
            SELECT availability_status, match_date
            FROM player_availability 
            WHERE player_name = %(player)s 
            AND series_id = %(series_id)s 
            AND DATE(match_date AT TIME ZONE 'UTC') = DATE(%(date)s AT TIME ZONE 'UTC')
            """,
            {
                "player": player_name.strip(),
                "series_id": series_id,
                "date": intended_date_obj,
            },
        )

        if verification_record:
            print(
                f"✅ Verification successful: Status={verification_record['availability_status']}, Date={verification_record['match_date']}"
            )
            return True
        else:
            print("❌ Verification failed: Record not found after insert/update")
            return False

    except Exception as e:
        print(f"❌ Error updating player availability: {str(e)}")
        print(traceback.format_exc())
        return False


def get_user_availability(player_name, matches, series, user_id=None):
    """Get availability for a user across multiple matches using proper user-player associations"""
    # First get the series_id
    series_record = execute_query_one(
        "SELECT id FROM series WHERE name = %(series)s", {"series": series}
    )

    if not series_record:
        return []

    # Map numeric status to string status for template
    status_map = {
        1: "available",
        2: "unavailable",
        3: "not_sure",
        None: None,  # No selection made
    }

    availability = []
    for match in matches:
        match_date = match.get("date", "")
        # Get this player's availability for this specific match, using user_id if available
        availability_data = get_player_availability(
            player_name, match_date, series, user_id
        )

        # Extract numeric status and notes
        numeric_status = (
            availability_data.get("status", 0)
            if isinstance(availability_data, dict)
            else availability_data
        )
        notes = (
            availability_data.get("notes", "")
            if isinstance(availability_data, dict)
            else ""
        )

        # Convert numeric status to string status that template expects
        string_status = status_map.get(numeric_status)
        availability.append({"status": string_status, "notes": notes})

    return availability


def init_availability_routes(app):
    @app.route("/debug/availability")
    def debug_availability():
        """Debug route to test availability functionality"""
        return f"<h1>Debug Availability</h1><p>This route works!</p><p>Session keys: {list(session.keys()) if session else 'No session'}</p>"

    # REMOVED: Duplicate /mobile/availability route - now handled by mobile_bp in app/routes/mobile_routes.py
    # This prevents route conflicts and infinite loops
    pass

    # Route moved to mobile_routes.py blueprint

    # DISABLED: The conflicting /api/availability route has been removed
    # The modern implementation is in app/routes/api_routes.py and handles availability updates properly
    pass


def set_player_availability(player_name, match_date, series, status, notes="", user_id=None):
    """
    Set availability for a player using stable user_id reference.
    
    Uses the same stable reference pattern as user_player_associations:
    - Primary: Store using user_id + match_date (stable - never orphaned)
    - Fallback: Continue to populate player_id for backward compatibility
    
    Args:
        player_name: Name of the player
        match_date: Date of the match  
        series: Series name
        status: Availability status (1=available, 2=unavailable, 3=not sure)
        notes: Optional notes
        user_id: User ID for stable storage (required for new records)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"Setting availability for {player_name} on {match_date}: {status}")
        
        # Convert match_date to proper format
        normalized_date = date_to_db_timestamp(match_date)
        
        # Get series_id for backward compatibility
        series_record = execute_query_one(
            "SELECT id FROM series WHERE name = %(series)s", {"series": series}
        )
        
        if not series_record:
            print(f"Series not found: {series}")
            return False
            
        series_id = series_record["id"]

        # Get player record for backward compatibility
        player_record = None
        if user_id:
            # Try to find player via user associations
            user_players = get_user_player_records(user_id)
            for p in user_players:
                if p["series_name"] == series:
                    player_record = p
                    break
        
        if not player_record:
            # Fallback to name-based lookup
            player_record = execute_query_one(
                "SELECT id FROM players WHERE CONCAT(first_name, ' ', last_name) = %(player_name)s AND series_id = %(series_id)s",
                {"player_name": player_name.strip(), "series_id": series_id},
            )

        player_id = player_record["id"] if player_record else None

        if not user_id:
            print("Warning: No user_id provided. Availability may become orphaned during ETL imports.")
            # For backward compatibility, still allow setting availability without user_id
            # but warn that it may become orphaned
        
        # STABLE APPROACH: Use user_id + match_date as primary key (upsert)
        if user_id:
            # Check if record already exists with user_id
            existing = execute_query_one(
                """
                SELECT id FROM player_availability 
                WHERE user_id = %(user_id)s 
                AND DATE(match_date AT TIME ZONE 'UTC') = DATE(%(match_date)s AT TIME ZONE 'UTC')
                """,
                {
                    "user_id": user_id,
                    "match_date": normalized_date,
                },
            )
            
            if existing:
                # Update existing record
                execute_query(
                    """
                    UPDATE player_availability 
                    SET availability_status = %(status)s,
                        notes = %(notes)s,
                        player_id = %(player_id)s,
                        series_id = %(series_id)s,
                        player_name = %(player_name)s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %(user_id)s 
                    AND DATE(match_date AT TIME ZONE 'UTC') = DATE(%(match_date)s AT TIME ZONE 'UTC')
                    """,
                    {
                        "status": status,
                        "notes": notes or "",
                        "player_id": player_id,
                        "series_id": series_id,
                        "player_name": player_name.strip(),
                        "user_id": user_id,
                        "match_date": normalized_date,
                    },
                )
                print(f"✅ Updated availability via user_id {user_id}")
                return True
            else:
                # Insert new record with stable user_id reference
                execute_query(
                    """
                    INSERT INTO player_availability 
                    (user_id, match_date, availability_status, notes, player_id, series_id, player_name, updated_at)
                    VALUES (%(user_id)s, %(match_date)s, %(status)s, %(notes)s, %(player_id)s, %(series_id)s, %(player_name)s, CURRENT_TIMESTAMP)
                    """,
                    {
                        "user_id": user_id,
                        "match_date": normalized_date,
                        "status": status,
                        "notes": notes or "",
                        "player_id": player_id,
                        "series_id": series_id,
                        "player_name": player_name.strip(),
                    },
                )
                print(f"✅ Inserted new availability via user_id {user_id}")
                return True
        
        # FALLBACK: Legacy approach using player_id (for backward compatibility)
        if not player_id:
            print(f"No player found for {player_name} in series {series}")
            return False
            
        # Check if record exists using legacy player_id approach
        existing = execute_query_one(
            """
            SELECT id FROM player_availability 
            WHERE player_id = %(player_id)s 
            AND DATE(match_date AT TIME ZONE 'UTC') = DATE(%(match_date)s AT TIME ZONE 'UTC')
            AND series_id = %(series_id)s
            """,
            {
                "player_id": player_id,
                "match_date": normalized_date,
                "series_id": series_id,
            },
        )
        
        if existing:
            # Update existing record (legacy approach)
            execute_query(
                """
                UPDATE player_availability 
                SET availability_status = %(status)s,
                    notes = %(notes)s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE player_id = %(player_id)s 
                AND DATE(match_date AT TIME ZONE 'UTC') = DATE(%(match_date)s AT TIME ZONE 'UTC')
                AND series_id = %(series_id)s
                """,
                {
                    "status": status,
                    "notes": notes or "",
                    "player_id": player_id,
                    "match_date": normalized_date,
                    "series_id": series_id,
                },
            )
            print(f"⚠️  Updated availability via legacy player_id {player_id}")
            return True
        else:
            # Insert new record (legacy approach) 
            execute_query(
                """
                INSERT INTO player_availability 
                (player_id, series_id, match_date, availability_status, notes, player_name, updated_at)
                VALUES (%(player_id)s, %(series_id)s, %(match_date)s, %(status)s, %(notes)s, %(player_name)s, CURRENT_TIMESTAMP)
                """,
                {
                    "player_id": player_id,
                    "series_id": series_id,
                    "match_date": normalized_date,
                    "status": status,
                    "notes": notes or "",
                    "player_name": player_name.strip(),
                },
            )
            print(f"⚠️  Inserted new availability via legacy player_id {player_id}")
            return True

    except Exception as e:
        print(f"❌ Error setting player availability: {str(e)}")
        print(traceback.format_exc())
        return False
