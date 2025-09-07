"""
Team Polls API Routes
Handles poll creation, voting, and results for team captains and players
"""

import uuid
from datetime import datetime

from flask import Blueprint, jsonify, redirect, request, session, url_for

from database_utils import execute_query, execute_query_one, execute_update
from utils.auth import login_required
from utils.logging import log_user_activity

# Create polls blueprint
polls_bp = Blueprint("polls", __name__)


def get_user_team_id(user):
    """Get user's team ID from their player association for the CURRENT league context"""
    try:
        user_id = user.get("id")
        if not user_id:
            print(f"❌ No user_id provided to get_user_team_id")
            return None

        # 🎯 NEW: Get current league context from session
        current_league_context = user.get("league_context")  # This should be the integer DB ID
        current_league_id = user.get("league_id")  # String league identifier
        
        print(f"[DEBUG] get_user_team_id for user {user_id}")
        print(f"[DEBUG] Current league_context: {current_league_context}")
        print(f"[DEBUG] Current league_id: {current_league_id}")

        # 🎯 NEW: Convert league context to proper integer if needed
        league_db_id = None
        if current_league_context:
            try:
                league_db_id = int(current_league_context)
                print(f"[DEBUG] Using league_context as DB ID: {league_db_id}")
            except (ValueError, TypeError):
                print(f"[DEBUG] league_context is not a valid integer: {current_league_context}")
        
        # Fallback: Try to convert string league_id to integer DB ID
        if not league_db_id and current_league_id:
            try:
                league_record = execute_query_one(
                    "SELECT id FROM leagues WHERE league_id = %s", [current_league_id]
                )
                if league_record:
                    league_db_id = league_record["id"]
                    print(f"[DEBUG] Converted league_id '{current_league_id}' to DB ID: {league_db_id}")
            except Exception as e:
                print(f"[DEBUG] Failed to convert league_id to DB ID: {e}")

        # 🎯 NEW: Query team ID filtered by current league context
        if league_db_id:
            # Use league-aware team lookup
            league_aware_team_query = """
                SELECT p.team_id, t.team_name, t.team_alias, l.league_name
                FROM players p
                JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
                JOIN teams t ON p.team_id = t.id
                JOIN leagues l ON p.league_id = l.id
                WHERE upa.user_id = %s 
                AND p.is_active = TRUE 
                AND p.team_id IS NOT NULL
                AND p.league_id = %s
                LIMIT 1
            """
            result = execute_query_one(league_aware_team_query, [user_id, league_db_id])
            if result and result["team_id"]:
                team_display = result.get("team_alias") or result.get("team_name")
                print(f"✅ Found team_id {result['team_id']} for current league context: {team_display}")
                return result["team_id"]
            else:
                print(f"⚠️ No team found for user {user_id} in league {league_db_id}")

        # 🎯 FALLBACK: If no league context or no team found, try any active team
        print(f"[DEBUG] Using fallback - any active team for user {user_id}")
        fallback_team_query = """
            SELECT p.team_id, t.team_name, t.team_alias
            FROM players p
            JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            JOIN teams t ON p.team_id = t.id
            JOIN leagues l ON p.league_id = l.id
            WHERE upa.user_id = %s AND p.is_active = TRUE AND p.team_id IS NOT NULL
            ORDER BY 
                CASE WHEN l.league_id = 'APTA_CHICAGO' THEN 1 ELSE 2 END,
                p.id
            LIMIT 1
        """
        result = execute_query_one(fallback_team_query, [user_id])
        if result and result["team_id"]:
            team_display = result.get("team_alias") or result.get("team_name")
            print(f"✅ Found fallback team_id {result['team_id']}: {team_display}")
            return result["team_id"]

        print(f"❌ Could not find any team_id for user {user_id}")
        return None
        
    except Exception as e:
        print(f"❌ Error getting user team ID: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return None


@polls_bp.route("/api/polls", methods=["POST"])
@login_required
def create_poll():
    """Create a new poll with question and choices"""
    print(f"🔥 === POLL CREATION API STARTED ===")
    try:
        data = request.get_json()
        print(f"🔥 Received data: {data}")

        if not data or not data.get("question") or not data.get("choices"):
            print(
                f"🔥 Missing required data - question: {data.get('question') if data else 'None'}, choices: {data.get('choices') if data else 'None'}"
            )
            return jsonify({"error": "Question and choices are required"}), 400

        question = data["question"].strip()
        choices = [choice.strip() for choice in data["choices"] if choice.strip()]

        print(f"🔥 Processed - question: '{question}', choices: {choices}")

        if len(choices) < 2:
            print(f"🔥 Not enough choices: {len(choices)}")
            return jsonify({"error": "At least 2 choices are required"}), 400

        user_id = session["user"]["id"]
        user = session["user"]

        # PRIORITY-BASED TEAM DETECTION (same as poll viewing API)
        user_team_id = None
        user_team_name = None
        
        # PRIORITY 1: Use team_id from session if available (most reliable for multi-team players)
        session_team_id = user.get("team_id")
        print(f"🔥 Poll Creation: session_team_id from user: {session_team_id}")
        
        if session_team_id:
            try:
                # Get team name for the specific team_id from session
                session_team_query = """
                    SELECT t.id, t.team_name
                    FROM teams t
                    WHERE t.id = %s
                """
                session_team_result = execute_query_one(session_team_query, [session_team_id])
                if session_team_result:
                    user_team_id = session_team_result['id'] 
                    user_team_name = session_team_result['team_name']
                    print(f"🔥 Poll Creation: Using team_id from session: team_id={user_team_id}, team_name={user_team_name}")
                else:
                    print(f"🔥 Poll Creation: Session team_id {session_team_id} not found in teams table")
            except Exception as e:
                print(f"🔥 Poll Creation: Error getting team from session team_id {session_team_id}: {e}")
        
        # PRIORITY 2: Use team_context from user if provided (from composite player URL)
        if not user_team_id:
            team_context = user.get("team_context") if user else None
            if team_context:
                try:
                    # Get team name for the specific team_id from team context
                    team_context_query = """
                        SELECT t.id, t.team_name
                        FROM teams t
                        WHERE t.id = %s
                    """
                    team_context_result = execute_query_one(team_context_query, [team_context])
                    if team_context_result:
                        user_team_id = team_context_result['id'] 
                        user_team_name = team_context_result['team_name']
                        print(f"🔥 Poll Creation: Using team_context from URL: team_id={user_team_id}, team_name={user_team_name}")
                    else:
                        print(f"🔥 Poll Creation: team_context {team_context} not found in teams table")
                except Exception as e:
                    print(f"🔥 Poll Creation: Error getting team from team_context {team_context}: {e}")
        
        # PRIORITY 3: Use legacy get_user_team_id as fallback if no direct team_id
        if not user_team_id:
            print(f"🔥 Poll Creation: No direct team_id, using legacy get_user_team_id fallback")
            user_team_id = get_user_team_id(user)
            if user_team_id:
                try:
                    session_team_query = """
                        SELECT t.id, t.team_name
                        FROM teams t
                        WHERE t.id = %s
                    """
                    session_team_result = execute_query_one(session_team_query, [user_team_id])
                    if session_team_result:
                        user_team_name = session_team_result['team_name']
                        print(f"🔥 Poll Creation: Legacy function provided: team_id={user_team_id}, team_name={user_team_name}")
                except Exception as e:
                    print(f"🔥 Poll Creation: Error getting team name from legacy team_id: {e}")
        
        # If still no team, return error
        if not user_team_id:
            print(
                f"🔥 Could not determine team ID for user: {user.get('email')} (user_id: {user_id})"
            )
            return (
                jsonify(
                    {"error": "Could not determine your team. Please contact support."}
                ),
                400,
            )

        print(f"🔥 Poll Creation: Final team selection: team_id={user_team_id}, team_name={user_team_name}")
        print(f"🔥 User ID: {user_id}, Team ID: {user_team_id}")
        
        # Use the determined team_id for poll creation
        team_id = user_team_id

        # Create the poll with team_id
        poll_query = """
            INSERT INTO polls (created_by, question, team_id)
            VALUES (%s, %s, %s)
            RETURNING id
        """

        print(
            f"🔥 Executing poll insert query with params: [{user_id}, '{question}', '{team_id}']"
        )
        poll_result = execute_query_one(poll_query, [user_id, question, team_id])
        print(f"🔥 Poll insert result: {poll_result}")

        if not poll_result:
            print(f"🔥 Failed to create poll - no result returned")
            return jsonify({"error": "Failed to create poll"}), 500

        poll_id = poll_result["id"]
        print(f"🔥 Created poll with ID: {poll_id}")

        # Add choices
        print(f"🔥 Adding {len(choices)} choices...")
        for i, choice_text in enumerate(choices):
            choice_query = """
                INSERT INTO poll_choices (poll_id, choice_text)
                VALUES (%s, %s)
            """
            print(f"🔥 Adding choice {i+1}: '{choice_text}'")
            execute_update(choice_query, [poll_id, choice_text])

        print(f"🔥 All choices added successfully")

        # Log the activity
        log_user_activity(
            session["user"]["email"],
            "poll_created",
            details=f"Created poll for team {team_id}: {question}",
        )
        print(f"🔥 Activity logged")

        # Generate shareable link
        poll_link = f"/mobile/polls/{poll_id}"

        # Send SMS notifications to team about new poll
        try:
            print(f"🔥 Sending SMS notifications for new poll {poll_id}")
            print(f"🔥 Poll creation request from user: {session['user']['email']}")
            from app.services.notifications_service import send_sms_notification
            
            # Get team members for SMS
            team_members_query = """
                SELECT DISTINCT 
                    u.first_name, 
                    u.last_name, 
                    u.phone_number
                FROM users u
                JOIN user_player_associations upa ON u.id = upa.user_id
                JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                WHERE p.team_id = %s AND u.phone_number IS NOT NULL AND u.phone_number != ''
            """
            team_members = execute_query(team_members_query, [team_id])
            print(f"🔥 Found {len(team_members)} team members for SMS")
            
            if team_members:
                # Create poll choices text
                choices_text = "\n".join([f"• {choice}" for choice in choices])
                
                # Create SMS message with full URL
                base_url = request.url_root.rstrip('/')
                poll_url = f"{base_url}/mobile/polls/{poll_id}"
                message = f"📊 New Team Poll from Rally:\n\n\"{question}\"\n\nChoices:\n{choices_text}\n\nVote now: {poll_url}"
                
                print(f"🔥 SMS Message: {message}")
                
                # Send SMS to each team member (with testing mode override)
                try:
                    from config.sms_testing import SMS_TESTING_MODE, ADMIN_PHONE_NUMBER
                    testing_mode = SMS_TESTING_MODE
                    admin_phone = ADMIN_PHONE_NUMBER
                except ImportError:
                    testing_mode = True  # Default to testing mode if config not found
                    admin_phone = "7732138911"
                
                successful_sends = 0
                processed_phones = set()  # Track processed phone numbers to prevent duplicates
                for member in team_members:
                    try:
                        # Use admin phone for testing, otherwise use member's phone
                        phone_to_use = admin_phone if testing_mode else member["phone_number"]
                        
                        # Check if we've already processed this phone number
                        if phone_to_use in processed_phones:
                            print(f"🔥 ⚠️ Skipping duplicate phone number: {phone_to_use}")
                            continue
                        processed_phones.add(phone_to_use)
                        
                        print(f"🔥 Processing SMS for {member['first_name']} {member['last_name']} ({phone_to_use})")
                        
                        result = send_sms_notification(
                            to_number=phone_to_use,
                            message=message,
                            test_mode=False
                        )
                        
                        if result["success"]:
                            successful_sends += 1
                            print(f"🔥 ✅ SMS sent to {member['first_name']} {member['last_name']} ({phone_to_use})")
                        else:
                            print(f"🔥 ❌ SMS failed to {member['first_name']} {member['last_name']}: {result.get('error')}")
                            
                    except Exception as e:
                        print(f"🔥 ❌ Error sending SMS to {member['first_name']} {member['last_name']}: {e}")
                
                print(f"🔥 SMS Results: {successful_sends} sent to team members")
            else:
                print(f"🔥 No team members found with phone numbers for team {team_id}")
                
        except Exception as e:
            print(f"🔥 ❌ Error sending poll creation SMS: {e}")
            # Don't fail the poll creation if SMS fails

        response_data = {
            "success": True,
            "poll_id": poll_id,
            "poll_link": poll_link,
            "team_id": team_id,
            "message": "Poll created successfully",
        }
        print(f"🔥 Returning success response: {response_data}")

        return jsonify(response_data)

    except Exception as e:
        print(f"🔥 ❌ Error creating poll: {str(e)}")
        import traceback

        print(f"🔥 ❌ Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to create poll"}), 500
    finally:
        print(f"🔥 === POLL CREATION API ENDED ===")
        print()


