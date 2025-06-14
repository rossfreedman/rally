#!/usr/bin/env python3
"""
Quick Database State Checker
=============================
Compare the current state of local and Railway databases to understand
what needs to be synced.

Usage:
    python scripts/check_database_state.py
"""

import psycopg2
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Database connection details
LOCAL_DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'rally',
    'user': 'postgres',
    'password': 'password'
}

RAILWAY_DB_CONFIG = {
    'host': 'ballast.proxy.rlwy.net',
    'port': 40911,
    'database': 'railway',
    'user': 'postgres',
    'password': 'HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq'
}

def get_database_info(config, name):
    """Get comprehensive database information"""
    logger.info(f"🔍 Analyzing {name} database...")
    
    try:
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database=config['database'],
            user=config['user'],
            password=config['password'],
            connect_timeout=10,
            sslmode='require' if 'railway' in config['host'] else 'prefer'
        )
        
        info = {}
        
        with conn.cursor() as cur:
            # Basic database info
            cur.execute("SELECT current_database(), current_user, version()")
            db, user, version = cur.fetchone()
            info['database'] = db
            info['user'] = user
            info['version'] = version.split(',')[0]  # Just the version number
            
            # Get all tables
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            tables = [row[0] for row in cur.fetchall()]
            info['tables'] = tables
            
            # Get record counts
            counts = {}
            for table in tables:
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    counts[table] = cur.fetchone()[0]
                except Exception as e:
                    counts[table] = f"ERROR: {e}"
            
            info['counts'] = counts
            
            # Check for Alembic version table
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'alembic_version'
                )
            """)
            has_alembic = cur.fetchone()[0]
            
            if has_alembic:
                cur.execute("SELECT version_num FROM alembic_version")
                result = cur.fetchone()
                info['alembic_version'] = result[0] if result else 'None'
            else:
                info['alembic_version'] = 'No alembic_version table'
        
        conn.close()
        return info
        
    except Exception as e:
        logger.error(f"❌ Failed to analyze {name} database: {e}")
        return None

def compare_databases():
    """Compare local and Railway databases"""
    logger.info("🚀 RALLY DATABASE STATE COMPARISON")
    logger.info("=" * 70)
    
    # Get database info
    local_info = get_database_info(LOCAL_DB_CONFIG, "Local")
    railway_info = get_database_info(RAILWAY_DB_CONFIG, "Railway")
    
    if not local_info or not railway_info:
        logger.error("❌ Could not retrieve database information")
        return
    
    # Basic info comparison
    logger.info("\n📊 DATABASE OVERVIEW")
    logger.info("-" * 40)
    logger.info(f"Local   - Database: {local_info['database']}, User: {local_info['user']}")
    logger.info(f"Railway - Database: {railway_info['database']}, User: {railway_info['user']}")
    logger.info(f"Local   - PostgreSQL: {local_info['version']}")
    logger.info(f"Railway - PostgreSQL: {railway_info['version']}")
    
    # Alembic version comparison
    logger.info("\n🔄 ALEMBIC MIGRATION STATE")
    logger.info("-" * 40)
    logger.info(f"Local   Migration: {local_info['alembic_version']}")
    logger.info(f"Railway Migration: {railway_info['alembic_version']}")
    
    if local_info['alembic_version'] == railway_info['alembic_version']:
        logger.info("✅ Alembic versions MATCH")
    else:
        logger.warning("⚠️  Alembic versions DIFFER")
    
    # Table comparison
    local_tables = set(local_info['tables'])
    railway_tables = set(railway_info['tables'])
    
    logger.info("\n📋 TABLE COMPARISON")
    logger.info("-" * 40)
    logger.info(f"Local tables: {len(local_tables)}")
    logger.info(f"Railway tables: {len(railway_tables)}")
    
    # Tables only in one database
    local_only = local_tables - railway_tables
    railway_only = railway_tables - local_tables
    common_tables = local_tables & railway_tables
    
    if local_only:
        logger.warning(f"⚠️  Tables only in LOCAL: {sorted(local_only)}")
    
    if railway_only:
        logger.warning(f"⚠️  Tables only in RAILWAY: {sorted(railway_only)}")
    
    if not local_only and not railway_only:
        logger.info("✅ Both databases have the same tables")
    
    # Record count comparison
    logger.info("\n📊 RECORD COUNT COMPARISON")
    logger.info("-" * 70)
    logger.info(f"{'Table':<25} {'Local':<15} {'Railway':<15} {'Status':<15}")
    logger.info("-" * 70)
    
    total_differences = 0
    local_total = 0
    railway_total = 0
    
    for table in sorted(common_tables):
        local_count = local_info['counts'].get(table, 0)
        railway_count = railway_info['counts'].get(table, 0)
        
        if isinstance(local_count, int):
            local_total += local_count
        if isinstance(railway_count, int):
            railway_total += railway_count
        
        if local_count == railway_count:
            status = "✅ MATCH"
        else:
            status = "❌ DIFFER"
            total_differences += 1
        
        logger.info(f"{table:<25} {str(local_count):<15} {str(railway_count):<15} {status:<15}")
    
    logger.info("-" * 70)
    logger.info(f"{'TOTAL':<25} {local_total:<15,} {railway_total:<15,}")
    
    # Summary
    logger.info("\n📋 SUMMARY")
    logger.info("-" * 40)
    
    if total_differences == 0:
        logger.info("🎉 DATABASES ARE IN SYNC!")
        logger.info("✅ All table record counts match")
    else:
        logger.warning(f"⚠️  DATABASES ARE OUT OF SYNC!")
        logger.warning(f"❌ {total_differences} table(s) have different record counts")
        logger.warning(f"📊 Total record difference: {abs(local_total - railway_total):,}")
        
        if local_total > railway_total:
            logger.info("📈 Local database has MORE records than Railway")
        elif railway_total > local_total:
            logger.info("📉 Railway database has MORE records than Local")
    
    # Recommendations
    logger.info("\n💡 RECOMMENDATIONS")
    logger.info("-" * 40)
    
    if total_differences > 0:
        logger.info("🔄 Run the database mirror script to sync Railway with Local:")
        logger.info("   python scripts/mirror_local_to_railway.py --dry-run")
        logger.info("   python scripts/mirror_local_to_railway.py")
    else:
        logger.info("✅ No action needed - databases are already in sync")
    
    return total_differences == 0

if __name__ == '__main__':
    compare_databases() 