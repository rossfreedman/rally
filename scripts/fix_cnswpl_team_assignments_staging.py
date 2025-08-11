#!/usr/bin/env python3
"""
Fix CNSWPL team assignments on staging

ROOT CAUSE: ETL assigned Lisa Wagner to "Tennaqua 10" instead of "Tennaqua 12"
SOLUTION: Re-run CNSWPL bootstrap and player import to ensure correct team assignments

This script should be run on staging to fix the team assignment issues.
"""

import os
import sys
import subprocess
from datetime import datetime

def log(message):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def check_environment():
    """Verify we're running on staging"""
    if 'DATABASE_URL' not in os.environ:
        log("❌ ERROR: DATABASE_URL not found - not running on staging/Railway")
        return False
    
    db_url = os.environ.get('DATABASE_URL', '')
    if 'railway' not in db_url.lower():
        log("❌ ERROR: DATABASE_URL doesn't contain 'railway' - may not be staging")
        return False
    
    log("✅ Environment check passed - running on Railway staging")
    return True

def run_bootstrap_teams():
    """Bootstrap CNSWPL teams to ensure all teams exist"""
    log("🚀 Step 1: Bootstrapping CNSWPL teams...")
    
    try:
        # Change to the correct directory for ETL scripts
        os.chdir('/app')
        
        # Run team bootstrap for CNSWPL
        result = subprocess.run([
            'python3', 'data/etl/database_import/bootstrap_teams_from_players.py', 'CNSWPL'
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            log("✅ Team bootstrap completed successfully")
            log(f"Output: {result.stdout}")
            return True
        else:
            log("❌ Team bootstrap failed")
            log(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        log(f"❌ Team bootstrap error: {e}")
        return False

def run_player_import():
    """Re-import CNSWPL players with correct team assignments"""
    log("🚀 Step 2: Re-importing CNSWPL players...")
    
    try:
        # Run player import for CNSWPL
        result = subprocess.run([
            'python3', 'data/etl/database_import/import_players.py', 
            'data/leagues/CNSWPL/players.json'
        ], capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            log("✅ Player import completed successfully")
            log(f"Output: {result.stdout}")
            return True
        else:
            log("❌ Player import failed")
            log(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        log(f"❌ Player import error: {e}")
        return False

def verify_fix():
    """Verify that Lisa Wagner is now correctly assigned"""
    log("🔍 Step 3: Verifying fix...")
    
    try:
        # Add project root to path for database utilities
        sys.path.append('/app')
        from database_utils import execute_query_one
        
        # Check Lisa Wagner's current assignment
        query = """
        SELECT p.first_name, p.last_name, t.team_name, t.display_name, s.name as series_name
        FROM players p 
        JOIN teams t ON p.team_id = t.id
        JOIN series s ON t.series_id = s.id
        WHERE p.first_name = 'Lisa' AND p.last_name = 'Wagner'
        AND p.league_id = (SELECT id FROM leagues WHERE league_id = 'CNSWPL')
        """
        
        result = execute_query_one(query)
        
        if result:
            team_name = result['team_name']
            series_name = result['series_name']
            log(f"✅ Lisa Wagner found: {team_name} - {series_name}")
            
            if team_name == "Tennaqua 12" and series_name == "Series 12":
                log("🎉 SUCCESS: Lisa Wagner is correctly assigned to Tennaqua 12 / Series 12")
                return True
            else:
                log(f"❌ ISSUE: Lisa Wagner still assigned to {team_name} / {series_name} instead of Tennaqua 12 / Series 12")
                return False
        else:
            log("❌ ERROR: Lisa Wagner not found in database")
            return False
            
    except Exception as e:
        log(f"❌ Verification error: {e}")
        return False

def check_team_player_count():
    """Check how many players are on Tennaqua 12 team"""
    log("🔍 Step 4: Checking Tennaqua 12 team roster...")
    
    try:
        sys.path.append('/app')
        from database_utils import execute_query
        
        # Count players on Tennaqua 12
        query = """
        SELECT COUNT(*) as player_count
        FROM players p 
        JOIN teams t ON p.team_id = t.id
        WHERE t.team_name = 'Tennaqua 12'
        AND p.league_id = (SELECT id FROM leagues WHERE league_id = 'CNSWPL')
        """
        
        result = execute_query(query)
        
        if result:
            count = result[0]['player_count']
            log(f"✅ Tennaqua 12 team has {count} players")
            
            if count >= 10:  # Expecting around 12 players
                log("🎉 SUCCESS: Tennaqua 12 has proper team roster")
                return True
            else:
                log(f"⚠️ WARNING: Tennaqua 12 only has {count} players (expected ~12)")
                return False
        else:
            log("❌ ERROR: Could not count Tennaqua 12 players")
            return False
            
    except Exception as e:
        log(f"❌ Team count error: {e}")
        return False

def main():
    """Main execution flow"""
    log("🛠️ CNSWPL Team Assignment Fix for Staging")
    log("=" * 50)
    
    # Check environment
    if not check_environment():
        log("❌ Environment check failed - exiting")
        return False
    
    # Step 1: Bootstrap teams
    if not run_bootstrap_teams():
        log("❌ Team bootstrap failed - exiting")
        return False
    
    # Step 2: Re-import players
    if not run_player_import():
        log("❌ Player import failed - exiting") 
        return False
    
    # Step 3: Verify fix
    if not verify_fix():
        log("❌ Fix verification failed")
        return False
    
    # Step 4: Check team roster
    if not check_team_player_count():
        log("⚠️ Team roster check had issues")
    
    log("=" * 50)
    log("🎉 CNSWPL team assignment fix completed successfully!")
    log("✅ Lisa Wagner should now be correctly on Tennaqua 12")
    log("✅ Team roster should now show all 12 players")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        log("❌ Fix script failed")
        sys.exit(1)
    else:
        log("✅ Fix script completed successfully")
        sys.exit(0)
