#!/usr/bin/env python3

import os
import sys
import psycopg2
from urllib.parse import urlparse

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Railway staging database URL (from staging environment)
STAGING_DB_URL = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"

def execute_query_railway(query, params=None):
    """Execute query on Railway staging database"""
    try:
        # Parse Railway URL
        parsed = urlparse(STAGING_DB_URL)
        conn_params = {
            "dbname": parsed.path[1:],
            "user": parsed.username,
            "password": parsed.password,
            "host": parsed.hostname,
            "port": parsed.port or 5432,
            "sslmode": "require",
            "connect_timeout": 30,
        }
        
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        if query.strip().upper().startswith('SELECT'):
            # For SELECT queries, fetch all results
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            results = []
            for row in rows:
                results.append(dict(zip(columns, row)))
            return results
        else:
            # For other queries, commit and return affected rows
            conn.commit()
            return cursor.rowcount
            
    except Exception as e:
        print(f"Database error: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def execute_query_one_railway(query, params=None):
    """Execute query and return single result on Railway staging database"""
    results = execute_query_railway(query, params)
    return results[0] if results else None

def debug_user_matches():
    """Debug why the user's matches aren't showing up on Railway staging"""
    
    # User data from the logs
    user_email = "rossfreedman@gmail.com"
    tenniscores_player_id = "nndz-WkMrK3didjlnUT09"
    team_id = 15083
    league_id = 4515
    
    print(f"🔍 Debugging matches for user: {user_email}")
    print(f"   - tenniscores_player_id: {tenniscores_player_id}")
    print(f"   - team_id: {team_id}")
    print(f"   - league_id: {league_id}")
    print(f"🌐 Connecting to Railway STAGING database...")
    print("=" * 60)
    
    # 1. Check if the player exists in the players table
    print("1. Checking player record in players table...")
    player_query = """
        SELECT id, first_name, last_name, tenniscores_player_id, team_id, league_id, is_active
        FROM players 
        WHERE tenniscores_player_id = %s
    """
    players = execute_query_railway(player_query, [tenniscores_player_id])
    
    if players:
        print(f"   ✅ Found {len(players)} player record(s):")
        for p in players:
            print(f"      ID: {p['id']}, Name: {p['first_name']} {p['last_name']}")
            print(f"      Team ID: {p['team_id']}, League ID: {p['league_id']}, Active: {p['is_active']}")
    else:
        print(f"   ❌ No player records found for tenniscores_player_id: {tenniscores_player_id}")
        return
    
    # 2. Check for any matches with this player ID (no filtering)
    print(f"\n2. Checking raw matches for this player ID...")
    raw_matches_query = """
        SELECT COUNT(*) as total_matches
        FROM match_scores
        WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
    """
    total_result = execute_query_one_railway(raw_matches_query, [tenniscores_player_id, tenniscores_player_id, tenniscores_player_id, tenniscores_player_id])
    total_matches = total_result['total_matches'] if total_result else 0
    print(f"   Total matches (any league/team): {total_matches}")
    
    if total_matches == 0:
        print(f"   ❌ No matches found for this player ID in match_scores table")
        
        # Check if there are any matches with similar player IDs
        print(f"\n   Checking for similar player IDs...")
        similar_query = """
            SELECT DISTINCT home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id
            FROM match_scores
            WHERE (home_player_1_id LIKE %s OR home_player_2_id LIKE %s OR away_player_1_id LIKE %s OR away_player_2_id LIKE %s)
            LIMIT 10
        """
        pattern = f"{tenniscores_player_id[:10]}%"
        similar_matches = execute_query_railway(similar_query, [pattern, pattern, pattern, pattern])
        
        if similar_matches:
            print(f"   Found some similar player IDs:")
            for match in similar_matches:
                for field in ['home_player_1_id', 'home_player_2_id', 'away_player_1_id', 'away_player_2_id']:
                    player_id = match[field]
                    if player_id and player_id.startswith(tenniscores_player_id[:10]):
                        print(f"      {field}: {player_id}")
        return
    
    # 3. Check matches by league
    print(f"\n3. Checking matches by league {league_id}...")
    league_matches_query = """
        SELECT COUNT(*) as league_matches
        FROM match_scores
        WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
        AND league_id = %s
    """
    league_result = execute_query_one_railway(league_matches_query, [tenniscores_player_id, tenniscores_player_id, tenniscores_player_id, tenniscores_player_id, league_id])
    league_matches = league_result['league_matches'] if league_result else 0
    print(f"   Matches in league {league_id}: {league_matches}")
    
    # 4. Check matches by team
    print(f"\n4. Checking matches by team {team_id}...")
    team_matches_query = """
        SELECT COUNT(*) as team_matches
        FROM match_scores
        WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
        AND league_id = %s
        AND (home_team_id = %s OR away_team_id = %s)
    """
    team_result = execute_query_one_railway(team_matches_query, [tenniscores_player_id, tenniscores_player_id, tenniscores_player_id, tenniscores_player_id, league_id, team_id, team_id])
    team_matches = team_result['team_matches'] if team_result else 0
    print(f"   Matches in league {league_id} and team {team_id}: {team_matches}")
    
    # 5. Check what teams this player has matches with
    if league_matches > 0:
        print(f"\n5. Checking which teams this player has matches with...")
        team_distribution_query = """
            SELECT 
                home_team_id, away_team_id,
                home_team, away_team,
                COUNT(*) as match_count
            FROM match_scores
            WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
            AND league_id = %s
            GROUP BY home_team_id, away_team_id, home_team, away_team
            ORDER BY match_count DESC
        """
        team_dist = execute_query_railway(team_distribution_query, [tenniscores_player_id, tenniscores_player_id, tenniscores_player_id, tenniscores_player_id, league_id])
        
        if team_dist:
            print(f"   Teams this player has matches with:")
            for team in team_dist:
                print(f"      {team['home_team']} vs {team['away_team']} (IDs: {team['home_team_id']} vs {team['away_team_id']}): {team['match_count']} matches")
        
        # Check if team_id 15083 exists in teams table
        print(f"\n6. Checking if team_id {team_id} exists...")
        team_check_query = """
            SELECT id, team_name, league_id 
            FROM teams 
            WHERE id = %s
        """
        team_record = execute_query_one_railway(team_check_query, [team_id])
        if team_record:
            print(f"   ✅ Team {team_id} exists: {team_record['team_name']} (League: {team_record['league_id']})")
        else:
            print(f"   ❌ Team {team_id} does not exist in teams table")
    
    # 7. Sample a few actual matches
    if total_matches > 0:
        print(f"\n7. Sample recent matches...")
        sample_matches_query = """
            SELECT 
                id,
                TO_CHAR(match_date, 'DD-Mon-YY') as match_date,
                home_team,
                away_team,
                home_team_id,
                away_team_id,
                league_id,
                winner
            FROM match_scores
            WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
            ORDER BY match_date DESC
            LIMIT 5
        """
        sample_matches = execute_query_railway(sample_matches_query, [tenniscores_player_id, tenniscores_player_id, tenniscores_player_id, tenniscores_player_id])
        
        if sample_matches:
            print(f"   Recent matches:")
            for match in sample_matches:
                print(f"      {match['match_date']}: {match['home_team']} (ID: {match['home_team_id']}) vs {match['away_team']} (ID: {match['away_team_id']}) - League: {match['league_id']}")

    # 8. Check the session user record
    print(f"\n8. Checking user record in users table...")
    user_query = """
        SELECT id, email, first_name, last_name, league_context, tenniscores_player_id
        FROM users 
        WHERE email = %s
    """
    user_record = execute_query_one_railway(user_query, [user_email])
    if user_record:
        print(f"   ✅ User record found:")
        print(f"      ID: {user_record['id']}, Name: {user_record['first_name']} {user_record['last_name']}")
        print(f"      Email: {user_record['email']}")
        print(f"      League Context: {user_record['league_context']}")
        print(f"      Tenniscores Player ID: {user_record['tenniscores_player_id']}")
    else:
        print(f"   ❌ No user record found for email: {user_email}")

    # 9. Check user_player_associations
    print(f"\n9. Checking user_player_associations...")
    assoc_query = """
        SELECT user_id, tenniscores_player_id, created_at
        FROM user_player_associations 
        WHERE user_id = (SELECT id FROM users WHERE email = %s)
    """
    associations = execute_query_railway(assoc_query, [user_email])
    if associations:
        print(f"   ✅ Found {len(associations)} association(s):")
        for assoc in associations:
            print(f"      User ID: {assoc['user_id']}, Player ID: {assoc['tenniscores_player_id']}, Created: {assoc['created_at']}")
    else:
        print(f"   ❌ No associations found for user")

if __name__ == "__main__":
    debug_user_matches() 