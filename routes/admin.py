from functools import wraps

from flask import Blueprint, jsonify, request, session

from utils.auth import login_required
from utils.db import execute_query, execute_query_one, execute_update
from utils.logging import log_user_activity

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/users")
@login_required
def get_users():
    """Get all users with their information, sorted by most recent activity"""
    try:
        users = execute_query(
            """
            SELECT DISTINCT ON (u.id) 
                u.id, u.email, u.first_name, u.last_name, 
                u.last_login, c.name as club_name, s.name as series_name,
                c.id as club_id, s.id as series_id,
                -- Get the most recent activity timestamp from either system
                GREATEST(
                    COALESCE(ual.latest_activity, '1970-01-01'::timestamp),
                    COALESCE(al.latest_activity, '1970-01-01'::timestamp),
                    COALESCE(u.last_login, '1970-01-01'::timestamp),
                    COALESCE(u.created_at, '1970-01-01'::timestamp)
                ) as most_recent_activity
            FROM users u
            LEFT JOIN (
                -- Get latest timestamp from legacy system
                SELECT 
                    user_email,
                    MAX(timestamp) as latest_activity
                FROM user_activity_logs 
                GROUP BY user_email
            ) ual ON u.email = ual.user_email
            LEFT JOIN (
                -- Get latest timestamp from comprehensive system
                SELECT 
                    user_id,
                    MAX(timestamp) as latest_activity
                FROM activity_log 
                WHERE user_id IS NOT NULL
                GROUP BY user_id
            ) al ON u.id = al.user_id
            LEFT JOIN clubs c ON u.club_id = c.id
            LEFT JOIN series s ON u.series_id = s.id
            ORDER BY u.id
        """
        )
        
        # Sort the results by most recent activity (newest first)
        users.sort(key=lambda x: x['most_recent_activity'], reverse=True)
        
        return jsonify(users)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/user-activity/<email>")
@login_required
def get_user_activity(email):
    """Get activity logs for a specific user"""
    try:
        print(f"\n=== Getting Activity for User: {email} ===")

        # Get user details first
        print("Fetching user details...")
        user = execute_query_one(
            """
            SELECT first_name, last_name, email, last_login
            FROM users
            WHERE email = %(email)s
            """,
            {"email": email},
        )

        if not user:
            print(f"User not found: {email}")
            return jsonify({"error": "User not found"}), 404

        print(f"Found user: {user['first_name']} {user['last_name']}")

        # Get activity logs with explicit timestamp ordering
        print("Fetching activity logs...")
        logs = execute_query(
            """
            SELECT id, activity_type, page, action, details, ip_address, 
                   timezone('America/Chicago', timestamp) as central_time
            FROM user_activity_logs
            WHERE user_email = %(email)s
            ORDER BY timestamp DESC, id DESC
            LIMIT 1000
            """,
            {"email": email},
        )

        print("\nMost recent activities:")
        for idx, log in enumerate(
            logs[:5]
        ):  # Print details of 5 most recent activities
            print(
                f"ID: {log['id']}, Type: {log['activity_type']}, Time: {log['central_time']}"
            )

        formatted_logs = [
            {
                "id": log["id"],
                "activity_type": log["activity_type"],
                "page": log["page"],
                "action": log["action"],
                "details": log["details"],
                "ip_address": log["ip_address"],
                "timestamp": log[
                    "central_time"
                ].isoformat(),  # Format timestamp as ISO string
            }
            for log in logs
        ]

        print(f"\nFound {len(formatted_logs)} activity logs")
        if formatted_logs:
            print(f"Most recent log ID: {formatted_logs[0]['id']}")
            print(f"Most recent timestamp: {formatted_logs[0]['timestamp']}")

        response_data = {
            "user": {
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "email": user["email"],
                "last_login": user["last_login"],
            },
            "activities": formatted_logs,
        }

        print("Returning response data")
        print("=== End Activity Request ===\n")

        # Create response with cache-busting headers
        response = jsonify(response_data)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    except Exception as e:
        print(f"Error getting user activity: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/update-user", methods=["POST"])