@polls_bp.route("/api/polls/my-team")
@login_required
def get_my_team_polls():
    """Get all polls for the current user's team using priority-based team detection like analyze-me"""
    try:
        user = session["user"]
        user_id = user["id"]
        user_email = user.get("email")
        
        # PRIORITY-BASED TEAM DETECTION (same as analyze-me and track-byes-courts pages)
        user_team_id = None
        user_team_name = None
        
        # PRIORITY 1: Use team_id from session if available (most reliable for multi-team players)
        session_team_id = user.get("team_id")
        print(f"[DEBUG] Polls: session_team_id from user: {session_team_id}")
        
        if session_team_id:
            try:
                # Get team name for the specific team_id from session
                session_team_query = """
                    SELECT t.id, t.team_name
                    FROM teams t
                    WHERE t.id = %s
                """
                session_team_result = execute_query_one(session_team_query, [session_team_id])
                if session_team_result:
                    user_team_id = session_team_result['id'] 
                    user_team_name = session_team_result['team_name']
                    print(f"[DEBUG] Polls: Using team_id from session: team_id={user_team_id}, team_name={user_team_name}")
                else:
                    print(f"[DEBUG] Polls: Session team_id {session_team_id} not found in teams table")
            except Exception as e:
                print(f"[DEBUG] Polls: Error getting team from session team_id {session_team_id}: {e}")
        
        # PRIORITY 2: Use team_context from user if provided (from composite player URL)
        if not user_team_id:
            team_context = user.get("team_context") if user else None
            if team_context:
                try:
                    # Get team name for the specific team_id from team context
                    team_context_query = """
                        SELECT t.id, t.team_name
                        FROM teams t
                        WHERE t.id = %s
                    """
                    team_context_result = execute_query_one(team_context_query, [team_context])
                    if team_context_result:
                        user_team_id = team_context_result['id'] 
                        user_team_name = team_context_result['team_name']
                        print(f"[DEBUG] Polls: Using team_context from URL: team_id={user_team_id}, team_name={user_team_name}")
                    else:
                        print(f"[DEBUG] Polls: team_context {team_context} not found in teams table")
                except Exception as e:
                    print(f"[DEBUG] Polls: Error getting team from team_context {team_context}: {e}")
        
        # PRIORITY 3: Use legacy get_user_team_id as fallback if no direct team_id
        if not user_team_id:
            print(f"[DEBUG] Polls: No direct team_id, using legacy get_user_team_id fallback")
            user_team_id = get_user_team_id(user)
            if user_team_id:
                try:
                    session_team_query = """
                        SELECT t.id, t.team_name
                        FROM teams t
                        WHERE t.id = %s
                    """
                    session_team_result = execute_query_one(session_team_query, [user_team_id])
                    if session_team_result:
                        user_team_name = session_team_result['team_name']
                        print(f"[DEBUG] Polls: Legacy function provided: team_id={user_team_id}, team_name={user_team_name}")
                except Exception as e:
                    print(f"[DEBUG] Polls: Error getting team name from legacy team_id: {e}")
        
        # If still no team, return error
        if not user_team_id:
            print(
                f"[DEBUG] Could not determine team ID for user: {user.get('email')} (user_id: {user_id})"
            )
            return (
                jsonify(
                    {"error": "Could not determine your team. Please contact support."}
                ),
                400,
            )

        print(f"[DEBUG] Polls: Final team selection: team_id={user_team_id}, team_name={user_team_name}")
        print(f"[DEBUG] Getting polls for user: {user.get('email')}")
        print(f"[DEBUG] Team ID: {user_team_id} (integer foreign key)")
        
        # Use the determined team_id for the rest of the function
        team_id = user_team_id

        # Get polls for this specific team only
        polls_query = """
            SELECT 
                p.id,
                p.question,
                p.created_at,
                p.created_by,
                p.team_id,
                creator.first_name,
                creator.last_name,
                COUNT(DISTINCT pr.player_id) as response_count,
                CASE WHEN p.created_by = %s THEN true ELSE false END as is_creator
            FROM polls p
            LEFT JOIN users creator ON p.created_by = creator.id
            LEFT JOIN poll_responses pr ON p.id = pr.poll_id
            WHERE p.team_id = %s
            GROUP BY p.id, p.question, p.created_at, p.created_by, p.team_id, creator.first_name, creator.last_name
            ORDER BY p.created_at DESC
        """

        print(f"[DEBUG] Executing polls query for team_id: {team_id}...")
        polls = execute_query(polls_query, [user_id, team_id])
        print(f"[DEBUG] Found {len(polls)} polls for team {team_id}")

        # Get choices for each poll
        for poll in polls:
            choices_query = """
                SELECT id, choice_text
                FROM poll_choices
                WHERE poll_id = %s
                ORDER BY id
            """
            try:
                poll["choices"] = execute_query(choices_query, [poll["id"]])
                print(f"[DEBUG] Poll {poll['id']} has {len(poll['choices'])} choices")
            except Exception as e:
                print(f"[DEBUG] Error getting choices for poll {poll['id']}: {e}")
                poll["choices"] = []

        # Get team name for response
        team_name_query = """
            SELECT team_name, team_alias FROM teams WHERE id = %s
        """
        team_info = execute_query_one(team_name_query, [team_id])
        team_display_name = (
            team_info.get("team_alias") or team_info.get("team_name")
            if team_info
            else f"Team {team_id}"
        )

        print(
            f"[DEBUG] Returning {len(polls)} polls for team {team_id} ({team_display_name})"
        )
        return jsonify(
            {
                "success": True,
                "polls": polls,
                "team_id": team_id,
                "team_name": team_display_name,
            }
        )

    except Exception as e:
        print(f"Error getting team polls: {str(e)}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return (
            jsonify(
                {
                    "error": "Failed to get polls",
                    "debug": (
                        str(e)
                        if user.get("email") == "rossfreedman@gmail.com"
                        else None
                    ),
                }
            ),
            500,
        )


