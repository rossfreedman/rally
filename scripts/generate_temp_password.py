#!/usr/bin/env python3
"""
Generate a new temporary password for testing
"""

import sys
import os
import secrets
import string
from werkzeug.security import generate_password_hash

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_update

def generate_temp_password():
    """Generate a new temporary password for Ross"""
    
    print("🔐 Generating Temporary Password for Testing")
    print("=" * 50)
    
    # Generate a random temporary password (8 characters, mix of letters and numbers)
    alphabet = string.ascii_letters + string.digits
    temp_password = ''.join(secrets.choice(alphabet) for _ in range(8))
    
    print(f"📋 Generated temporary password: {temp_password}")
    
    # Hash the temporary password
    password_hash = generate_password_hash(temp_password, method='pbkdf2:sha256')
    
    print(f"🔒 Password hash: {password_hash[:50]}...")
    
    # Update Ross's password in database
    update_query = """
        UPDATE users 
        SET password_hash = %s, 
            has_temporary_password = TRUE,
            temporary_password_set_at = NOW()
        WHERE email = %s
    """
    
    result = execute_update(update_query, [password_hash, "rossfreedman@gmail.com"])
    
    if result:
        print(f"✅ Password updated successfully - {result} rows affected")
        print(f"🎯 Temporary password for rossfreedman@gmail.com: {temp_password}")
        print(f"🔗 Use this password to test the login flow")
    else:
        print(f"❌ Failed to update password - no rows affected")
    
    return temp_password

if __name__ == "__main__":
    generate_temp_password() 