#!/usr/bin/env python
import os
import sys
import psycopg2
from dotenv import load_dotenv
from urllib.parse import urlparse

def test_connection(url):
    """Test database connection and print detailed information"""
    print("\n🔍 Testing database connection...")
    
    # Parse the URL
    parsed = urlparse(url)
    print(f"Host: {parsed.hostname}")
    print(f"Port: {parsed.port}")
    print(f"Database: {parsed.path[1:]}")  # Remove leading '/'
    print(f"Username: {parsed.username}")
    
    try:
        # Try to connect
        print("\n📡 Attempting connection...")
        conn = psycopg2.connect(url)
        
        # Get server version
        cursor = conn.cursor()
        cursor.execute('SELECT version();')
        version = cursor.fetchone()[0]
        print(f"\n✅ Connection successful!")
        print(f"PostgreSQL version: {version}")
        
        # List tables
        print("\n📋 Listing tables:")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = cursor.fetchall()
        for table in tables:
            print(f"  - {table[0]}")
            
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.Error as e:
        print(f"\n❌ Connection failed!")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        
        # Additional error details
        if hasattr(e, 'pgcode'):
            print(f"PostgreSQL error code: {e.pgcode}")
        if hasattr(e, 'pgerror'):
            print(f"PostgreSQL error message: {e.pgerror}")
            
        # Network troubleshooting suggestions
        print("\n🔧 Troubleshooting suggestions:")
        print("1. Check if the hostname is reachable:")
        print(f"   ping {parsed.hostname}")
        print("2. Verify the port is accessible:")
        print(f"   nc -zv {parsed.hostname} {parsed.port}")
        print("3. Ensure your IP is allowlisted in Railway's database settings")
        print("4. Check if you're behind a VPN or firewall that might block the connection")
        
        return False

def main():
    load_dotenv()
    
    # Get Railway URL
    url = os.getenv('RAILWAY_POSTGRES_URL')
    if not url:
        print("❌ Error: RAILWAY_POSTGRES_URL environment variable is not set")
        sys.exit(1)
        
    # Convert internal hostname to public if needed
    if 'postgres.railway.internal' in url:
        url = url.replace(
            'postgres.railway.internal', 
            'postgres-production-0931.up.railway.app'
        )
    
    test_connection(url)

if __name__ == "__main__":
    main() 