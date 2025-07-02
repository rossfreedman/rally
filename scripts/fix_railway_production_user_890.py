#!/usr/bin/env python3
"""
Direct Railway production fix for user 890 association issue
Connects directly to Railway production database
"""

import os
import sys
import subprocess

def main():
    print("=== Railway Production User 890 Fix ===")
    
    # Get Railway production database URL
    print("\n1. Getting Railway production database connection...")
    
    try:
        # Use Railway CLI to get production database URL
        result = subprocess.run(['railway', 'variables'], capture_output=True, text=True, cwd='/Users/rossfreedman/dev/rally')
        
        if result.returncode != 0:
            print("❌ Failed to get Railway variables. Make sure Railway CLI is installed and you're logged in.")
            print("   Run: railway login")
            return
            
        # Parse DATABASE_URL from Railway variables
        database_url = None
        for line in result.stdout.split('\n'):
            if 'DATABASE_URL' in line and '=' in line:
                database_url = line.split('=', 1)[1].strip()
                break
                
        if not database_url:
            print("❌ DATABASE_URL not found in Railway variables")
            return
            
        print("✅ Got Railway production database URL")
        
        # Set environment variable and run fix
        env = os.environ.copy()
        env['DATABASE_URL'] = database_url
        
        print("\n2. Running production fix...")
        
        # Create the SQL commands to fix the issue
        fix_commands = f"""
import psycopg2
import os

# Connect to Railway production
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

print("=== Connected to Railway Production ===")

# Check user 890
cur.execute("SELECT * FROM users WHERE id = %s", (890,))
user_890 = cur.fetchone()

if user_890:
    print(f"✅ User 890 exists: {{user_890[1]}}")  # email is column 1
    
    # Check associations
    cur.execute("SELECT * FROM user_player_associations WHERE user_id = %s", (890,))
    associations = cur.fetchall()
    print(f"   Current associations: {{len(associations)}}")
    
    if len(associations) == 0:
        print("❌ No associations - creating missing association...")
        
        # Create the missing association
        cur.execute('''
            INSERT INTO user_player_associations (user_id, tenniscores_player_id, is_primary, created_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (user_id, tenniscores_player_id) DO NOTHING
        ''', (890, 'nndz-WkMrK3didjlnUT09', True))
        
        conn.commit()
        print("✅ Association created successfully")
    
    # Check league context
    cur.execute("SELECT * FROM players WHERE tenniscores_player_id = %s", ('nndz-WkMrK3didjlnUT09',))
    player = cur.fetchone()
    
    if player:
        player_league_id = player[3]  # league_id column
        user_league_context = user_890[10]  # league_context column
        
        print(f"   Player league_id: {{player_league_id}}")
        print(f"   User league_context: {{user_league_context}}")
        
        if player_league_id != user_league_context:
            print("⚠️  League context mismatch - fixing...")
            cur.execute("UPDATE users SET league_context = %s WHERE id = %s", (player_league_id, 890))
            conn.commit()
            print("✅ League context updated")
            
        print(f"✅ Player team_id: {{player[14]}}")  # team_id column
        
else:
    print("❌ User 890 does not exist in Railway production")
    
    # Check if rossfreedman@gmail.com exists with different ID
    cur.execute("SELECT * FROM users WHERE email = %s", ('rossfreedman@gmail.com',))
    users = cur.fetchall()
    print(f"   Found {{len(users)}} users with email rossfreedman@gmail.com")
    for user in users:
        print(f"   - User ID: {{user[0]}}, Created: {{user[6]}}")

cur.close()
conn.close()
print("\\n=== Railway Production Fix Complete ===")
"""
        
        # Write and execute the fix
        with open('/tmp/railway_fix.py', 'w') as f:
            f.write(fix_commands)
            
        result = subprocess.run([sys.executable, '/tmp/railway_fix.py'], 
                              env=env, capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
            
        # Clean up
        os.unlink('/tmp/railway_fix.py')
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
    print("\n=== Next Steps ===")
    print("1. User should log out of https://www.lovetorally.com")
    print("2. Clear browser cache/cookies")
    print("3. Log back in")
    print("4. Data should now be properly associated")

if __name__ == "__main__":
    main() 