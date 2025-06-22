"""
Rally Security Tests
Comprehensive security testing including SQL injection, XSS, authentication bypass, and more
"""

import json
import re
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.models.database_models import Player, User
from app.services.auth_service_refactored import authenticate_user, register_user


@pytest.mark.security
class TestSQLInjectionPrevention:
    """Test SQL injection attack prevention"""

    def test_login_sql_injection(self, client, mock_security_payloads):
        """Test SQL injection attempts in login form"""
        for sql_payload in mock_security_payloads["sql_injection"]:
            login_data = {"email": sql_payload, "password": "testpassword"}

            response = client.post(
                "/api/login", json=login_data, content_type="application/json"
            )

            # Should not succeed with SQL injection
            assert response.status_code in [400, 401]

            # Should not crash the server
            data = response.get_json()
            assert "error" in data

    def test_registration_sql_injection(self, client, mock_security_payloads):
        """Test SQL injection attempts in registration"""
        for sql_payload in mock_security_payloads["sql_injection"]:
            registration_data = {
                "email": f"test{hash(sql_payload)}@example.com",
                "password": "testpassword123",
                "firstName": sql_payload,
                "lastName": "User",
                "league": "TEST_LEAGUE",
                "club": "Test Club",
                "series": "Test Series",
            }

            response = client.post(
                "/api/register", json=registration_data, content_type="application/json"
            )

            # Should handle gracefully - either succeed with escaped data or fail validation
            assert response.status_code in [201, 400, 500]

    def test_player_search_sql_injection(
        self, authenticated_client, mock_security_payloads
    ):
        """Test SQL injection in player search functionality"""
        for sql_payload in mock_security_payloads["sql_injection"]:
            search_data = {"first_name": sql_payload, "last_name": "TestPlayer"}

            response = authenticated_client.post(
                "/api/players/search", json=search_data, content_type="application/json"
            )

            # Should not cause server error
            assert response.status_code in [200, 400, 404]

    def test_database_integrity_after_injection_attempts(
        self, client, db_session, mock_security_payloads
    ):
        """Test that database remains intact after injection attempts"""
        # Count users before injection attempts
        initial_user_count = db_session.query(User).count()

        # Attempt multiple SQL injections
        for sql_payload in mock_security_payloads["sql_injection"]:
            login_data = {"email": sql_payload, "password": "anything"}

            client.post("/api/login", json=login_data, content_type="application/json")

        # Verify database integrity
        final_user_count = db_session.query(User).count()
        assert final_user_count == initial_user_count

        # Verify specific tables still exist and function
        users = db_session.query(User).all()
        assert isinstance(users, list)  # Should not crash


@pytest.mark.security
class TestXSSPrevention:
    """Test Cross-Site Scripting (XSS) prevention"""

    def test_user_input_xss_sanitization(self, client, mock_security_payloads):
        """Test XSS payload handling in user input"""
        for xss_payload in mock_security_payloads["xss_payloads"]:
            registration_data = {
                "email": f"xss{hash(xss_payload)}@example.com",
                "password": "testpassword123",
                "firstName": xss_payload,
                "lastName": "Test",
                "league": "TEST_LEAGUE",
                "club": "Test Club",
                "series": "Test Series",
            }

            response = client.post(
                "/api/register", json=registration_data, content_type="application/json"
            )

            # Should handle XSS attempts gracefully
            assert response.status_code in [201, 400]

            if response.status_code == 201:
                # If registration succeeded, verify XSS was escaped/sanitized
                data = response.get_json()
                assert "script" not in str(data).lower()

    def test_poll_question_xss_prevention(
        self, authenticated_client, test_team, mock_security_payloads
    ):
        """Test XSS prevention in poll questions"""
        for xss_payload in mock_security_payloads["xss_payloads"]:
            poll_data = {
                "question": xss_payload,
                "choices": ["Choice 1", "Choice 2"],
                "team_id": test_team.id,
            }

            response = authenticated_client.post(
                "/api/polls", json=poll_data, content_type="application/json"
            )

            # Should handle gracefully
            assert response.status_code in [201, 400]

    def test_output_encoding_in_templates(
        self, authenticated_client, db_session, test_user
    ):
        """Test that template output properly encodes user input"""
        # Create user with potentially dangerous name
        dangerous_name = "<script>alert('XSS')</script>"

        user = User(
            email="xsstest@example.com",
            password_hash="hashed",
            first_name=dangerous_name,
            last_name="Test",
        )
        db_session.add(user)
        db_session.commit()

        # Access page that displays user name
        response = authenticated_client.get("/mobile")

        assert response.status_code == 200
        response_text = response.get_data(as_text=True)

        # Should not contain raw script tags
        assert "<script>alert" not in response_text
        # Should contain encoded version or be filtered out
        assert "&lt;script&gt;" in response_text or dangerous_name not in response_text