@polls_bp.route("/api/polls/team/<int:team_id>")
@login_required
def get_team_polls(team_id):
    """Get all polls for a team (legacy endpoint - deprecated)"""
    try:
        user = session["user"]
        user_id = user["id"]

        print(f"[DEBUG] DEPRECATED: Getting team polls for user: {user.get('email')}")
        print(f"[DEBUG] User club: {user.get('club')}, series: {user.get('series')}")
        print(f"[WARNING] This endpoint is deprecated. Use /api/polls/my-team instead.")

        # Get all polls - including those with NULL team_id (which is how polls are currently created)
        # TODO: In the future, we may want to filter by actual team membership
        polls_query = """
            SELECT 
                p.id,
                p.question,
                p.created_at,
                p.created_by,
                p.team_id,
                creator.first_name,
                creator.last_name,
                COUNT(DISTINCT pr.player_id) as response_count,
                CASE WHEN p.created_by = %s THEN true ELSE false END as is_creator
            FROM polls p
            LEFT JOIN users creator ON p.created_by = creator.id
            LEFT JOIN poll_responses pr ON p.id = pr.poll_id
            WHERE p.team_id IS NULL OR p.team_id = %s
            GROUP BY p.id, p.question, p.created_at, p.created_by, p.team_id, creator.first_name, creator.last_name
            ORDER BY p.created_at DESC
        """

        print(f"[DEBUG] Executing polls query for team_id: {team_id}...")
        polls = execute_query(polls_query, [user_id, team_id])
        print(f"[DEBUG] Found {len(polls)} polls")

        # Get choices for each poll
        for poll in polls:
            choices_query = """
                SELECT id, choice_text
                FROM poll_choices
                WHERE poll_id = %s
                ORDER BY id
            """
            try:
                poll["choices"] = execute_query(choices_query, [poll["id"]])
                print(f"[DEBUG] Poll {poll['id']} has {len(poll['choices'])} choices")
            except Exception as e:
                print(f"[DEBUG] Error getting choices for poll {poll['id']}: {e}")
                poll["choices"] = []

        print(f"[DEBUG] Returning {len(polls)} polls successfully")
        return jsonify({"success": True, "polls": polls})

    except Exception as e:
        print(f"Error getting team polls: {str(e)}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return (
            jsonify(
                {
                    "error": "Failed to get polls",
                    "debug": (
                        str(e)
                        if user.get("email") == "rossfreedman@gmail.com"
                        else None
                    ),
                }
            ),
            500,
        )


