"""Import all core data from local to Railway

Revision ID: import_all_data
Revises: import_missing_data
Create Date: 2025-06-12 09:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from database_config import get_db

# revision identifiers, used by Alembic.
revision = 'import_all_data'
down_revision = 'import_missing_data'
branch_labels = None
depends_on = None

def get_all_local_data():
    """Get all necessary data from local database"""
    print("📥 Fetching all data from local database...")
    
    data = {
        'leagues': [],
        'clubs': [],
        'series': [],
        'users': [],
        'players': [],
        'player_history': [],
        'user_player_associations': [],
        'match_scores': [],
        'schedule': [],
        'series_stats': [],
        'player_availability': []
    }
    
    # Connect explicitly to local database (hardcoded to avoid env var conflicts)
    import psycopg2
    local_conn_params = {
        'dbname': 'rally',
        'user': 'postgres', 
        'password': 'password',
        'host': 'localhost',
        'port': 5432,
        'sslmode': 'prefer'
    }
    
    try:
        print(f"   🔌 Connecting to local database: localhost:5432/rally")
        local_conn = psycopg2.connect(**local_conn_params)
        try:
            local_cursor = local_conn.cursor()
            
            # Get leagues
            local_cursor.execute("SELECT id, league_id, league_name, league_url, created_at, updated_at FROM leagues ORDER BY id")
            for row in local_cursor.fetchall():
                data['leagues'].append({
                    'id': row[0], 'league_id': row[1], 'league_name': row[2], 
                    'league_url': row[3], 'created_at': row[4], 'updated_at': row[5]
                })
            print(f"   ✅ Leagues: {len(data['leagues']):,}")
            
            # Get clubs
            local_cursor.execute("SELECT id, name, updated_at FROM clubs ORDER BY id")
            for row in local_cursor.fetchall():
                data['clubs'].append({
                    'id': row[0], 'name': row[1], 'updated_at': row[2]
                })
            print(f"   ✅ Clubs: {len(data['clubs']):,}")
            
            # Get series
            local_cursor.execute("SELECT id, name, updated_at FROM series ORDER BY id")
            for row in local_cursor.fetchall():
                data['series'].append({
                    'id': row[0], 'name': row[1], 'updated_at': row[2]
                })
            print(f"   ✅ Series: {len(data['series']):,}")
            
            # Get users
            local_cursor.execute("""
                SELECT id, email, password_hash, first_name, last_name, 
                       club_automation_password, is_admin, created_at, last_login,
                       series_id, league_id, club_id, tenniscores_player_id
                FROM users ORDER BY id
            """)
            for row in local_cursor.fetchall():
                data['users'].append({
                    'id': row[0], 'email': row[1], 'password_hash': row[2],
                    'first_name': row[3], 'last_name': row[4], 'club_automation_password': row[5],
                    'is_admin': row[6], 'created_at': row[7], 'last_login': row[8],
                    'series_id': row[9], 'league_id': row[10], 'club_id': row[11],
                    'tenniscores_player_id': row[12]
                })
            print(f"   ✅ Users: {len(data['users']):,}")
            
            # Get players
            local_cursor.execute("""
                SELECT id, tenniscores_player_id, first_name, last_name, email,
                       league_id, club_id, series_id, pti, wins, losses, win_percentage,
                       captain_status, career_win_percentage, career_matches, career_wins, career_losses,
                       is_active, created_at, updated_at
                FROM players ORDER BY id
            """)
            for row in local_cursor.fetchall():
                data['players'].append({
                    'id': row[0], 'tenniscores_player_id': row[1], 'first_name': row[2],
                    'last_name': row[3], 'email': row[4], 'league_id': row[5], 'club_id': row[6],
                    'series_id': row[7], 'pti': row[8], 'wins': row[9], 'losses': row[10],
                    'win_percentage': row[11], 'captain_status': row[12], 'career_win_percentage': row[13],
                    'career_matches': row[14], 'career_wins': row[15], 'career_losses': row[16],
                    'is_active': row[17], 'created_at': row[18], 'updated_at': row[19]
                })
            print(f"   ✅ Players: {len(data['players']):,}")
            
            # Get player_history
            local_cursor.execute("""
                SELECT player_id, league_id, series, date, end_pti, created_at
                FROM player_history ORDER BY id
            """)
            for row in local_cursor.fetchall():
                data['player_history'].append({
                    'player_id': row[0], 'league_id': row[1], 'series': row[2],
                    'date': row[3], 'end_pti': row[4], 'created_at': row[5]
                })
            print(f"   ✅ Player History: {len(data['player_history']):,}")
            
            # Get user_player_associations
            local_cursor.execute("""
                SELECT user_id, player_id, is_primary, created_at
                FROM user_player_associations ORDER BY created_at
            """)
            for row in local_cursor.fetchall():
                data['user_player_associations'].append({
                    'user_id': row[0], 'player_id': row[1], 'is_primary': row[2], 'created_at': row[3]
                })
            print(f"   ✅ User Player Associations: {len(data['user_player_associations']):,}")
            
            # Get match_scores (critical for player analysis)
            local_cursor.execute("""
                SELECT id, match_date, home_team, away_team, home_player_1_id, home_player_2_id, 
                       away_player_1_id, away_player_2_id, scores, winner, created_at, league_id
                FROM match_scores ORDER BY id
            """)
            for row in local_cursor.fetchall():
                data['match_scores'].append({
                    'id': row[0], 'match_date': row[1], 'home_team': row[2], 'away_team': row[3],
                    'home_player_1_id': row[4], 'home_player_2_id': row[5], 'away_player_1_id': row[6], 
                    'away_player_2_id': row[7], 'scores': row[8], 'winner': row[9], 'created_at': row[10], 'league_id': row[11]
                })
            print(f"   ✅ Match Scores: {len(data['match_scores']):,}")
            
            # Get schedule
            local_cursor.execute("""
                SELECT id, match_date, match_time, home_team, away_team, location, created_at, league_id
                FROM schedule ORDER BY id
            """)
            for row in local_cursor.fetchall():
                data['schedule'].append({
                    'id': row[0], 'match_date': row[1], 'match_time': row[2], 'home_team': row[3],
                    'away_team': row[4], 'location': row[5], 'created_at': row[6], 'league_id': row[7]
                })
            print(f"   ✅ Schedule: {len(data['schedule']):,}")
            
            # Get series_stats
            local_cursor.execute("""
                SELECT id, series, team, points, matches_won, matches_lost, matches_tied,
                       lines_won, lines_lost, lines_for, lines_ret, sets_won, sets_lost,
                       games_won, games_lost, created_at, league_id
                FROM series_stats ORDER BY id
            """)
            for row in local_cursor.fetchall():
                data['series_stats'].append({
                    'id': row[0], 'series': row[1], 'team': row[2], 'points': row[3],
                    'matches_won': row[4], 'matches_lost': row[5], 'matches_tied': row[6],
                    'lines_won': row[7], 'lines_lost': row[8], 'lines_for': row[9], 'lines_ret': row[10],
                    'sets_won': row[11], 'sets_lost': row[12], 'games_won': row[13], 'games_lost': row[14],
                    'created_at': row[15], 'league_id': row[16]
                })
            print(f"   ✅ Series Stats: {len(data['series_stats']):,}")
            
            # Get player_availability
            local_cursor.execute("""
                SELECT id, player_name, availability_status, updated_at, series_id, match_date, player_id
                FROM player_availability ORDER BY id
            """)
            for row in local_cursor.fetchall():
                data['player_availability'].append({
                    'id': row[0], 'player_name': row[1], 'availability_status': row[2], 'updated_at': row[3],
                    'series_id': row[4], 'match_date': row[5], 'player_id': row[6]
                })
            print(f"   ✅ Player Availability: {len(data['player_availability']):,}")
            
        finally:
            local_conn.close()
            
    except Exception as e:
        print(f"   ❌ Error fetching local data: {e}")
        raise
    
    return data

def clear_railway_data(connection):
    """Clear existing data from Railway"""
    print("🗑️  Clearing Railway data...")
    
    # Disable foreign key checks temporarily
    connection.execute(sa.text("SET session_replication_role = replica;"))
    
    # Clear tables in reverse dependency order
    tables_to_clear = [
        'player_availability', 'series_stats', 'schedule', 'match_scores',
        'user_player_associations', 'player_history', 'players', 'users', 
        'series', 'clubs', 'leagues'
    ]
    
    for table in tables_to_clear:
        try:
            connection.execute(sa.text(f"TRUNCATE TABLE {table} CASCADE"))
            print(f"   ✅ Cleared {table}")
        except Exception as e:
            print(f"   ⚠️  Could not clear {table}: {e}")
    
    # Re-enable foreign key checks
    connection.execute(sa.text("SET session_replication_role = DEFAULT;"))

def import_table_data(connection, table_name, data, columns):
    """Import data into a specific table"""
    if not data:
        print(f"   📭 {table_name}: No data to import")
        return
    
    print(f"   📊 Importing {len(data):,} records to {table_name}...")
    
    table = sa.table(table_name, *[sa.column(col) for col in columns])
    
    # Import in batches for better performance
    batch_size = 1000
    for i in range(0, len(data), batch_size):
        batch = data[i:i+batch_size]
        op.bulk_insert(table, batch)
        if len(data) > batch_size:
            print(f"      ✅ Batch {i//batch_size + 1}: {len(batch)} records")
    
    print(f"   ✅ {table_name}: {len(data):,} records imported")

def fix_sequences(connection):
    """Fix auto-increment sequences after import"""
    print("🔧 Fixing sequences...")
    
    tables_with_sequences = [
        ('leagues', 'id'), ('clubs', 'id'), ('series', 'id'), 
        ('users', 'id'), ('players', 'id'), ('player_history', 'id'),
        ('match_scores', 'id'), ('schedule', 'id'), ('series_stats', 'id'), 
        ('player_availability', 'id')
    ]
    
    for table, id_col in tables_with_sequences:
        try:
            result = connection.execute(sa.text(f"SELECT MAX({id_col}) FROM {table}"))
            max_id = result.scalar() or 0
            
            if max_id > 0:
                connection.execute(sa.text(f"""
                    SELECT setval(pg_get_serial_sequence('{table}', '{id_col}'), {max_id}, true)
                """))
                print(f"   ✅ Fixed {table} sequence (max: {max_id})")
        except Exception as e:
            print(f"   ⚠️  Could not fix {table} sequence: {e}")

def upgrade():
    """Import all core data to Railway"""
    print("🚀 IMPORTING ALL CORE DATA TO RAILWAY VIA ALEMBIC")
    print("=" * 60)
    
    connection = op.get_bind()
    
    # Check if data already exists
    current_users = connection.execute(sa.text("SELECT COUNT(*) FROM users")).scalar()
    current_players = connection.execute(sa.text("SELECT COUNT(*) FROM players")).scalar()
    current_matches = connection.execute(sa.text("SELECT COUNT(*) FROM match_scores")).scalar()
    
    print(f"📊 Current Railway state:")
    print(f"   Users: {current_users:,}")
    print(f"   Players: {current_players:,}")
    print(f"   Match Scores: {current_matches:,}")
    
    if current_users > 0 and current_players > 1000 and current_matches > 5000:
        print("✅ Complete data already exists. Skipping full import.")
        return
    elif current_matches == 0:
        print("⚠️  Match scores missing - proceeding with complete import.")
    else:
        print("⚠️  Some data exists but appears incomplete - proceeding with import.")
    
    # Get all local data
    local_data = get_all_local_data()
    
    # Clear existing Railway data
    clear_railway_data(connection)
    
    # Import data in dependency order
    print("\n📥 Importing data in dependency order...")
    
    # Core lookup tables first
    import_table_data(connection, 'leagues', local_data['leagues'], 
                     ['id', 'league_id', 'league_name', 'league_url', 'created_at', 'updated_at'])
    
    import_table_data(connection, 'clubs', local_data['clubs'],
                     ['id', 'name', 'updated_at'])
    
    import_table_data(connection, 'series', local_data['series'],
                     ['id', 'name', 'updated_at'])
    
    # Users
    import_table_data(connection, 'users', local_data['users'],
                     ['id', 'email', 'password_hash', 'first_name', 'last_name', 
                      'club_automation_password', 'is_admin', 'created_at', 'last_login',
                      'series_id', 'league_id', 'club_id', 'tenniscores_player_id'])
    
    # Players
    import_table_data(connection, 'players', local_data['players'],
                     ['id', 'tenniscores_player_id', 'first_name', 'last_name', 'email',
                      'league_id', 'club_id', 'series_id', 'pti', 'wins', 'losses', 'win_percentage',
                      'captain_status', 'career_win_percentage', 'career_matches', 'career_wins', 'career_losses',
                      'is_active', 'created_at', 'updated_at'])
    
    # Player history
    import_table_data(connection, 'player_history', local_data['player_history'],
                     ['player_id', 'league_id', 'series', 'date', 'end_pti', 'created_at'])
    
    # User player associations
    import_table_data(connection, 'user_player_associations', local_data['user_player_associations'],
                     ['user_id', 'player_id', 'is_primary', 'created_at'])
    
    # Match scores (critical for player analysis)
    import_table_data(connection, 'match_scores', local_data['match_scores'],
                     ['id', 'match_date', 'home_team', 'away_team', 'home_player_1_id', 'home_player_2_id',
                      'away_player_1_id', 'away_player_2_id', 'scores', 'winner', 'created_at', 'league_id'])
    
    # Schedule
    import_table_data(connection, 'schedule', local_data['schedule'],
                     ['id', 'match_date', 'match_time', 'home_team', 'away_team', 'location', 'created_at', 'league_id'])
    
    # Series stats
    import_table_data(connection, 'series_stats', local_data['series_stats'],
                     ['id', 'series', 'team', 'points', 'matches_won', 'matches_lost', 'matches_tied',
                      'lines_won', 'lines_lost', 'lines_for', 'lines_ret', 'sets_won', 'sets_lost',
                      'games_won', 'games_lost', 'created_at', 'league_id'])
    
    # Player availability
    import_table_data(connection, 'player_availability', local_data['player_availability'],
                     ['id', 'player_name', 'availability_status', 'updated_at', 'series_id', 'match_date', 'player_id'])
    
    # Fix sequences
    fix_sequences(connection)
    
    # Final verification
    final_users = connection.execute(sa.text("SELECT COUNT(*) FROM users")).scalar()
    final_players = connection.execute(sa.text("SELECT COUNT(*) FROM players")).scalar()
    final_ph = connection.execute(sa.text("SELECT COUNT(*) FROM player_history")).scalar()
    final_upa = connection.execute(sa.text("SELECT COUNT(*) FROM user_player_associations")).scalar()
    final_matches = connection.execute(sa.text("SELECT COUNT(*) FROM match_scores")).scalar()
    final_schedule = connection.execute(sa.text("SELECT COUNT(*) FROM schedule")).scalar()
    final_stats = connection.execute(sa.text("SELECT COUNT(*) FROM series_stats")).scalar()
    final_availability = connection.execute(sa.text("SELECT COUNT(*) FROM player_availability")).scalar()
    
    print(f"\n✅ COMPLETE IMPORT FINISHED!")
    print(f"📊 Final Railway counts:")
    print(f"   Users: {final_users:,}")
    print(f"   Players: {final_players:,}")
    print(f"   Player History: {final_ph:,}")
    print(f"   User Player Associations: {final_upa:,}")
    print(f"   Match Scores: {final_matches:,}")
    print(f"   Schedule: {final_schedule:,}")
    print(f"   Series Stats: {final_stats:,}")
    print(f"   Player Availability: {final_availability:,}")
    
    if final_matches > 5000 and final_ph > 100000 and final_upa > 0:
        print(f"\n🎉 ALL DATA SUCCESSFULLY IMPORTED!")
        print(f"🌐 Your application should now be fully functional at: https://www.lovetorally.com")
        print(f"🏓 Player analysis, match history, and all features should work!")
    else:
        print(f"\n⚠️  Import may be incomplete - check the counts above")

def downgrade():
    """Remove all imported data"""
    print("⏪ REMOVING ALL IMPORTED DATA")
    
    connection = op.get_bind()
    clear_railway_data(connection)
    
    print("✅ All imported data removed (including match_scores, schedule, series_stats, player_availability)") 