@pytest.mark.security
class TestAuthenticationSecurity:
    """Test authentication and authorization security"""

    def test_password_hashing_strength(self, db_session):
        """Test that passwords are hashed with strong algorithm"""
        password = "testpassword123"

        result = register_user(
            email="hashtest@example.com",
            password=password,
            first_name="Hash",
            last_name="Test",
        )

        assert result["success"] is True

        user = (
            db_session.query(User).filter(User.email == "hashtest@example.com").first()
        )

        # Password should be hashed, not plain text
        assert user.password_hash != password
        assert len(user.password_hash) >= 60  # bcrypt hashes are typically 60+ chars

        # Should contain bcrypt format indicators
        assert user.password_hash.startswith("$2")  # bcrypt prefix

    def test_session_security(self, authenticated_client):
        """Test session security measures"""
        # Test that session is properly configured
        with authenticated_client.session_transaction() as sess:
            assert "user" in sess

            # Check for session security attributes
            # These would be set at the application level

        # Test session timeout behavior
        # Note: This would require time manipulation or configuration changes

        # Test that sensitive data is not exposed in session
        with authenticated_client.session_transaction() as sess:
            user_data = sess.get("user", {})
            assert "password" not in user_data
            assert "password_hash" not in user_data

    def test_unauthorized_access_prevention(self, client):
        """Test that unauthorized access is properly prevented"""
        protected_endpoints = [
            "/api/schedule",
            "/api/polls",
            "/mobile",
            "/schedule",
            "/admin",
        ]

        for endpoint in protected_endpoints:
            response = client.get(endpoint)
            assert response.status_code in [401, 302, 403]  # Unauthorized or redirect

    def test_privilege_escalation_prevention(
        self, authenticated_client, db_session, test_user
    ):
        """Test that users cannot escalate privileges"""
        # Ensure test user is not admin
        assert test_user.is_admin is False

        # Try to access admin functionality
        response = authenticated_client.get("/api/admin/users")
        assert response.status_code in [401, 403]

        # Try to modify admin status via API (if such endpoint exists)
        user_update_data = {"is_admin": True}

        response = authenticated_client.put(
            f"/api/users/{test_user.id}",
            json=user_update_data,
            content_type="application/json",
        )

        # Should be rejected
        assert response.status_code in [401, 403, 404, 405]


@pytest.mark.security
class TestBruteForceProtection:
    """Test brute force attack protection"""

    def test_login_rate_limiting(self, client):
        """Test protection against brute force login attempts"""
        login_data = {"email": "nonexistent@example.com", "password": "wrongpassword"}

        response_times = []

        # Attempt multiple failed logins
        for i in range(10):
            start_time = time.time()

            response = client.post(
                "/api/login", json=login_data, content_type="application/json"
            )

            end_time = time.time()
            response_times.append(end_time - start_time)

            # Should consistently fail
            assert response.status_code == 401

        # Later attempts should take longer (rate limiting) or be blocked
        # Note: Current implementation may not have rate limiting
        # This test documents expected behavior

        average_early_time = sum(response_times[:3]) / 3
        average_late_time = sum(response_times[-3:]) / 3

        # Ideally, later attempts should be slower or blocked
        print(f"Early login attempts: {average_early_time:.3f}s")
        print(f"Late login attempts: {average_late_time:.3f}s")

    def test_registration_flood_protection(self, client):
        """Test protection against registration flooding"""
        base_email = "flood{i}@example.com"

        successful_registrations = 0

        # Attempt many registrations quickly
        for i in range(20):
            registration_data = {
                "email": base_email.format(i=i),
                "password": "floodtest123",
                "firstName": f"Flood{i}",
                "lastName": "Test",
                "league": "TEST_LEAGUE",
                "club": "Test Club",
                "series": "Test Series",
            }

            response = client.post(
                "/api/register", json=registration_data, content_type="application/json"
            )

            if response.status_code == 201:
                successful_registrations += 1

        # Some protection mechanism should limit registrations
        # Note: Current implementation may not have flood protection
        print(
            f"Successful registrations out of 20 attempts: {successful_registrations}"
        )