@polls_bp.route("/api/polls/<int:poll_id>")
def get_poll_details(poll_id):
    """Get poll details + current results (public endpoint for sharing)"""
    try:
        # Get poll details with team_id
        poll_query = """
            SELECT 
                p.id,
                p.question,
                p.created_at,
                p.team_id,
                u.first_name,
                u.last_name
            FROM polls p
            LEFT JOIN users u ON p.created_by = u.id
            WHERE p.id = %s
        """

        poll = execute_query_one(poll_query, [poll_id])

        if not poll:
            return jsonify({"error": "Poll not found"}), 404

        # If user is logged in, verify they can access this poll (same team)
        if "user" in session:
            user = session["user"]
            user_team_id = get_user_team_id(user)
            poll_team_id = poll.get("team_id")

            # Allow access if:
            # 1. Poll has no team_id (legacy polls)
            # 2. User's team matches poll's team (integer comparison)
            # 3. Poll team_id is None/NULL
            if poll_team_id and user_team_id and int(poll_team_id) != int(user_team_id):
                print(
                    f"[SECURITY] User team {user_team_id} attempting to access poll from team {poll_team_id}"
                )
                return jsonify({"error": "Poll not found"}), 404

        # Get choices with vote counts
        choices_query = """
            SELECT 
                pc.id,
                pc.choice_text,
                COUNT(pr.id) as vote_count
            FROM poll_choices pc
            LEFT JOIN poll_responses pr ON pc.id = pr.choice_id
            WHERE pc.poll_id = %s
            GROUP BY pc.id, pc.choice_text
            ORDER BY pc.id
        """

        choices = execute_query(choices_query, [poll_id])

        # Get total votes
        total_votes = sum(choice["vote_count"] for choice in choices)

        # Calculate percentages
        for choice in choices:
            choice["percentage"] = (
                (choice["vote_count"] / total_votes * 100) if total_votes > 0 else 0
            )

        # Get voter details (who voted for what)
        voters_query = """
            SELECT 
                pr.choice_id,
                p.first_name,
                p.last_name,
                pr.responded_at
            FROM poll_responses pr
            JOIN players p ON pr.player_id = p.id
            WHERE pr.poll_id = %s
            ORDER BY pr.responded_at DESC
        """

        voters = execute_query(voters_query, [poll_id])

        # Group voters by choice
        voters_by_choice = {}
        for voter in voters:
            choice_id = voter["choice_id"]
            if choice_id not in voters_by_choice:
                voters_by_choice[choice_id] = []
            voters_by_choice[choice_id].append(
                {
                    "name": f"{voter['first_name']} {voter['last_name']}",
                    "responded_at": voter["responded_at"],
                }
            )

        # Check if current user has voted (if logged in)
        user_vote = None
        if "user" in session:
            # Get user's player ID
            user_player_query = """
                SELECT p.id
                FROM players p
                JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
                WHERE upa.user_id = %s
                LIMIT 1
            """
            user_player = execute_query_one(user_player_query, [session["user"]["id"]])

            if user_player:
                vote_query = """
                    SELECT choice_id
                    FROM poll_responses
                    WHERE poll_id = %s AND player_id = %s
                """
                user_vote_result = execute_query_one(
                    vote_query, [poll_id, user_player["id"]]
                )
                if user_vote_result:
                    user_vote = user_vote_result["choice_id"]

        return jsonify(
            {
                "success": True,
                "poll": poll,
                "choices": choices,
                "total_votes": total_votes,
                "voters_by_choice": voters_by_choice,
                "user_vote": user_vote,
            }
        )

    except Exception as e:
        print(f"Error getting poll details: {str(e)}")
        return jsonify({"error": "Failed to get poll details"}), 500


