#!/usr/bin/env python3
"""
Simple migration fix: temporarily disable foreign key constraints
"""

import psycopg2
from urllib.parse import urlparse
import logging
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

RAILWAY_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

def connect_to_railway():
    """Connect to Railway database"""
    parsed = urlparse(RAILWAY_URL)
    conn_params = {
        'dbname': parsed.path[1:],
        'user': parsed.username,
        'password': parsed.password,
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'sslmode': 'require',
        'connect_timeout': 10
    }
    return psycopg2.connect(**conn_params)

def migrate_table_simple(local_conn, railway_conn, table_name, exclude_columns=None):
    """Simple table migration with conflict resolution"""
    exclude_columns = exclude_columns or []
    
    local_cursor = local_conn.cursor()
    railway_cursor = railway_conn.cursor()
    
    # Get total count
    local_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    total_rows = local_cursor.fetchone()[0]
    
    if total_rows == 0:
        logger.info(f"  📭 {table_name}: No data to migrate")
        return 0
    
    logger.info(f"  📊 {table_name}: Migrating {total_rows} records...")
    
    # Get column names (excluding specified columns)
    local_cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
    all_columns = [desc[0] for desc in local_cursor.description]
    columns = [col for col in all_columns if col not in exclude_columns]
    
    # Clear existing data first
    railway_cursor.execute(f"TRUNCATE TABLE {table_name} CASCADE")
    logger.info(f"    🗑️  Cleared existing {table_name} data")
    
    # Migrate in batches
    batch_size = 1000
    offset = 0
    migrated_count = 0
    
    while offset < total_rows:
        # Fetch batch
        column_select = ', '.join(columns)
        local_cursor.execute(f"""
            SELECT {column_select} FROM {table_name} 
            ORDER BY {all_columns[0]} 
            LIMIT {batch_size} OFFSET {offset}
        """)
        batch_rows = local_cursor.fetchall()
        
        if not batch_rows:
            break
        
        # Insert batch
        placeholders = ', '.join(['%s'] * len(columns))
        column_names = ', '.join(columns)
        
        insert_sql = f"""
            INSERT INTO {table_name} ({column_names}) 
            VALUES ({placeholders})
            ON CONFLICT DO NOTHING
        """
        
        railway_cursor.executemany(insert_sql, batch_rows)
        migrated_count += len(batch_rows)
        
        if migrated_count % 1000 == 0 or offset + batch_size >= total_rows:
            logger.info(f"    ✅ Migrated {migrated_count}/{total_rows} records")
        
        offset += batch_size
    
    return migrated_count