@login_required
def update_user():
    """Update user information"""
    try:
        data = request.json
        result = execute_update(
            """
            UPDATE users 
            SET first_name = %(first_name)s,
                last_name = %(last_name)s,
                club_id = %(club_id)s,
                series_id = %(series_id)s
            WHERE id = %(id)s
            RETURNING id
        """,
            data,
        )

        if result:
            log_user_activity(
                session["user"]["email"],
                "admin_action",
                action="update_user",
                details=f"Updated user {data['email']}",
            )
            return jsonify({"status": "success"})
        return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/clubs")
@login_required
def get_clubs():
    """Get all clubs"""
    try:
        clubs = execute_query("SELECT * FROM clubs ORDER BY name")
        return jsonify(clubs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/save-club", methods=["POST"])
@login_required
def save_club():
    """Add or update a club"""
    try:
        data = request.json
        if data.get("id"):
            result = execute_update(
                """
                UPDATE clubs 
                SET name = %(name)s
                WHERE id = %(id)s
                RETURNING id
            """,
                data,
            )
        else:
            result = execute_update(
                """
                INSERT INTO clubs (name)
                VALUES (%(name)s)
                RETURNING id
            """,
                data,
            )

        if result:
            log_user_activity(
                session["user"]["email"],
                "admin_action",
                action="save_club",
                details=f"{'Updated' if data.get('id') else 'Added'} club {data['name']}",
            )
            return jsonify({"status": "success", "id": result[0]["id"]})
        return jsonify({"error": "Operation failed"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/delete-club/<int:club_id>", methods=["DELETE"])
@login_required
def delete_club(club_id):
    """Delete a club"""
    try:
        # Check if club is being used by any users
        users = execute_query(
            "SELECT COUNT(*) as count FROM users WHERE club_id = %(club_id)s",
            {"club_id": club_id},
        )
        if users[0]["count"] > 0:
            return jsonify({"error": "Cannot delete club that has users assigned"}), 400

        result = execute_update(
            "DELETE FROM clubs WHERE id = %(club_id)s RETURNING id",
            {"club_id": club_id},
        )

        if result:
            log_user_activity(
                session["user"]["email"],
                "admin_action",
                action="delete_club",
                details=f"Deleted club ID {club_id}",
            )
            return jsonify({"status": "success"})
        return jsonify({"error": "Club not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/series")
@login_required
def get_series():
    """Get all series"""
    try:
        series = execute_query("SELECT * FROM series ORDER BY name")
        return jsonify(series)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/save-series", methods=["POST"])
@login_required
def save_series():
    """Add or update a series"""
    try:
        data = request.json
        if data.get("id"):
            result = execute_update(
                """
                UPDATE series 
                SET name = %(name)s
                WHERE id = %(id)s
                RETURNING id
            """,
                data,
            )
        else:
            result = execute_update(
                """
                INSERT INTO series (name)
                VALUES (%(name)s)
                RETURNING id
            """,
                data,
            )

        if result:
            log_user_activity(
                session["user"]["email"],
                "admin_action",
                action="save_series",
                details=f"{'Updated' if data.get('id') else 'Added'} series {data['name']}",
            )
            return jsonify({"status": "success", "id": result[0]["id"]})
        return jsonify({"error": "Operation failed"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/delete-series/<int:series_id>", methods=["DELETE"])
@login_required
def delete_series(series_id):
    """Delete a series"""
    try:
        # Check if series is being used by any users
        users = execute_query(
            "SELECT COUNT(*) as count FROM users WHERE series_id = %(series_id)s",
            {"series_id": series_id},
        )
        if users[0]["count"] > 0:
            return (
                jsonify({"error": "Cannot delete series that has users assigned"}),
                400,
            )

        result = execute_update(
            "DELETE FROM series WHERE id = %(series_id)s RETURNING id",
            {"series_id": series_id},
        )

        if result:
            log_user_activity(
                session["user"]["email"],
                "admin_action",
                action="delete_series",
                details=f"Deleted series ID {series_id}",
            )
            return jsonify({"status": "success"})
        return jsonify({"error": "Series not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