@polls_bp.route("/api/polls/<int:poll_id>/respond", methods=["POST"])
@login_required
def respond_to_poll(poll_id):
    """Submit a player's response to a poll"""
    print(f"🗳️  === POLL VOTE SUBMISSION API STARTED ===")
    print(f"🗳️  Poll ID: {poll_id}")
    try:
        data = request.get_json()
        print(f"🗳️  Received data: {data}")

        if not data or not data.get("choice_id"):
            print(f"🗳️  Missing choice_id in request data")
            return jsonify({"error": "Choice ID is required"}), 400

        choice_id = data["choice_id"]
        print(f"🗳️  Choice ID: {choice_id}")

        # Get user's team ID for security check
        user = session["user"]
        user_id = user["id"]
        user_team_id = get_user_team_id(user)
        print(f"🗳️  User ID: {user_id}, Team ID: {user_team_id}")

        # Verify the poll exists and user can access it (same team)
        poll_query = """
            SELECT team_id FROM polls WHERE id = %s
        """
        poll = execute_query_one(poll_query, [poll_id])

        if not poll:
            print(f"🗳️  Poll {poll_id} not found")
            return jsonify({"error": "Poll not found"}), 404

        poll_team_id = poll.get("team_id")

        # Security check: Verify user can vote on this poll (same team - integer comparison)
        if poll_team_id and user_team_id and int(poll_team_id) != int(user_team_id):
            print(
                f"🗳️  SECURITY: User team {user_team_id} attempting to vote on poll from team {poll_team_id}"
            )
            return jsonify({"error": "Poll not found"}), 404

        # Get user's player ID
        user_player_query = """
            SELECT p.id
            FROM players p
            JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            WHERE upa.user_id = %s
            LIMIT 1
        """
        user_player = execute_query_one(user_player_query, [user_id])
        print(f"🗳️  User player query result: {user_player}")

        if not user_player:
            print(f"🗳️  No player profile found for user {user_id}")
            return jsonify({"error": "Player profile not found"}), 400

        player_id = user_player["id"]
        print(f"🗳️  Player ID: {player_id}")

        # Verify the choice exists for this poll
        choice_query = """
            SELECT id FROM poll_choices
            WHERE id = %s AND poll_id = %s
        """
        choice_exists = execute_query_one(choice_query, [choice_id, poll_id])
        print(f"🗳️  Choice exists check: {choice_exists}")

        if not choice_exists:
            print(f"🗳️  Invalid choice {choice_id} for poll {poll_id}")
            return jsonify({"error": "Invalid choice for this poll"}), 400

        # Check if user has already voted
        existing_vote_query = """
            SELECT id FROM poll_responses
            WHERE poll_id = %s AND player_id = %s
        """
        existing_vote = execute_query_one(existing_vote_query, [poll_id, player_id])
        print(f"🗳️  Existing vote check: {existing_vote}")

        if existing_vote:
            # Update existing vote
            print(f"🗳️  Updating existing vote")
            update_query = """
                UPDATE poll_responses
                SET choice_id = %s, responded_at = NOW()
                WHERE poll_id = %s AND player_id = %s
            """
            execute_update(update_query, [choice_id, poll_id, player_id])
        else:
            # Insert new vote
            print(f"🗳️  Inserting new vote")
            insert_query = """
                INSERT INTO poll_responses (poll_id, choice_id, player_id)
                VALUES (%s, %s, %s)
            """
            execute_update(insert_query, [poll_id, choice_id, player_id])

        print(f"🗳️  Vote successfully processed")

        # Send SMS notifications to team about the vote
        try:
            print(f"🗳️  Sending SMS notifications for poll vote {poll_id}")
            from app.services.notifications_service import send_sms_notification
            
            # Get poll details and current results
            poll_details_query = """
                SELECT 
                    p.question,
                    p.team_id,
                    u.first_name as voter_first_name,
                    u.last_name as voter_last_name,
                    pc.choice_text as voted_choice
                FROM polls p
                JOIN poll_choices pc ON p.id = pc.poll_id
                JOIN users u ON u.id = %s
                WHERE p.id = %s AND pc.id = %s
            """
            poll_details = execute_query_one(poll_details_query, [user_id, poll_id, choice_id])
            
            if poll_details:
                # Get current poll results
                results_query = """
                    SELECT 
                        pc.choice_text,
                        COUNT(pr.id) as vote_count
                    FROM poll_choices pc
                    LEFT JOIN poll_responses pr ON pc.id = pr.choice_id
                    WHERE pc.poll_id = %s
                    GROUP BY pc.id, pc.choice_text
                    ORDER BY pc.id
                """
                results = execute_query(results_query, [poll_id])
                
                # Get team members for SMS
                team_members_query = """
                    SELECT DISTINCT 
                        u.first_name, 
                        u.last_name, 
                        u.phone_number
                    FROM users u
                    JOIN user_player_associations upa ON u.id = upa.user_id
                    JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                    WHERE p.team_id = %s AND u.phone_number IS NOT NULL AND u.phone_number != ''
                """
                team_members = execute_query(team_members_query, [poll_details["team_id"]])
                
                if team_members:
                    # Create results summary
                    total_votes = sum(r["vote_count"] for r in results)
                    results_text = "\n".join([f"• {r['choice_text']}: {r['vote_count']} vote{'s' if r['vote_count'] != 1 else ''}" for r in results])
                    
                    # Create SMS message with full URL
                    base_url = request.url_root.rstrip('/')
                    poll_url = f"{base_url}/mobile/polls/{poll_id}"
                    message = f"🗳️ Poll Update from Rally:\n\n\"{poll_details['question']}\"\n\n{poll_details['voter_first_name']} {poll_details['voter_last_name']} voted: {poll_details['voted_choice']}\n\nCurrent Results ({total_votes} total votes):\n{results_text}\n\nView poll: {poll_url}"
                    
                    print(f"🗳️  SMS Message: {message}")
                    
                    # Send SMS to each team member (with testing mode override)
                    try:
                        from config.sms_testing import SMS_TESTING_MODE, ADMIN_PHONE_NUMBER
                        testing_mode = SMS_TESTING_MODE
                        admin_phone = ADMIN_PHONE_NUMBER
                    except ImportError:
                        testing_mode = True  # Default to testing mode if config not found
                        admin_phone = "7732138911"
                    
                    successful_sends = 0
                    for member in team_members:
                        try:
                            # Use admin phone for testing, otherwise use member's phone
                            phone_to_use = admin_phone if testing_mode else member["phone_number"]
                            
                            result = send_sms_notification(
                                to_number=phone_to_use,
                                message=message,
                                test_mode=False
                            )
                            
                            if result["success"]:
                                successful_sends += 1
                                print(f"🗳️  ✅ SMS sent to {member['first_name']} {member['last_name']} ({phone_to_use})")
                            else:
                                print(f"🗳️  ❌ SMS failed to {member['first_name']} {member['last_name']}: {result.get('error')}")
                                
                        except Exception as e:
                            print(f"🗳️  ❌ Error sending SMS to {member['first_name']} {member['last_name']}: {e}")
                    
                    print(f"🗳️  SMS Results: {successful_sends} sent to team members")
                else:
                    print(f"🗳️  No team members found with phone numbers for team {poll_details['team_id']}")
            else:
                print(f"🗳️  Could not get poll details for SMS notification")
                
        except Exception as e:
            print(f"🗳️  ❌ Error sending poll vote SMS: {e}")
            # Don't fail the vote if SMS fails

        # Log the activity
        log_user_activity(
            session["user"]["email"], "poll_voted", details=f"Voted in poll {poll_id}"
        )

        response_data = {"success": True, "message": "Vote submitted successfully"}
        print(f"🗳️  Returning success response: {response_data}")

        return jsonify(response_data)

    except Exception as e:
        print(f"🗳️  ❌ Error submitting poll response: {str(e)}")
        import traceback

        print(f"🗳️  ❌ Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to submit vote"}), 500
    finally:
        print(f"🗳️  === POLL VOTE SUBMISSION API ENDED ===")
        print()


