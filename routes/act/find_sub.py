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

    # NOTE: /api/player-contact route removed - using the comprehensive version from api_routes.py instead
    # The API blueprint version handles both database associations and CSV fallback, making this duplicate unnecessary
