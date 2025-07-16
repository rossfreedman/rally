#!/usr/bin/env python3
"""
Test script for temporary password middleware integration
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, session, request
from app.middleware.temporary_password_middleware import TemporaryPasswordMiddleware


def test_middleware_integration():
    """Test the middleware integration in a Flask context"""
    
    print("🧪 Testing Temporary Password Middleware Integration")
    print("=" * 60)
    
    # Create a test Flask app
    app = Flask(__name__)
    app.secret_key = 'test-secret-key'
    
    # Initialize the middleware
    TemporaryPasswordMiddleware(app)
    
    # Add test routes
    @app.route('/test-page')
    def test_page():
        return "Test page - should be blocked for temporary password users"
    
    @app.route('/change-password')
    def change_password():
        return "Change password page - should be accessible"
    
    @app.route('/api/test')
    def test_api():
        return {"message": "Test API - should be blocked for temporary password users"}
    
    @app.route('/api/change-password')
    def change_password_api():
        return {"message": "Change password API - should be accessible"}
    
    @app.route('/static/test.css')
    def test_static():
        return "Static file - should be accessible"
    
    # Test scenarios
    test_scenarios = [
        {
            "name": "User with temporary password accessing protected page",
            "session_data": {"user": {"email": "test@example.com", "has_temporary_password": True}},
            "path": "/test-page",
            "expected_status": 302,  # Redirect
            "expected_location": "/change-password"
        },
        {
            "name": "User with temporary password accessing protected API",
            "session_data": {"user": {"email": "test@example.com", "has_temporary_password": True}},
            "path": "/api/test",
            "expected_status": 403,  # Forbidden
            "expected_json": {"error": "Password change required"}
        },
        {
            "name": "User with temporary password accessing change password page",
            "session_data": {"user": {"email": "test@example.com", "has_temporary_password": True}},
            "path": "/change-password",
            "expected_status": 200,  # OK
            "expected_content": "Change password page"
        },
        {
            "name": "User with temporary password accessing change password API",
            "session_data": {"user": {"email": "test@example.com", "has_temporary_password": True}},
            "path": "/api/change-password",
            "expected_status": 200,  # OK
            "expected_json": {"message": "Change password API"}
        },
        {
            "name": "User with temporary password accessing static file",
            "session_data": {"user": {"email": "test@example.com", "has_temporary_password": True}},
            "path": "/static/test.css",
            "expected_status": 200,  # OK
            "expected_content": "Static file"
        },
        {
            "name": "User without temporary password accessing protected page",
            "session_data": {"user": {"email": "test@example.com", "has_temporary_password": False}},
            "path": "/test-page",
            "expected_status": 200,  # OK
            "expected_content": "Test page"
        },
        {
            "name": "User without temporary password accessing protected API",
            "session_data": {"user": {"email": "test@example.com", "has_temporary_password": False}},
            "path": "/api/test",
            "expected_status": 200,  # OK
            "expected_json": {"message": "Test API"}
        },
        {
            "name": "No user session accessing protected page",
            "session_data": {},
            "path": "/test-page",
            "expected_status": 200,  # OK (middleware only checks authenticated users)
            "expected_content": "Test page"
        }
    ]
    
    with app.test_client() as client:
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n{i}. {scenario['name']}")
            print(f"   Path: {scenario['path']}")
            print(f"   Expected status: {scenario['expected_status']}")
            
            # Set up session
            with client.session_transaction() as sess:
                sess.update(scenario['session_data'])
            
            # Make request
            response = client.get(scenario['path'])
            
            # Check status
            if response.status_code == scenario['expected_status']:
                print(f"   ✅ Status code: {response.status_code}")
            else:
                print(f"   ❌ Status code: {response.status_code} (expected {scenario['expected_status']})")
            
            # Check redirect location
            if scenario['expected_status'] == 302:
                if response.location == scenario['expected_location']:
                    print(f"   ✅ Redirect location: {response.location}")
                else:
                    print(f"   ❌ Redirect location: {response.location} (expected {scenario['expected_location']})")
            
            # Check JSON response
            if scenario['expected_status'] == 403:
                try:
                    json_data = response.get_json()
                    if json_data.get('error') == scenario['expected_json']['error']:
                        print(f"   ✅ JSON error: {json_data['error']}")
                    else:
                        print(f"   ❌ JSON error: {json_data.get('error')} (expected {scenario['expected_json']['error']})")
                except:
                    print(f"   ❌ No JSON response")
            
            # Check content
            if scenario['expected_status'] == 200 and 'expected_content' in scenario:
                content = response.get_data(as_text=True)
                if scenario['expected_content'] in content:
                    print(f"   ✅ Content contains expected text")
                else:
                    print(f"   ❌ Content: {content[:50]}...")
            elif scenario['expected_status'] == 200 and 'expected_json' in scenario:
                try:
                    json_data = response.get_json()
                    if json_data.get('message') == scenario['expected_json']['message']:
                        print(f"   ✅ JSON response: {json_data['message']}")
                    else:
                        print(f"   ❌ JSON response: {json_data}")
                except:
                    print(f"   ❌ No JSON response")
            elif scenario['expected_status'] == 200:
                print(f"   ✅ Request successful")
    
    print(f"\n🎉 Middleware integration test completed!")
    print(f"📋 The middleware should now properly block users with temporary passwords")
    print(f"   from accessing protected pages and APIs while allowing access to")
    print(f"   the change password page and static files.")


if __name__ == "__main__":
    test_middleware_integration() 