@polls_bp.route("/api/polls/<int:poll_id>", methods=["DELETE"])
@login_required
def delete_poll(poll_id):
    """Delete a poll (admin only)"""
    print(f"🗑️  === POLL DELETION API STARTED ===")
    print(f"🗑️  Poll ID: {poll_id}")
    try:
        # Check if user is admin
        from app.services.admin_service import is_user_admin

        user_email = session["user"]["email"]

        if not is_user_admin(user_email):
            print(f"🗑️  User {user_email} is not admin, access denied")
            return jsonify({"error": "Admin access required"}), 403

        print(f"🗑️  Admin check passed for user: {user_email}")

        # Check if poll exists
        poll_query = """
            SELECT id, question, created_by
            FROM polls
            WHERE id = %s
        """
        poll = execute_query_one(poll_query, [poll_id])
        print(f"🗑️  Poll exists check: {poll}")

        if not poll:
            print(f"🗑️  Poll {poll_id} not found")
            return jsonify({"error": "Poll not found"}), 404

        # Delete poll responses first (foreign key constraint)
        print(f"🗑️  Deleting poll responses...")
        delete_responses_query = """
            DELETE FROM poll_responses
            WHERE poll_id = %s
        """
        execute_update(delete_responses_query, [poll_id])

        # Delete poll choices
        print(f"🗑️  Deleting poll choices...")
        delete_choices_query = """
            DELETE FROM poll_choices
            WHERE poll_id = %s
        """
        execute_update(delete_choices_query, [poll_id])

        # Finally delete the poll
        print(f"🗑️  Deleting poll...")
        delete_poll_query = """
            DELETE FROM polls
            WHERE id = %s
        """
        execute_update(delete_poll_query, [poll_id])

        print(f"🗑️  Poll deletion successful")

        # Log the activity
        log_user_activity(
            user_email,
            "admin_action",
            action="delete_poll",
            details=f'Deleted poll: {poll["question"]} (ID: {poll_id})',
        )

        response_data = {"success": True, "message": "Poll deleted successfully"}
        print(f"🗑️  Returning success response: {response_data}")

        return jsonify(response_data)

    except Exception as e:
        print(f"🗑️  ❌ Error deleting poll: {str(e)}")
        import traceback

        print(f"🗑️  ❌ Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to delete poll"}), 500
    finally:
        print(f"🗑️  === POLL DELETION API ENDED ===")
        print()