def simple_migration():
    """Simple migration approach"""
    logger.info("🚀 SIMPLE MIGRATION APPROACH")
    logger.info("="*60)
    
    with get_db() as local_conn:
        railway_conn = connect_to_railway()
        railway_cursor = railway_conn.cursor()
        
        try:
            # Step 1: Disable foreign key constraints temporarily
            logger.info("🔓 Temporarily disabling foreign key constraints...")
            railway_cursor.execute("SET session_replication_role = replica;")
            
            # Step 2: Migrate players (excluding id to avoid conflicts)
            logger.info("\n📋 MIGRATING PLAYERS:")
            player_count = migrate_table_simple(local_conn, railway_conn, 'players', exclude_columns=['id'])
            railway_conn.commit()
            
            # Step 3: Migrate player_history (excluding id)
            logger.info("\n📋 MIGRATING PLAYER HISTORY:")
            history_count = migrate_table_simple(local_conn, railway_conn, 'player_history', exclude_columns=['id'])
            railway_conn.commit()
            
            # Step 4: Migrate user_player_associations (excluding original ids)
            logger.info("\n📋 MIGRATING USER-PLAYER ASSOCIATIONS:")
            
            # For user_player_associations, we need to map the user and player IDs
            # Let's create a simple mapping approach
            local_cursor = local_conn.cursor()
            
            # Get local associations
            local_cursor.execute("SELECT user_id, player_id, is_primary, created_at FROM user_player_associations")
            local_associations = local_cursor.fetchall()
            
            association_count = 0
            if local_associations:
                # Get user mapping (assuming user emails are unique)
                local_cursor.execute("SELECT id, email FROM users")
                local_users = {email: local_id for local_id, email in local_cursor.fetchall()}
                
                railway_cursor.execute("SELECT id, email FROM users")
                railway_users = {email: railway_id for railway_id, email in railway_cursor.fetchall()}
                
                # Get player mapping (using tenniscores_player_id as unique key)
                local_cursor.execute("SELECT id, tenniscores_player_id FROM players WHERE tenniscores_player_id IS NOT NULL")
                local_players = {tc_id: local_id for local_id, tc_id in local_cursor.fetchall()}
                
                railway_cursor.execute("SELECT id, tenniscores_player_id FROM players WHERE tenniscores_player_id IS NOT NULL")
                railway_players = {tc_id: railway_id for railway_id, tc_id in railway_cursor.fetchall()}
                
                # Map and insert associations
                for local_user_id, local_player_id, is_primary, created_at in local_associations:
                    # Find corresponding user by email
                    local_cursor.execute("SELECT email FROM users WHERE id = %s", (local_user_id,))
                    user_result = local_cursor.fetchone()
                    if not user_result:
                        continue
                    
                    user_email = user_result[0]
                    if user_email not in railway_users:
                        continue
                    
                    # Find corresponding player by tenniscores_player_id
                    local_cursor.execute("SELECT tenniscores_player_id FROM players WHERE id = %s", (local_player_id,))
                    player_result = local_cursor.fetchone()
                    if not player_result or not player_result[0]:
                        continue
                    
                    tc_player_id = player_result[0]
                    if tc_player_id not in railway_players:
                        continue
                    
                    # Insert association with mapped IDs
                    railway_user_id = railway_users[user_email]
                    railway_player_id = railway_players[tc_player_id]
                    
                    try:
                        railway_cursor.execute("""
                            INSERT INTO user_player_associations (user_id, player_id, is_primary, created_at)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT DO NOTHING
                        """, (railway_user_id, railway_player_id, is_primary, created_at))
                        association_count += 1
                    except Exception as e:
                        logger.warning(f"    ⚠️  Failed to migrate association: {e}")
            
            logger.info(f"    ✅ Migrated {association_count} user-player associations")
            railway_conn.commit()
            
            # Step 5: Re-enable foreign key constraints
            logger.info("\n🔒 Re-enabling foreign key constraints...")
            railway_cursor.execute("SET session_replication_role = DEFAULT;")
            railway_conn.commit()
            
            # Step 6: Update sequences
            logger.info("\n🔧 Updating sequences...")
            tables_with_sequences = ['players', 'player_history']
            
            for table in tables_with_sequences:
                try:
                    railway_cursor.execute(f"""
                        SELECT setval(pg_get_serial_sequence('{table}', 'id'), 
                                      COALESCE((SELECT MAX(id) FROM {table}), 1), false)
                    """)
                    logger.info(f"    ✅ Updated {table} sequence")
                except Exception as e:
                    logger.warning(f"    ⚠️  Could not update {table} sequence: {e}")
            
            railway_conn.commit()
            
            # Final summary
            logger.info(f"\n" + "="*60)
            logger.info(f"✅ SIMPLE MIGRATION COMPLETED!")
            logger.info(f"📊 MIGRATION RESULTS:")
            logger.info(f"  • Players: {player_count} records")
            logger.info(f"  • Player History: {history_count} records")
            logger.info(f"  • User-Player Associations: {association_count} records")
            logger.info(f"  • Total new records: {player_count + history_count + association_count}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            # Re-enable constraints even on failure
            try:
                railway_cursor.execute("SET session_replication_role = DEFAULT;")
                railway_conn.commit()
            except:
                pass
            return False
        
        finally:
            railway_conn.close()

if __name__ == "__main__":
    success = simple_migration()
    if success:
        logger.info("\n🎯 MIGRATION COMPLETED!")
        logger.info("Test your application at: https://www.lovetorally.com")
    sys.exit(0 if success else 1) 