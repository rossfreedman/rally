from functools import wraps

from flask import jsonify, redirect, request, session, url_for


def login_required(f):
    """Decorator to check if user is logged in"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Not authenticated"}), 401
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return decorated_function