# ✅ FIX: Add missing /vote endpoint that tests expect
@polls_bp.route("/api/polls/<int:poll_id>/vote", methods=["POST"])
@login_required
def vote_on_poll(poll_id):
    """Submit a player's response to a poll (legacy endpoint)"""
    print(f"🗳️  === LEGACY POLL VOTE ENDPOINT CALLED ===")
    print(f"🗳️  Redirecting to /respond endpoint")
    
    # ✅ FIX: Simply call the respond_to_poll function
    return respond_to_poll(poll_id)


@polls_bp.route("/api/polls/<int:poll_id>/text-team", methods=["POST"])
@login_required
def text_team_about_poll(poll_id):
    """Send SMS to team members about a poll"""
    print(f"📱 === POLL SMS API STARTED ===")
    print(f"📱 Poll ID: {poll_id}")
    
    try:
        from app.services.notifications_service import send_sms_notification
        
        # Get poll details
        poll_query = """
            SELECT 
                p.id,
                p.question,
                p.team_id,
                p.created_by,
                u.first_name as creator_first_name,
                u.last_name as creator_last_name
            FROM polls p
            LEFT JOIN users u ON p.created_by = u.id
            WHERE p.id = %s
        """
        poll = execute_query_one(poll_query, [poll_id])
        
        if not poll:
            print(f"📱 Poll {poll_id} not found")
            return jsonify({"error": "Poll not found"}), 404
        
        # Get user's team information for finding team members
        user = session["user"]
        user_team_id = None
        
        # Get user's team ID (same logic as in poll creation)
        session_team_id = user.get("team_id")
        if session_team_id:
            user_team_id = session_team_id
        else:
            # Fallback: get from user_player_associations
            team_query = """
                SELECT DISTINCT p.team_id
                FROM players p
                JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
                WHERE upa.user_id = %s AND p.team_id IS NOT NULL
                LIMIT 1
            """
            team_result = execute_query_one(team_query, [user["id"]])
            if team_result:
                user_team_id = team_result["team_id"]
        
        if not user_team_id:
            print(f"📱 User has no team association")
            return jsonify({"error": "No team found for user"}), 400
        
        print(f"📱 User team ID: {user_team_id}")
        
        # Get total team members count first (for debugging)
        total_team_members_query = """
            SELECT COUNT(DISTINCT u.id) as total_count
            FROM users u
            JOIN user_player_associations upa ON u.id = upa.user_id
            JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
            WHERE p.team_id = %s
        """
        
        total_result = execute_query_one(total_team_members_query, [user_team_id])
        total_team_members = total_result["total_count"] if total_result else 0
        
        print(f"📱 Total team members (including you): {total_team_members}")
        
        # Get team members with phone numbers
        team_members_query = """
            SELECT DISTINCT
                u.id,
                u.first_name,
                u.last_name,
                u.email,
                u.phone_number,
                p.team_id
            FROM users u
            JOIN user_player_associations upa ON u.id = upa.user_id
            JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
            WHERE p.team_id = %s 
            AND u.phone_number IS NOT NULL 
            AND u.phone_number != ''
            ORDER BY u.first_name, u.last_name
        """
        
        team_members = execute_query(team_members_query, [user_team_id])
        print(f"📱 Found {len(team_members)} team members with phone numbers")
        
        if not team_members:
            if total_team_members == 0:
                return jsonify({"error": "No team members found."}), 400
            else:
                return jsonify({"error": f"No team members have phone numbers set. Found {total_team_members} team members total, but none have added phone numbers in their Profile Settings."}), 400
        
        # Generate poll link with full URL
        base_url = request.url_root.rstrip('/')
        poll_url = f"{base_url}/mobile/polls/{poll_id}"
        
        # Create SMS message
        message = f"📊 Team Poll from Rally:\n\n\"{poll['question']}\"\n\nVote now:\n{poll_url}"
        
        print(f"📱 SMS Message: {message}")
        
        # Send SMS to each team member
        successful_sends = 0
        failed_sends = 0
        send_results = []
        
        for member in team_members:
            try:
                result = send_sms_notification(
                    to_number=member["phone_number"],
                    message=message,
                    test_mode=False
                )
                
                if result["success"]:
                    successful_sends += 1
                    send_results.append({
                        "name": f"{member['first_name']} {member['last_name']}",
                        "phone": member["phone_number"],
                        "status": "sent",
                        "message_sid": result.get("message_sid")
                    })
                    print(f"📱 ✅ SMS sent to {member['first_name']} {member['last_name']} ({member['phone_number']})")
                else:
                    failed_sends += 1
                    send_results.append({
                        "name": f"{member['first_name']} {member['last_name']}",
                        "phone": member["phone_number"],
                        "status": "failed",
                        "error": result.get("error")
                    })
                    print(f"📱 ❌ SMS failed to {member['first_name']} {member['last_name']}: {result.get('error')}")
                    
            except Exception as e:
                failed_sends += 1
                send_results.append({
                    "name": f"{member['first_name']} {member['last_name']}",
                    "phone": member["phone_number"],
                    "status": "error",
                    "error": str(e)
                })
                print(f"📱 ❌ Exception sending to {member['first_name']} {member['last_name']}: {str(e)}")
        
        # Log admin action for audit
        from app.services.admin_service import log_admin_action
        log_admin_action(
            admin_email=user["email"],
            action="send_poll_sms",
            details={
                "poll_id": poll_id,
                "poll_question": poll["question"][:50] + "..." if len(poll["question"]) > 50 else poll["question"],
                "recipients_count": len(team_members),
                "successful_sends": successful_sends,
                "failed_sends": failed_sends
            }
        )
        
        print(f"📱 SMS Results: {successful_sends} sent, {failed_sends} failed")
        
        # Return results with confirmation message
        if successful_sends > 0:
            confirmation_message = f"Confirmation: The team has been sent the new poll: \"{poll['question']}\""
            return jsonify({
                "success": True,
                "message": confirmation_message,
                "recipients_count": successful_sends,
                "total_attempted": len(team_members),
                "successful_sends": successful_sends,
                "failed_sends": failed_sends,
                "results": send_results
            })
        else:
            return jsonify({
                "error": f"Failed to send SMS to any team members ({failed_sends} failures)",
                "successful_sends": successful_sends,
                "failed_sends": failed_sends,
                "results": send_results
            }), 500
            
    except Exception as e:
        print(f"📱 Error in poll SMS API: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Failed to send SMS to team"}), 500
