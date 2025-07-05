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

            # FIXED: Get series with both ID and name for efficient lookups
            all_series_records = execute_query("SELECT id, name FROM series ORDER BY name")

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
            all_series_sorted = sorted(all_series_records, key=lambda x: get_series_sort_key(x["name"]))
            
            # FIXED: Create series objects with both id and name
            all_series_objects = [{"id": record["id"], "name": record["name"]} for record in all_series_sorted]
            
            # For backward compatibility, also provide the old format (just names)
            all_series_names = [record["name"] for record in all_series_sorted]

            # Get user's current series
            current_series = None
            if "user" in session and "series" in session["user"]:
                current_series = session["user"]["series"]

            # ENHANCED: Return both the new format (with IDs) and old format (names only) for compatibility
            return jsonify({
                "series": current_series,  # Current user's series name (backward compatibility)
                "all_series": all_series_names,  # All series names (backward compatibility)
                "all_series_objects": all_series_objects,  # NEW: All series with IDs
                "current_series_object": None  # Will be populated if we can find the current series with ID
            })

        except Exception as e:
            print(f"Error getting series: {str(e)}")
            return jsonify({"error": str(e)}), 500

    return app
