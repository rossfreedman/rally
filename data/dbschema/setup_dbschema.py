#!/usr/bin/env python3
"""
DbSchema Quick Setup Script
Guides you through the initial DbSchema setup with your Rally database.
"""

import os
import sys
from dotenv import load_dotenv

# Add root directory to path for imports (go up two levels from data/dbschema)
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

load_dotenv()

def print_banner():
    """Print setup banner"""
    print("🎯 DbSchema Quick Setup for Rally Database")
    print("=" * 50)
    print("This script will guide you through setting up DbSchema")
    print("for visual database management and schema synchronization.\n")

def check_prerequisites():
    """Check if prerequisites are met"""
    print("📋 CHECKING PREREQUISITES...")
    
    # Check if DbSchema is mentioned as installed
    print("   ✅ DbSchema - You mentioned it's already installed")
    
    # Check local PostgreSQL
    try:
        import psycopg2
        print("   ✅ psycopg2 - PostgreSQL Python adapter available")
    except ImportError:
        print("   ❌ psycopg2 - Required for database connections")
        return False
    
    # Check database connection
    local_url = "postgresql://rossfreedman@localhost/rally"
    if test_connection_silent("Local Database", local_url):
        print("   ✅ Local PostgreSQL - Connected successfully")
    else:
        print("   ❌ Local PostgreSQL - Connection failed")
        return False
    
    print("   ✅ All prerequisites met!\n")
    return True

def test_connection_silent(name, url):
    """Silent version of connection test"""
    try:
        from database_config import parse_db_url
        import psycopg2
        
        db_params = parse_db_url(url)
        conn = psycopg2.connect(**db_params)
        conn.close()
        return True
    except:
        return False

def print_dbschema_setup_steps():
    """Print step-by-step DbSchema setup instructions"""
    print("🚀 DBSCHEMA SETUP STEPS")
    print("=" * 30)
    
    print("\n1️⃣ OPEN DBSCHEMA")
    print("   Launch DbSchema application on your Mac")
    
    print("\n2️⃣ CREATE NEW PROJECT")
    print("   - File → New Project")
    print("   - Project Name: Rally Database")
    print("   - Save Location: database_schema/rally_schema.dbs")
    print("   - Click 'Create Project'")
    
    print("\n3️⃣ ADD LOCAL DATABASE CONNECTION")
    print("   - Click 'Add Connection' or Database → New Connection")
    print("   - Connection Name: Rally Local")
    print("   - Database Type: PostgreSQL")
    print("   - Fill in connection details:")
    print(f"     Host: localhost")
    print(f"     Port: 5432")
    print(f"     Database: rally")
    print(f"     Username: rossfreedman")
    print(f"     Password: (your local PostgreSQL password)")
    print(f"     SSL Mode: prefer")
    print("   - Test connection")
    print("   - Save connection")
    
    print("\n4️⃣ IMPORT DATABASE SCHEMA")
    print("   - Right-click on 'Rally Local' connection")
    print("   - Select 'Reverse Engineer' or 'Import Schema'")
    print("   - Select all tables (should show ~30 tables)")
    print("   - Include relationships and constraints")
    print("   - Click 'Import'")
    
    print("\n5️⃣ EXPLORE YOUR SCHEMA")
    print("   You should see these key tables:")
    print("   - users (authentication)")
    print("   - leagues (APTA_CHICAGO, NSTF, etc.)")
    print("   - clubs (tennis facilities)")
    print("   - series (divisions within leagues)")
    print("   - teams (club + series + league)")
    print("   - players (league-specific player records)")
    print("   - user_player_associations (user-player linking)")
    print("   - match_scores (match results)")
    print("   - And 22 more tables with full relationships!")

def print_verification_steps():
    """Print verification steps"""
    print("\n✅ VERIFICATION STEPS")
    print("=" * 25)
    
    print("\n📊 Verify Schema Import:")
    print("   - Should see ~30 tables in the diagram")
    print("   - Foreign key relationships should be visible as lines")
    print("   - Tables should show column details")
    
    print("\n🔗 Test Key Relationships:")
    print("   - users → user_player_associations (user_id)")
    print("   - user_player_associations → players (tenniscores_player_id)")
    print("   - players → teams (team_id)")
    print("   - teams → clubs, series, leagues")
    print("   - match_scores → teams (home_team_id, away_team_id)")
    
    print("\n📋 Generate Documentation:")
    print("   - Tools → Generate Documentation")
    print("   - Format: HTML")
    print("   - Include: Tables, Relationships, Constraints")
    print("   - Save to: docs/database_documentation/")

def print_next_steps():
    """Print next steps after setup"""
    print("\n🔗 WHAT'S NEXT?")
    print("=" * 20)
    
    print("\n🚂 Railway Connection (Optional):")
    print("   - Set up DATABASE_PUBLIC_URL environment variable")
    print("   - Run: python data/dbschema/validate_dbschema_connections.py")
    print("   - Add Railway connection to DbSchema")
    print("   - Compare schemas visually")
    
    print("\n📊 Schema Comparison:")
    print("   - Run: python data/dbschema/compare_schemas_dbschema.py")
    print("   - Use DbSchema's built-in schema comparison")
    print("   - Identify differences between environments")
    
    print("\n🔄 Daily Workflow:")
    print("   1. Make schema changes via Alembic migrations")
    print("   2. Refresh DbSchema to see changes")
    print("   3. Document relationships visually")
    print("   4. Validate with validation scripts")
    print("   5. Deploy with confidence")
    
    print("\n📖 Advanced Features:")
    print("   - Visual query builder")
    print("   - Schema comparison between environments")
    print("   - Data synchronization (use carefully)")
    print("   - Documentation generation")

def print_troubleshooting():
    """Print common troubleshooting tips"""
    print("\n🔧 TROUBLESHOOTING")
    print("=" * 20)
    
    print("\n❌ Connection Issues:")
    print("   - Check PostgreSQL is running: brew services list")
    print("   - Verify database exists: psql -l")
    print("   - Test manual connection: psql rally")
    
    print("\n❌ Schema Import Issues:")
    print("   - Ensure user has read permissions")
    print("   - Check for schema name (should be 'public')")
    print("   - Verify tables exist: \\dt in psql")
    
    print("\n❌ DbSchema Performance:")
    print("   - Close unnecessary connections")
    print("   - Increase Java heap size if needed")
    print("   - Use schema filtering for large databases")

def main():
    """Main setup function"""
    print_banner()
    
    if not check_prerequisites():
        print("❌ Prerequisites not met. Please fix issues above.")
        return
    
    print_dbschema_setup_steps()
    print_verification_steps()
    print_next_steps()
    print_troubleshooting()
    
    print("\n" + "=" * 50)
    print("🎉 READY TO START!")
    print("Your local database is ready for DbSchema.")
    print("Follow the steps above to set up visual schema management.")
    print("\n💡 Pro tip: Start with the local connection first,")
    print("   then add Railway connection once you're comfortable.")
    print("=" * 50)

if __name__ == "__main__":
    main() 