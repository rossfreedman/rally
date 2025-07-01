import json
import logging

from flask import jsonify, request, session

from database_utils import execute_query_one, execute_update

logger = logging.getLogger(__name__)


def login_required(f):
    """Decorator to check if user is logged in"""
    from functools import wraps

    from flask import jsonify, redirect, request, session, url_for

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Not authenticated"}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


def init_routes(app):
    # Route moved to api_routes.py blueprint

    # Route moved to api_routes.py blueprint

    @app.route("/api/set-series", methods=["POST"])
    @login_required
    def set_series():
        try:
            data = request.get_json()
            series = data.get("series")

            if not series:
                return jsonify({"error": "Series not provided"}), 400

            user_email = session["user"]["email"]

            # Get series_id from name
            series_result = execute_query_one(
                "SELECT id FROM series WHERE name = %(series)s", {"series": series}
            )
            if not series_result:
                return jsonify({"error": "Series not found"}), 404

            series_id = series_result["id"]

            # Update user series
            success = execute_update(
                """
                UPDATE users 
                SET series_id = %(series_id)s
                WHERE email = %(email)s
            """,
                {"series_id": series_id, "email": user_email},
            )

            if not success:
                return jsonify({"error": "Failed to update series"}), 500

            # Update session
            session["user"]["series"] = series

            return jsonify({"message": "Series updated successfully"})

        except Exception as e:
            logger.error(f"Error updating series: {str(e)}")
            return jsonify({"error": "Failed to update series"}), 500

    @app.route("/api/get-series")
    def get_series():
        try:
            import re

            from database_utils import execute_query

            # Get all available series (unsorted)
            all_series_records = execute_query("SELECT name FROM series")

            # Extract series names and sort them numerically
            def get_series_sort_key(series_name):
                """Extract and sort series names properly by prefix, number, and suffix"""
                # Handle series with numeric values: "Chicago 1", "Series 2", "Division 3", etc.
                match = re.match(r'^(?:(Chicago|Series|Division)\s+)?(\d+)([a-zA-Z\s]*)$', series_name)
                if match:
                    prefix = match.group(1) or ''
                    number = int(match.group(2))
                    suffix = match.group(3).strip() if match.group(3) else ''
                    
                    # Sort by: prefix priority, then number, then suffix
                    prefix_priority = {'Chicago': 0, 'Series': 1, 'Division': 2}.get(prefix, 3)
                    return (0, prefix_priority, number, suffix)  # Numeric series first
                
                # Handle letter-only series (Series A, Series B, etc.)
                match = re.match(r'^(?:(Chicago|Series|Division)\s+)?([A-Z]+)$', series_name)
                if match:
                    prefix = match.group(1) or ''
                    letter = match.group(2)
                    prefix_priority = {'Chicago': 0, 'Series': 1, 'Division': 2}.get(prefix, 3)
                    return (1, prefix_priority, 0, letter)  # Letters after numbers
                
                # Everything else goes last (sorted alphabetically)
                return (2, 0, 0, series_name)

            # Sort series by the extracted number
            all_series_names = [record["name"] for record in all_series_records]
            all_series_sorted = sorted(all_series_names, key=get_series_sort_key)
            
            # Convert series names for APTA league UI display
            user_league_id = session.get("user", {}).get("league_id", "")
            if user_league_id and user_league_id.startswith("APTA"):
                def convert_chicago_to_series_for_ui(series_name):
                    """Convert "Chicago X" format to "Series X" format for APTA league UI display"""
                    import re
                    match = re.match(r'^Chicago\s+(\d+)([a-zA-Z\s]*)$', series_name)
                    if match:
                        number = match.group(1)
                        suffix = match.group(2).strip() if match.group(2) else ''
                        if suffix:
                            return f"Series {number} {suffix}"
                        else:
                            return f"Series {number}"
                    return series_name
                
                all_series_sorted = [convert_chicago_to_series_for_ui(name) for name in all_series_sorted]

            # Get user's current series (also convert if APTA)
            current_series = None
            if "user" in session and "series" in session["user"]:
                current_series = session["user"]["series"]
                if user_league_id and user_league_id.startswith("APTA"):
                    current_series = convert_chicago_to_series_for_ui(current_series)

            return jsonify({"series": current_series, "all_series": all_series_sorted})

        except Exception as e:
            logger.error(f"Error getting series: {str(e)}")
            return jsonify({"error": "Failed to get series"}), 500

    return app
