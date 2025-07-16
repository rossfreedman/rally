import logging
import time

from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.services.auth_service_refactored import (
    authenticate_user,
    get_clubs_list,
    register_user,
)
from app.services.association_discovery_service import AssociationDiscoveryService
from utils.logging import log_user_activity

# Create Blueprint
auth_bp = Blueprint("auth", __name__)
logger = logging.getLogger(__name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Serve the login page"""
    if request.method == "GET":
        return render_template("login.html", default_tab="login")
    return jsonify({"error": "Method not allowed"}), 405


@auth_bp.route("/register", methods=["GET"])
def register():
    """Serve the registration page (uses login template with register tab active)"""
    return render_template("login.html", default_tab="register")


@auth_bp.route("/forgot-password", methods=["GET"])
def forgot_password():
    """Serve the forgot password page"""
    return render_template("forgot_password.html")


@auth_bp.route("/change-password", methods=["GET"])
def change_password():
    """Serve the change password page for users with temporary passwords"""
    # Allow access if user has temporary password (middleware will handle redirects)
    # This prevents circular redirects between login and change-password
    if "user" not in session:
        return redirect("/login")
    
    # Check if user actually has a temporary password
    user_data = session.get("user", {})
    has_temporary_password = user_data.get("has_temporary_password", False)
    
    if not has_temporary_password:
        # User doesn't have temporary password, redirect to welcome
        return redirect("/welcome")
    
    return render_template("change_password.html")


@auth_bp.route("/api/register", methods=["POST"])
def handle_register():
    """Handle user registration with mandatory player association"""
    try:
        # ✅ FIX: Better error handling for malformed JSON
        try:
            data = request.get_json()
        except Exception as json_error:
            logger.warning(f"Invalid JSON in registration request: {json_error}")
            return jsonify({"error": "Invalid JSON format"}), 400
            
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # ✅ FIX: Better field extraction with validation
        email = (data.get("email", "") if data else "").strip().lower()
        password = (data.get("password", "") if data else "").strip()
        first_name = (data.get("firstName", "") if data else "").strip()
        last_name = (data.get("lastName", "") if data else "").strip()
        phone_number = (data.get("phoneNumber", "") if data else "").strip()
        league_id = (data.get("league", "") if data else "").strip()
        club_name = (data.get("club", "") if data else "").strip()
        series_name = (data.get("series", "") if data else "").strip()
        ad_deuce_preference = (data.get("adDeuce", "") if data else "").strip()
        dominant_hand = (data.get("dominantHand", "") if data else "").strip()

        # ✅ FIX: Improved validation with specific error messages
        missing_fields = []
        if not email:
            missing_fields.append("email")
        if not password:
            missing_fields.append("password")
        if not first_name:
            missing_fields.append("firstName")
        if not last_name:
            missing_fields.append("lastName")
        if not phone_number:
            missing_fields.append("phoneNumber")
        if not league_id:
            missing_fields.append("league")
        if not club_name:
            missing_fields.append("club")
        if not series_name:
            missing_fields.append("series")

        if missing_fields:
            return (
                jsonify({"error": f'Missing required fields: {", ".join(missing_fields)}'}),
                400,
            )

        # Use service to register user with mandatory player association
        result = register_user(
            email, password, first_name, last_name, league_id, club_name, series_name, 
            ad_deuce_preference=ad_deuce_preference, dominant_hand=dominant_hand, phone_number=phone_number
        )

        if not result["success"]:
            if "already exists" in result["error"]:
                return jsonify({"error": result["error"]}), 409
            else:
                # All registration failures now use the specific error message
                return jsonify({"error": result["error"]}), 400

        # Set session data directly from register_user result
        session["user"] = result["user"]
        session.permanent = True

        logger.info(f"Registration: Session created for user {email} with player_id: {result['user'].get('tenniscores_player_id', 'None')}")

        # 🔍 ENHANCED: Run association discovery after successful registration with retry mechanism
        # This finds additional associations for multi-league users
        try:
            user_id = result["user"]["id"]
            logger.info(f"🔍 Post-registration discovery: Looking for additional associations for {email}")
            
            # Enhanced retry mechanism with 3 attempts
            discovery_success = False
            discovery_attempts = 0
            max_attempts = 3
            
            while not discovery_success and discovery_attempts < max_attempts:
                discovery_attempts += 1
                try:
                    # Small delay to ensure primary registration is fully committed
                    time.sleep(0.1)
                    
                    logger.info(f"🔍 Registration discovery attempt {discovery_attempts}/{max_attempts} for {email}")
                    
                    discovery_result = AssociationDiscoveryService.discover_missing_associations(user_id, email)
                    
                    if discovery_result.get("success"):
                        discovery_success = True
                        associations_created = discovery_result.get("associations_created", 0)
                        
                        if associations_created > 0:
                            logger.info(f"🎯 Registration discovery SUCCESS: Found {associations_created} additional associations for {email}")
                            
                            # Update session with any new associations found
                            try:
                                from app.services.session_service import get_session_data_for_user
                                updated_session_data = get_session_data_for_user(email)
                                if updated_session_data:
                                    session["user"] = updated_session_data
                                    logger.info(f"Registration: Updated session with additional associations")
                            except Exception as session_update_error:
                                logger.warning(f"Failed to update session with additional associations: {session_update_error}")
                                # Continue anyway - user will see new associations on next login
                        else:
                            logger.info(f"🔍 Registration discovery SUCCESS: No additional associations found for {email}")
                    else:
                        logger.info(f"🔍 Registration discovery FAILED (attempt {discovery_attempts}): {discovery_result.get('error', 'Unknown error')}")
                        # Retry with backoff
                        if discovery_attempts < max_attempts:
                            logger.info(f"🔄 Retrying association discovery in 0.5 seconds...")
                            time.sleep(0.5)
                        
                except Exception as discovery_error:
                    # Enhanced error logging with full tracebacks
                    logger.error(f"❌ Registration discovery ERROR (attempt {discovery_attempts}): {discovery_error}")
                    import traceback
                    logger.error(f"❌ Registration discovery TRACEBACK: {traceback.format_exc()}")
                    
                    if discovery_attempts < max_attempts:
                        logger.info(f"🔄 Retrying association discovery after exception...")
                        time.sleep(0.5)
            
            # If all attempts failed, log the fallback mechanism
            if not discovery_success:
                logger.warning(f"⚠️  Registration discovery FAILED after {max_attempts} attempts for {email}")
                logger.info(f"🔄 Association Discovery will run automatically on next login for {email}")
                
        except Exception as discovery_error:
            logger.warning(f"Post-registration discovery error for {email}: {discovery_error}")
            # This is not critical since main player association already succeeded

        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Registration successful",
                    "redirect": "/welcome",
                }
            ),
            201,
        )

    except Exception as e:
        logger.error(f"Registration API error: {str(e)}")
        import traceback
        logger.error(f"Registration API traceback: {traceback.format_exc()}")
        return jsonify({"error": "Registration was not successful. Rally was unable to link your user account to a player ID. Please contact support for assistance."}), 500


@auth_bp.route("/api/login", methods=["POST"])
def handle_login():
    """Handle user login"""
    try:
        logger.info("Login attempt started")

        # Check if we can get JSON data
        try:
            data = request.get_json()
            logger.info("Successfully parsed JSON data")
        except Exception as json_error:
            logger.error(f"Failed to parse JSON: {json_error}")
            return jsonify({"error": "Invalid JSON data"}), 400

        if not data:
            logger.error("No JSON data received")
            return jsonify({"error": "No data received"}), 400

        email = data.get("email", "").lower()
        password = data.get("password", "")

        logger.info(f"Login attempt for email: {email}")

        if not email or not password:
            logger.warning("Missing email or password")
            return jsonify({"error": "Missing email or password"}), 400

        # Test database connection first
        try:
            from database_config import test_db_connection

            db_success, db_error = test_db_connection()
            if not db_success:
                logger.error(f"Database connection failed: {db_error}")
                return jsonify({"error": "Database connection failed"}), 500
            logger.info("Database connection verified")
        except Exception as db_test_error:
            logger.error(f"Database test error: {db_test_error}")
            return jsonify({"error": "Database test failed"}), 500

        # Use service to authenticate user
        try:
            result = authenticate_user(email, password)
            logger.info(f"Authentication result: success={result['success']}")
        except Exception as auth_error:
            logger.error(f"Authentication service error: {auth_error}")
            return jsonify({"error": "Authentication service failed"}), 500

        if not result["success"]:
            logger.warning(f"Authentication failed: {result['error']}")
            return jsonify({"error": result["error"]}), 401

        # Set session data directly from authenticate_user result (don't call create_session_data again)
        try:
            session["user"] = result["user"]  # Use the session data directly from authenticate_user
            session.permanent = True
            logger.info(f"Session created for user: {email} with player_id: {result['user'].get('tenniscores_player_id', 'None')}")
        except Exception as session_error:
            logger.error(f"Session creation error: {session_error}")
            return jsonify({"error": "Session creation failed"}), 500

        # 🔍 ENHANCED: Run association discovery on login to find missing league connections
        try:
            user_id = result["user"]["id"]
            logger.info(f"🔍 Login discovery: Running association discovery for {email}")
            
            discovery_result = AssociationDiscoveryService.discover_missing_associations(user_id, email)
            
            if discovery_result.get("success"):
                associations_created = discovery_result.get("associations_created", 0)
                
                if associations_created > 0:
                    logger.info(f"🎯 Login discovery SUCCESS: Created {associations_created} new associations for {email}")
                    
                    # Log the new associations
                    for assoc in discovery_result.get('new_associations', []):
                        logger.info(f"   • {assoc['tenniscores_player_id']} - {assoc['league_name']} ({assoc['club_name']}, {assoc['series_name']})")
                else:
                    logger.info(f"🔍 Login discovery SUCCESS: No additional associations found for {email}")
            else:
                logger.warning(f"🔍 Login discovery FAILED: {discovery_result.get('error', 'Unknown error')}")
            
        except Exception as discovery_error:
            logger.warning(f"Association discovery failed during login for {email}: {discovery_error}")
            import traceback
            logger.error(f"Login discovery TRACEBACK: {traceback.format_exc()}")
            # Don't fail login if discovery fails - it's an enhancement, not critical

        # Get user data for response
        user_data = result["user"]
        has_temporary_password = result.get("has_temporary_password", False)
        
        # Extract club and series for response
        club = user_data.get("club", "")
        series = user_data.get("series", "")

        # Determine redirect URL based on temporary password status
        if has_temporary_password:
            redirect_url = "/change-password"
            logger.info(f"User {user_data['email']} has temporary password, redirecting to change password page")
        else:
            # Check for redirect_after_login in session
            redirect_url = session.pop("redirect_after_login", "/welcome")

        return jsonify(
            {
                "status": "success",
                "message": result["message"],
                "redirect": redirect_url,
                "has_temporary_password": has_temporary_password,
                "user": {
                    "email": user_data["email"],
                    "first_name": user_data["first_name"],
                    "last_name": user_data["last_name"],
                    "club": club,
                    "series": series,
                    "tenniscores_player_id": user_data.get("tenniscores_player_id", ""),
                },
            }
        )

    except Exception as e:
        logger.error(f"Login endpoint error: {str(e)}")
        logger.error(f"Request path: {request.path}")
        logger.error(f"Request method: {request.method}")
        logger.error(f"Request headers: {dict(request.headers)}")
        return jsonify({"error": "Login failed - server error"}), 500


@auth_bp.route("/api/forgot-password", methods=["POST"])
def handle_forgot_password():
    """Handle password reset request via SMS"""
    try:
        logger.info("Password reset attempt started")

        # Parse request data
        try:
            data = request.get_json()
            logger.info("Successfully parsed JSON data for password reset")
        except Exception as json_error:
            logger.error(f"Failed to parse JSON in password reset: {json_error}")
            return jsonify({"error": "Invalid JSON data"}), 400

        if not data:
            logger.error("No JSON data received for password reset")
            return jsonify({"error": "No data received"}), 400

        phone = data.get("phone", "").strip()
        email = data.get("email", "").strip().lower()
        
        if not phone:
            logger.warning("Missing phone in password reset request")
            return jsonify({"error": "Phone number is required"}), 400

        logger.info(f"Password reset attempt for phone: {phone} (email: {email})")

        # Import password reset service
        from app.services.password_reset_service import send_password_via_sms
        
        # Attempt to send password via SMS
        result = send_password_via_sms(phone, email)
        
        if result["success"]:
            logger.info(f"Password reset successful for {phone}")
            return jsonify({
                "success": True,
                "message": result["message"]
            })
        else:
            logger.warning(f"Password reset failed for {phone}: {result['error']}")
            return jsonify({
                "success": False,
                "error": result["error"]
            }), 400

    except Exception as e:
        logger.error(f"Password reset endpoint error: {str(e)}")
        import traceback
        logger.error(f"Password reset traceback: {traceback.format_exc()}")
        return jsonify({"error": "Password reset failed - server error"}), 500


@auth_bp.route("/api/change-password", methods=["POST"])
def handle_change_password():
    """Handle password change for users with temporary passwords"""
    try:
        if "user" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        # Check if user has temporary password
        user_data = session.get("user", {})
        has_temporary_password = user_data.get("has_temporary_password", False)
        
        if not has_temporary_password:
            return jsonify({"error": "No temporary password detected"}), 400
        
        # Parse request data
        try:
            data = request.get_json()
        except Exception as json_error:
            logger.error(f"Failed to parse JSON in change password: {json_error}")
            return jsonify({"error": "Invalid JSON data"}), 400

        if not data:
            return jsonify({"error": "No data received"}), 400

        new_password = data.get("newPassword", "").strip()
        confirm_password = data.get("confirmPassword", "").strip()
        
        if not new_password:
            return jsonify({"error": "New password is required"}), 400
        
        if new_password != confirm_password:
            return jsonify({"error": "Passwords do not match"}), 400
        
        if len(new_password) == 0:
            return jsonify({"error": "Password cannot be empty"}), 400
        
        # Update user's password in database
        from database_utils import execute_update
        from werkzeug.security import generate_password_hash
        
        user_id = user_data.get("id")
        password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
        
        # Update password and clear temporary password flag
        update_query = """
            UPDATE users 
            SET password_hash = %s, 
                has_temporary_password = FALSE,
                temporary_password_set_at = NULL
            WHERE id = %s
        """
        
        rows_updated = execute_update(update_query, [password_hash, user_id])
        
        if rows_updated == 0:
            return jsonify({"error": "Failed to update password"}), 500
        
        # Update session to remove temporary password flag
        session["user"]["has_temporary_password"] = False
        
        # Log the password change
        log_user_activity(
            user_data["email"], 
            "password_changed", 
            details={
                "from_temporary": True,
                "user_id": user_id
            }
        )
        
        logger.info(f"Password changed successfully for user {user_data['email']}")
        
        return jsonify({
            "success": True,
            "message": "Password changed successfully",
            "redirect": "/welcome"
        })
        
    except Exception as e:
        logger.error(f"Change password endpoint error: {str(e)}")
        import traceback
        logger.error(f"Change password traceback: {traceback.format_exc()}")
        return jsonify({"error": "Password change failed - server error"}), 500


@auth_bp.route("/api/logout", methods=["POST"])
def handle_logout():
    """Handle API logout"""
    try:
        session.clear()
        return jsonify({"message": "Logout successful"})
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return jsonify({"error": "Logout failed"}), 500


@auth_bp.route("/logout")
def logout_page():
    """Handle page logout with redirect"""
    session.clear()
    return redirect(url_for("auth.login"))


@auth_bp.route("/api/check-auth")
def check_auth():
    """Check if the user is authenticated"""
    try:
        if "user" in session:
            return jsonify({"authenticated": True, "user": session["user"]})
        return jsonify({"authenticated": False})
    except Exception as e:
        logger.error(f"Error checking authentication: {str(e)}")
        return jsonify({"error": str(e), "authenticated": False}), 500


@auth_bp.route("/static/js/logout.js")
def serve_logout_js():
    """Serve the logout JavaScript file"""
    try:
        logout_js_content = """
// logout.js - Handle logout functionality
console.log("Logout.js loaded");

window.logout = function() {
    console.log("Logout function called");
    fetch('/api/logout', {
        method: 'POST',
        credentials: 'include'
    })
    .then(response => response.json())
    .then(data => {
        console.log("Logout response:", data);
        // Redirect to login page
        window.location.href = '/login';
    })
    .catch(error => {
        console.error('Logout error:', error);
        // Still redirect to login page even if logout fails
        window.location.href = '/login';
    });
};
"""
        response = jsonify(logout_js_content)
        response.headers["Content-Type"] = "application/javascript"
        return response
    except Exception as e:
        logger.error(f"Error serving logout.js: {str(e)}")
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/api/get-clubs")
def get_clubs():
    """Get list of all clubs - public endpoint for registration"""
    try:
        clubs_list = get_clubs_list()
        return jsonify({"clubs": clubs_list})  # For login page compatibility
    except Exception as e:
        logger.error(f"Error getting clubs: {str(e)}")
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/terms")
def terms_of_use():
    """Serve the Terms of Use page"""
    return render_template("legal/terms_of_use.html")


@auth_bp.route("/privacy")
def privacy_policy():
    """Serve the Privacy Policy page"""
    return render_template("legal/privacy_policy.html")