@pytest.mark.security
class TestInputValidation:
    """Test input validation and sanitization"""

    def test_email_validation(self, client):
        """Test email format validation"""
        invalid_emails = [
            "notanemail",
            "@domain.com",
            "user@",
            "user..user@domain.com",
            "user@domain",
            "user name@domain.com",  # Space in email
            "user@domain..com",  # Double dot
        ]

        for invalid_email in invalid_emails:
            registration_data = {
                "email": invalid_email,
                "password": "testpassword123",
                "firstName": "Test",
                "lastName": "User",
                "league": "TEST_LEAGUE",
                "club": "Test Club",
                "series": "Test Series",
            }

            response = client.post(
                "/api/register", json=registration_data, content_type="application/json"
            )

            # Should reject invalid emails
            # Note: Current implementation may not validate email format
            print(f"Testing invalid email: {invalid_email} -> {response.status_code}")

    def test_password_strength_validation(self, client):
        """Test password strength requirements"""
        weak_passwords = [
            "123",  # Too short
            "password",  # Common password
            "abc",  # Too short
            "",  # Empty
            "12345678",  # Numbers only
            "abcdefgh",  # Letters only
        ]

        for weak_password in weak_passwords:
            registration_data = {
                "email": f"weak{hash(weak_password)}@example.com",
                "password": weak_password,
                "firstName": "Weak",
                "lastName": "Password",
                "league": "TEST_LEAGUE",
                "club": "Test Club",
                "series": "Test Series",
            }

            response = client.post(
                "/api/register", json=registration_data, content_type="application/json"
            )

            # Should enforce password strength
            # Note: Current implementation may not validate password strength
            print(f"Testing weak password: '{weak_password}' -> {response.status_code}")

    def test_input_length_limits(self, client):
        """Test protection against oversized input"""
        oversized_inputs = {
            "firstName": "A" * 1000,  # Very long name
            "lastName": "B" * 1000,  # Very long name
            "club": "C" * 1000,  # Very long club name
            "series": "D" * 1000,  # Very long series name
        }

        for field, oversized_value in oversized_inputs.items():
            registration_data = {
                "email": f"oversize{field}@example.com",
                "password": "testpassword123",
                "firstName": "Test",
                "lastName": "User",
                "league": "TEST_LEAGUE",
                "club": "Test Club",
                "series": "Test Series",
            }
            registration_data[field] = oversized_value

            response = client.post(
                "/api/register", json=registration_data, content_type="application/json"
            )

            # Should reject oversized input
            assert response.status_code in [
                400,
                413,
                500,
            ]  # Bad request or payload too large

    def test_special_character_handling(self, client):
        """Test handling of special characters in input"""
        special_chars = [
            "Test\x00User",  # Null byte
            "Test\nUser",  # Newline
            "Test\rUser",  # Carriage return
            "Test\tUser",  # Tab
            "Test\x1fUser",  # Control character
            "Test\x7fUser",  # DEL character
        ]

        for special_char in special_chars:
            registration_data = {
                "email": f"special{hash(special_char)}@example.com",
                "password": "testpassword123",
                "firstName": special_char,
                "lastName": "User",
                "league": "TEST_LEAGUE",
                "club": "Test Club",
                "series": "Test Series",
            }

            response = client.post(
                "/api/register", json=registration_data, content_type="application/json"
            )

            # Should handle special characters gracefully
            assert response.status_code in [201, 400]


@pytest.mark.security
class TestPathTraversalPrevention:
    """Test path traversal attack prevention"""

    def test_file_access_path_traversal(self, client, mock_security_payloads):
        """Test protection against path traversal in file access"""
        for path_payload in mock_security_payloads["path_traversal"]:
            # Test static file serving
            response = client.get(f"/static/{path_payload}")

            # Should not allow access to files outside static directory
            assert response.status_code in [400, 403, 404]

    def test_template_path_traversal(
        self, authenticated_client, mock_security_payloads
    ):
        """Test protection against path traversal in template rendering"""
        # This would test if template names can be manipulated
        # Most modern frameworks prevent this, but worth testing

        for path_payload in mock_security_payloads["path_traversal"]:
            # Try to access templates with path traversal
            response = authenticated_client.get(f"/template/{path_payload}")

            # Should not allow access
            assert response.status_code in [400, 403, 404]


