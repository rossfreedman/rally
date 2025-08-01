import json
import os
from datetime import datetime

from flask import jsonify, render_template, request, session

from utils.auth import login_required
from utils.db import execute_query
from utils.logging import log_user_activity


def init_find_sub_routes(app):
    @app.route("/mobile/find-subs")
    @login_required
    def serve_mobile_find_subs():
        """Serve the mobile Find Sub page"""
        try:
            session_data = {"user": session["user"], "authenticated": True}
            log_user_activity(
                session["user"]["email"], "page_visit", page="mobile_find_subs"
            )
            return render_template("mobile/find_subs.html", session_data=session_data)
        except Exception as e:
            print(f"Error serving find subs page: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/player-contact")
    def get_player_contact():
        """Get player contact information for a specific player from CSV directory"""
        try:
            first_name = request.args.get("first")
            last_name = request.args.get("last")

            if not first_name or not last_name:
                return (
                    jsonify({"error": "First and last name parameters are required"}),
                    400,
                )

            # Load club directory data
            try:
                # Get user's league for dynamic path  
                # FIXED: Use league_string_id instead of league_id (which is now an integer)
                user_league_string_id = session.get("user", {}).get("league_string_id", "")

                # Use dynamic path based on league
                if user_league_string_id and not user_league_string_id.startswith("APTA"):
                    # For non-APTA leagues, use league-specific path
                    csv_path = os.path.join(
                        os.path.dirname(
                            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        ),
                        "data",
                        "leagues",
                        user_league_string_id,
                        "club_directories",
                        "directory_tennaqua.csv",
                    )
                else:
                    # For APTA leagues, use the main directory
                    csv_path = os.path.join(
                        os.path.dirname(
                            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        ),
                        "data",
                        "leagues",
                        "all",
                        "club_directories",
                        "directory_tennaqua.csv",
                    )
            except Exception as e:
                print(f"Error loading club directory data: {str(e)}")
                return jsonify({"error": str(e)}), 500

            print(f"Looking for CSV file at: {csv_path}")
            if not os.path.exists(csv_path):
                print(f"CSV file not found at: {csv_path}")
                return jsonify({"error": "Directory file not found"}), 404

            import csv

            with open(csv_path, "r") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    # Match by first and last name (case insensitive)
                    if (
                        row["First"].strip().lower() == first_name.lower()
                        and row["Last Name"].strip().lower() == last_name.lower()
                    ):

                        result = {
                            "first_name": row["First"].strip(),
                            "last_name": row["Last Name"].strip(),
                            "email": row["Email"].strip(),
                            "phone": row["Phone"].strip(),
                            "series": (
                                f"Series {row['Series'].strip()}"
                                if row["Series"].strip()
                                else "Unknown"
                            ),
                        }

                        return jsonify(result)

            # Player not found in CSV
            return (
                jsonify(
                    {"error": f"Player {first_name} {last_name} not found in directory"}
                ),
                404,
            )

        except Exception as e:
            print(f"Error getting player contact info: {str(e)}")
            return jsonify({"error": str(e)}), 500
