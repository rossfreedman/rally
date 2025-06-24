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
    """Get user's team ID from their player association (integer foreign key)"""
    try:
        user_id = user.get("id")
        if not user_id:
            print(f"❌ No user_id provided to get_user_team_id")
            return None

        # ✅ FIX: More robust team ID lookup with fallbacks
        # Try primary association first
        primary_team_query = """
            SELECT p.team_id
            FROM players p
            JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            WHERE upa.user_id = %s AND upa.is_primary = TRUE AND p.is_active = TRUE AND p.team_id IS NOT NULL
            LIMIT 1
        """
        result = execute_query_one(primary_team_query, [user_id])
        if result and result["team_id"]:
            print(f"✅ Found team_id via primary association: {result['team_id']}")
            return result["team_id"]

        # ✅ FIX: Fallback to any association if no primary
        any_team_query = """
            SELECT p.team_id
            FROM players p
            JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            JOIN leagues l ON p.league_id = l.id
            WHERE upa.user_id = %s AND p.is_active = TRUE AND p.team_id IS NOT NULL
            ORDER BY 
                CASE WHEN l.league_id = 'APTA_CHICAGO' THEN 1 ELSE 2 END,
                p.id
            LIMIT 1
        """
        result = execute_query_one(any_team_query, [user_id])
        if result and result["team_id"]:
            print(f"✅ Found team_id via any association: {result['team_id']}")
            return result["team_id"]

        # ✅ FIX: Last resort - try to create team assignment if player exists but no team
        try:
            from app.services.auth_service_refactored import assign_player_to_team
            from app.models.database_models import Player
            from database_config import get_db_session
            
            db_session = get_db_session()
            try:
                # Find user's player without team
                unassigned_player_query = """
                    SELECT p.id
                    FROM players p
                    JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
                    WHERE upa.user_id = %s AND p.is_active = TRUE AND p.team_id IS NULL
                    LIMIT 1
                """
                unassigned = execute_query_one(unassigned_player_query, [user_id])
                
                if unassigned:
                    player = db_session.query(Player).filter(Player.id == unassigned["id"]).first()
                    if player:
                        print(f"🔧 Attempting to assign team to unassigned player {player.id}")
                        team_assigned = assign_player_to_team(player, db_session)
                        if team_assigned:
                            db_session.commit()
                            print(f"✅ Successfully assigned team to player {player.id}")
                            # Try the query again
                            result = execute_query_one(any_team_query, [user_id])
                            if result and result["team_id"]:
                                return result["team_id"]
                        else:
                            db_session.rollback()
            finally:
                db_session.close()
        except Exception as team_assignment_error:
            print(f"⚠️ Team assignment attempt failed: {team_assignment_error}")

        print(f"❌ Could not find team_id for user {user_id}")
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

        # Get user's team ID from player association
        team_id = get_user_team_id(user)
        if not team_id:
            print(
                f"🔥 Could not determine team ID for user: {user.get('email')} (user_id: {user_id})"
            )
            return (
                jsonify(
                    {"error": "Could not determine your team. Please contact support."}
                ),
                400,
            )

        print(f"🔥 User ID: {user_id}, Team ID: {team_id}")

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
    """Get all polls for the current user's team"""
    try:
        user = session["user"]
        user_id = user["id"]

        # Get user's team ID
        team_id = get_user_team_id(user)
        if not team_id:
            print(
                f"[DEBUG] Could not determine team ID for user: {user.get('email')} (user_id: {user_id})"
            )
            return (
                jsonify(
                    {"error": "Could not determine your team. Please contact support."}
                ),
                400,
            )

        print(f"[DEBUG] Getting polls for user: {user.get('email')}")
        print(f"[DEBUG] Team ID: {team_id} (integer foreign key)")

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