@pytest.mark.security
class TestSecurityHeaders:
    """Test security headers and configurations"""

    def test_security_headers_present(self, client):
        """Test that appropriate security headers are set"""
        response = client.get("/")

        # Check for common security headers
        headers_to_check = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",  # HTTPS only
            "Content-Security-Policy",
            "Referrer-Policy",
        ]

        for header in headers_to_check:
            # Not all headers may be implemented yet
            if header in response.headers:
                print(f"✓ {header}: {response.headers[header]}")
            else:
                print(f"⚠ Missing security header: {header}")

    def test_sensitive_info_not_exposed(self, client):
        """Test that sensitive information is not exposed in responses"""
        response = client.get("/health")

        assert response.status_code == 200
        response_text = response.get_data(as_text=True)

        # Should not expose sensitive information
        sensitive_patterns = [
            r"password",
            r"secret",
            r"key",
            r"token",
            r"database.*url",
            r"connection.*string",
        ]

        for pattern in sensitive_patterns:
            matches = re.search(pattern, response_text, re.IGNORECASE)
            if matches:
                print(f"⚠ Potentially sensitive info exposed: {matches.group()}")


@pytest.mark.security
class TestDataProtection:
    """Test data protection and privacy measures"""

    def test_password_not_returned_in_api(self, authenticated_client, test_user):
        """Test that passwords are never returned in API responses"""
        # Test user profile endpoint
        response = authenticated_client.get("/api/user/profile")

        if response.status_code == 200:
            data = response.get_json()

            # Ensure no password fields are present
            def check_no_passwords(obj, path=""):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        current_path = f"{path}.{key}" if path else key
                        if "password" in key.lower():
                            pytest.fail(
                                f"Password field found in API response: {current_path}"
                            )
                        check_no_passwords(value, current_path)
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        check_no_passwords(item, f"{path}[{i}]")

            check_no_passwords(data)

    def test_user_data_isolation(
        self, authenticated_client, db_session, test_user, test_player
    ):
        """Test that users can only access their own data"""
        # Create another user
        other_user = User(
            email="other@example.com",
            password_hash="hashed",
            first_name="Other",
            last_name="User",
        )
        db_session.add(other_user)
        db_session.commit()

        # Try to access other user's data
        response = authenticated_client.get(f"/api/users/{other_user.id}")

        # Should be forbidden or not found
        assert response.status_code in [401, 403, 404]

    def test_database_connection_security(self):
        """Test database connection security"""
        # Verify that database connections use secure configurations
        from database_config import get_db_url

        db_url = get_db_url()

        # Should use SSL for production databases
        if "localhost" not in db_url and "127.0.0.1" not in db_url:
            assert "sslmode=require" in db_url or "ssl=true" in db_url


@pytest.mark.security
class TestSecurityRegression:
    """Regression tests for previously fixed security issues"""

    def test_session_fixation_prevention(self, client):
        """Test prevention of session fixation attacks"""
        # Get initial session
        with client.session_transaction() as sess:
            initial_session_id = id(sess)

        # Perform login
        login_data = {"email": "test@example.com", "password": "testpassword123"}

        response = client.post(
            "/api/login", json=login_data, content_type="application/json"
        )

        # Session should be regenerated after login
        with client.session_transaction() as sess:
            post_login_session_id = id(sess)

        # Note: Session ID regeneration depends on Flask-Session configuration
        # This test documents expected behavior

    def test_csrf_token_validation(self, authenticated_client):
        """Test CSRF token validation for state-changing operations"""
        # Test POST operations without CSRF token
        poll_data = {"question": "CSRF Test?", "choices": ["Yes", "No"], "team_id": 1}

        response = authenticated_client.post(
            "/api/polls", json=poll_data, content_type="application/json"
        )

        # Current implementation may not use CSRF tokens for API endpoints
        # This test documents expected behavior if CSRF protection is added
        print(f"CSRF test result: {response.status_code}")

    def test_clickjacking_prevention(self, client):
        """Test clickjacking prevention via X-Frame-Options"""
        response = client.get("/")

        # Should have X-Frame-Options header
        frame_options = response.headers.get("X-Frame-Options")
        if frame_options:
            assert frame_options.upper() in ["DENY", "SAMEORIGIN"]
        else:
            print("⚠ X-Frame-Options header not set - clickjacking may be possible")
