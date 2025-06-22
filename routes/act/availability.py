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
                   p.series_id, s.name as series_name, upa.is_primary
            FROM user_player_associations upa
            JOIN players p ON p.tenniscores_player_id = upa.tenniscores_player_id
            JOIN series s ON s.id = p.series_id
            WHERE upa.user_id = %(user_id)s
            ORDER BY upa.is_primary DESC, p.first_name, p.last_name
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
    Get availability for a player on a specific date with verification.

    Args:
        player_name: Name of the player (used for fallback matching)
        match_date: Date of the match
        series: Series name
        user_id: Optional user ID to use proper user-player associations

    Returns: 1 (available), 2 (unavailable), 3 (not sure), or 0 (not set)
    """
    try:
        print(
            f"Getting availability for {player_name} on {match_date} in series {series}"
        )
        if user_id:
            print(f"Using user_id {user_id} for proper association lookup")

        # Convert match_date to proper format for database query
        normalized_date = date_to_db_timestamp(match_date)
        print(f"Normalized date for query: {normalized_date}")

        # Get series ID
        series_record = execute_query_one(
            "SELECT id FROM series WHERE name = %(series)s", {"series": series}
        )

        if not series_record:
            print(f"No series found with name: {series}")
            return 0  # Return 0 instead of None for consistency

        series_id = series_record["id"]

        # If user_id is provided, use the proper association to find the player
        player_record = None
        if user_id:
            user_players = get_user_player_records(user_id)
            # Find the player record that matches the series
            for p in user_players:
                if p["series_name"] == series:
                    player_record = p
                    print(
                        f"Found player via association: {p['first_name']} {p['last_name']} (ID: {p['tenniscores_player_id']})"
                    )
                    break

            if not player_record:
                print(f"No player record found for user {user_id} in series {series}")
                # Fallback to name-based lookup
                player_record = execute_query_one(
                    "SELECT id, tenniscores_player_id FROM players WHERE CONCAT(first_name, ' ', last_name) = %(player_name)s AND series_id = %(series_id)s",
                    {"player_name": player_name.strip(), "series_id": series_id},
                )
        else:
            # Fallback to name-based lookup
            player_record = execute_query_one(
                "SELECT id, tenniscores_player_id FROM players WHERE CONCAT(first_name, ' ', last_name) = %(player_name)s AND series_id = %(series_id)s",
                {"player_name": player_name.strip(), "series_id": series_id},
            )

        if not player_record:
            print(f"No player record found for {player_name} in series {series}")
            return 0

        internal_player_id = player_record["id"]
        tenniscores_player_id = player_record["tenniscores_player_id"]

        print(
            f"Found player: internal_id={internal_player_id}, tenniscores_id={tenniscores_player_id}"
        )

        # Query availability using the internal player ID
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

        if not result:
            # Fallback to name-based search if player_id search failed
            print(
                f"No availability found with player ID {internal_player_id}, trying name-based search"
            )
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
            print(f"Name-based availability lookup result: {result}")
        else:
            print(f"Player ID availability lookup result: {result}")

        if not result:
            print(f"No availability found for {player_name} on {match_date}")
            return {"status": 0, "notes": ""}  # Return dict with default values

        # Return both status and notes
        status = result["availability_status"]
        notes = result.get("notes", "") or ""  # Handle None values
        print(f"Found availability status: {status}, notes: {notes}")
        return {"status": status if status is not None else 0, "notes": notes}

    except Exception as e:
        print(f"❌ Error getting player availability: {str(e)}")
        print(traceback.format_exc())
        return 0  # Return 0 on error


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

    @app.route("/mobile/availability", methods=["GET", "POST"])
    @login_required
    def mobile_availability():
        """Handle mobile availability page and updates"""
        if request.method == "POST":
            try:
                data = request.json
                player_name = data.get("player_name")
                match_date = data.get("match_date")
                availability_status = data.get("availability_status")
                series = data.get("series")

                # Validate required fields
                required_fields = [
                    "player_name",
                    "match_date",
                    "availability_status",
                    "series",
                ]
                if not all(field in data for field in required_fields):
                    missing = [f for f in required_fields if f not in data]
                    print(f"Missing required fields: {missing}")
                    return jsonify({"error": "Missing required fields"}), 400

                # Validate availability_status is in valid range
                if availability_status not in [1, 2, 3]:
                    return jsonify({"error": "Invalid availability status"}), 400

                # Get user_id from session for proper user-player associations
                user = session.get("user")
                user_id = user.get("id") if user else None

                notes = data.get("notes", "")  # Get notes from request data
                success = update_player_availability(
                    player_name, match_date, availability_status, series, user_id, notes
                )
                if success:
                    return jsonify({"status": "success"})
                return jsonify({"error": "Failed to update availability"}), 500
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        else:
            try:
                user = session.get("user")
                if not user:
                    return jsonify({"error": "No user in session"}), 400

                user_id = user.get("id")
                player_name = f"{user['first_name']} {user['last_name']}"
                series = user["series"]

                # Get matches for the user's club/series
                matches = get_matches_for_user_club(user)

                # Get this user's availability for each match using proper user-player associations
                availability = get_user_availability(
                    player_name, matches, series, user_id
                )

                # Create match-availability pairs
                match_avail_pairs = list(zip(matches, availability))

                session_data = {
                    "user": user,
                    "authenticated": True,
                    "matches": matches,
                    "availability": availability,
                    "players": [{"name": player_name}],
                }

                return render_template(
                    "mobile/availability.html",
                    session_data=session_data,
                    match_avail_pairs=match_avail_pairs,
                    players=[{"name": player_name}],
                )

            except Exception as e:
                print(f"ERROR in mobile_availability: {str(e)}")
                print(traceback.format_exc())
                return f"Error: {str(e)}", 500

    # Route moved to mobile_routes.py blueprint

    @app.route("/api/availability", methods=["GET", "POST"])
    @login_required
    def handle_availability():
        """Handle availability API requests"""
        if request.method == "POST":
            try:
                print(f"\n=== AVAILABILITY API POST START ===")
                print(f"Request Content-Type: {request.content_type}")
                print(f"Request headers: {dict(request.headers)}")
                print(f"Session user: {session.get('user', {})}")

                # Parse request data with detailed error logging
                data = None

                if request.is_json:
                    try:
                        data = request.get_json()
                        print(f"✅ Successfully parsed JSON data: {data}")
                    except Exception as e:
                        error_msg = f"❌ Error parsing JSON: {str(e)}"
                        print(error_msg)
                        return jsonify({"error": error_msg}), 400
                elif request.form:
                    data = request.form.to_dict()
                    print(f"✅ Successfully parsed form data: {data}")
                else:
                    error_msg = "❌ No JSON or form data found"
                    print(error_msg)
                    return jsonify({"error": error_msg}), 400

                # Validate data is not None
                if not data:
                    error_msg = "❌ Parsed data is empty or None"
                    print(error_msg)
                    return jsonify({"error": error_msg}), 400

                print(f"✅ Final parsed data: {data}")
                print(f"✅ Data type: {type(data)}")
                print(f"✅ Keys in data: {list(data.keys())}")

                # Extract and validate required fields with detailed logging
                player_name = data.get("player_name")
                match_date = data.get("match_date")
                availability_status = data.get("availability_status")
                series = data.get("series")

                print(f"✅ Extracted fields:")
                print(f"  - player_name: '{player_name}' (type: {type(player_name)})")
                print(f"  - match_date: '{match_date}' (type: {type(match_date)})")
                print(
                    f"  - availability_status: '{availability_status}' (type: {type(availability_status)})"
                )
                print(f"  - series: '{series}' (type: {type(series)})")

                # Validate required fields
                required_fields = [
                    "player_name",
                    "match_date",
                    "availability_status",
                    "series",
                ]
                missing_fields = [
                    field
                    for field in required_fields
                    if field not in data or data[field] is None or data[field] == ""
                ]

                if missing_fields:
                    error_msg = f"❌ Missing or empty required fields: {missing_fields}"
                    print(error_msg)
                    return jsonify({"error": error_msg}), 400

                # Convert and validate availability_status
                try:
                    status = int(availability_status)
                    print(f"✅ Converted availability_status to int: {status}")
                except (ValueError, TypeError) as e:
                    error_msg = f"❌ Error converting availability_status '{availability_status}' to int: {str(e)}"
                    print(error_msg)
                    return jsonify({"error": error_msg}), 400

                # Validate status range
                if status not in [1, 2, 3]:
                    error_msg = (
                        f"❌ Invalid availability status: {status} (must be 1, 2, or 3)"
                    )
                    print(error_msg)
                    return jsonify({"error": error_msg}), 400

                # Verify user session
                user = session.get("user")
                if not user:
                    error_msg = "❌ No user found in session"
                    print(error_msg)
                    return jsonify({"error": error_msg}), 401

                user_id = user.get("id")
                expected_player_name = f"{user['first_name']} {user['last_name']}"
                if player_name != expected_player_name:
                    error_msg = f"❌ Player name mismatch: received '{player_name}' vs expected '{expected_player_name}'"
                    print(error_msg)
                    return jsonify({"error": error_msg}), 403

                print(
                    f"✅ All validations passed. Calling update_player_availability with user_id {user_id}..."
                )

                # Call the update function with proper user association
                success = update_player_availability(
                    player_name, match_date, status, series, user_id
                )

                if success:
                    print(f"✅ Successfully updated availability")
                    return jsonify({"status": "success"})
                else:
                    error_msg = "❌ update_player_availability returned False"
                    print(error_msg)
                    return (
                        jsonify(
                            {
                                "error": "Failed to update availability - database operation failed"
                            }
                        ),
                        500,
                    )

            except Exception as e:
                error_msg = (
                    f"❌ Unhandled exception in availability POST handler: {str(e)}"
                )
                print(error_msg)
                print(f"❌ Full traceback:\n{traceback.format_exc()}")
                return jsonify({"error": f"Server error: {str(e)}"}), 500
        else:
            # GET request handling
            try:
                player_name = request.args.get("player_name")
                match_date = request.args.get("match_date")
                series = request.args.get("series")

                print(f"\n=== AVAILABILITY API GET ===")
                print(
                    f"Query params: player_name={player_name}, match_date={match_date}, series={series}"
                )

                is_available = get_player_availability(player_name, match_date, series)
                return jsonify({"is_available": is_available})
            except Exception as e:
                error_msg = f"❌ Error in availability GET handler: {str(e)}"
                print(error_msg)
                return jsonify({"error": error_msg}), 500
