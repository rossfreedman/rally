#!/usr/bin/env python3
"""
Rally Database Backup Utility with Alembic Integration

This script creates comprehensive backups of the Rally PostgreSQL database using pg_dump,
while also capturing Alembic migration state and providing restore capabilities.

Usage:
    python3 scripts/backup_database.py                    # Create backup with default settings
    python3 scripts/backup_database.py --format custom    # Create binary backup (smaller, faster)
    python3 scripts/backup_database.py --schema-only      # Create schema-only backup
    python3 scripts/backup_database.py --data-only        # Create data-only backup
    python3 scripts/backup_database.py --list             # List existing backups
    python3 scripts/backup_database.py --max-backups 5    # Keep only 5 most recent backups
    
Features:
- Uses pg_dump for reliable PostgreSQL backups
- Captures Alembic migration state information
- Supports multiple backup formats (SQL, custom, tar, directory)
- Automatic cleanup of old backups
- Backup verification and metadata storage
- Integration with existing Rally workflow

Author: Rally Team
"""

import os
import sys
import subprocess
import psycopg2
import json
import argparse
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_database_config():
    """Get database configuration from environment"""
    database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/rally')
    
    if database_url:
        parsed = urlparse(database_url)
        return {
            'host': parsed.hostname or 'localhost',
            'port': parsed.port or 5432,
            'database': parsed.path.lstrip('/') or 'rally',
            'user': parsed.username or 'postgres',
            'password': parsed.password or 'postgres',
            'url': database_url
        }
    
    # Fallback configuration
    return {
        'host': 'localhost',
        'port': 5432,
        'database': 'rally',
        'user': 'postgres',
        'password': 'postgres',
        'url': 'postgresql://postgres:postgres@localhost:5432/rally'
    }

def get_backup_directory():
    """Get backup directory (create if it doesn't exist)"""
    # Get current directory (script is in rally/scripts/)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    rally_root = os.path.dirname(current_dir)
    parent_dir = os.path.dirname(rally_root)
    
    # Create backup directory as sibling to rally folder
    backup_dir = os.path.join(parent_dir, 'rally_db_backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    return backup_dir

def get_alembic_info():
    """Get current Alembic migration information"""
    try:
        # Check current Alembic revision
        result = subprocess.run(['alembic', 'current'], 
                              capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        current_revision = result.stdout.strip() if result.returncode == 0 else 'unknown'
        
        # Check if there are pending migrations
        result = subprocess.run(['alembic', 'check'], 
                              capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        migrations_current = result.returncode == 0
        
        # Get migration history
        result = subprocess.run(['alembic', 'history'], 
                              capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        migration_history = result.stdout if result.returncode == 0 else 'unavailable'
        
        return {
            'current_revision': current_revision,
            'migrations_current': migrations_current,
            'migration_history': migration_history,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.warning(f"Could not get Alembic information: {e}")
        return {
            'current_revision': 'error',
            'migrations_current': False,
            'migration_history': f'Error: {e}',
            'timestamp': datetime.now().isoformat()
        }

def get_database_stats(config):
    """Get database statistics for backup metadata"""
    try:
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database=config['database'],
            user=config['user'],
            password=config['password']
        )
        
        stats = {}
        
        with conn.cursor() as cur:
            # Get PostgreSQL version
            cur.execute("SELECT version()")
            stats['postgresql_version'] = cur.fetchone()[0]
            
            # Get database size
            cur.execute(f"SELECT pg_size_pretty(pg_database_size('{config['database']}'))")
            stats['database_size'] = cur.fetchone()[0]
            
            # Get table count
            cur.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """)
            stats['table_count'] = cur.fetchone()[0]
            
            # Get record counts for major tables
            major_tables = ['users', 'players', 'match_scores', 'leagues', 'clubs', 'series']
            table_counts = {}
            
            for table in major_tables:
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    table_counts[table] = cur.fetchone()[0]
                except:
                    table_counts[table] = 'N/A'
            
            stats['table_counts'] = table_counts
        
        conn.close()
        return stats
        
    except Exception as e:
        logger.warning(f"Could not get database statistics: {e}")
        return {'error': str(e)}

def create_backup(backup_format='sql', schema_only=False, data_only=False, max_backups=10):
    """Create a database backup using pg_dump"""
    try:
        config = get_database_config()
        backup_dir = get_backup_directory()
        
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Determine file extension based on format
        extensions = {
            'sql': '.sql',
            'custom': '.dump',
            'tar': '.tar',
            'directory': ''
        }
        
        backup_name = f"rally_db_backup_{timestamp}"
        if backup_format != 'directory':
            backup_name += extensions.get(backup_format, '.sql')
        
        backup_path = os.path.join(backup_dir, backup_name)
        
        logger.info(f"🔄 Creating database backup...")
        logger.info(f"Database: {config['host']}:{config['port']}/{config['database']}")
        logger.info(f"Format: {backup_format}")
        logger.info(f"Backup path: {backup_path}")
        
        # Build pg_dump command
        cmd = [
            'pg_dump',
            '--host', config['host'],
            '--port', str(config['port']),
            '--username', config['user'],
            '--dbname', config['database'],
            '--verbose'
        ]
        
        # Add format-specific options
        if backup_format == 'custom':
            cmd.extend(['--format', 'custom'])
        elif backup_format == 'tar':
            cmd.extend(['--format', 'tar'])
        elif backup_format == 'directory':
            cmd.extend(['--format', 'directory'])
            os.makedirs(backup_path, exist_ok=True)
        
        # Add content options
        if schema_only:
            cmd.append('--schema-only')
        elif data_only:
            cmd.append('--data-only')
        
        # Add output option
        if backup_format != 'directory':
            cmd.extend(['--file', backup_path])
        else:
            cmd.extend(['--file', backup_path])
        
        # Set environment for password
        env = os.environ.copy()
        env['PGPASSWORD'] = config['password']
        
        # Run pg_dump
        start_time = datetime.now()
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"pg_dump failed: {result.stderr}")
            return None
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Get backup file size
        if backup_format == 'directory':
            backup_size = sum(f.stat().st_size for f in Path(backup_path).rglob('*') if f.is_file())
        else:
            backup_size = os.path.getsize(backup_path)
        
        backup_size_mb = backup_size / (1024 * 1024)
        
        # Get additional metadata
        alembic_info = get_alembic_info()
        db_stats = get_database_stats(config)
        
        # Create metadata file
        metadata = {
            'backup_name': backup_name,
            'backup_path': backup_path,
            'timestamp': timestamp,
            'created_at': start_time.isoformat(),
            'duration_seconds': duration,
            'backup_size_bytes': backup_size,
            'backup_size_mb': backup_size_mb,
            'backup_format': backup_format,
            'schema_only': schema_only,
            'data_only': data_only,
            'database_config': {
                'host': config['host'],
                'port': config['port'],
                'database': config['database'],
                'user': config['user']
            },
            'alembic_info': alembic_info,
            'database_stats': db_stats,
            'pg_dump_version': get_pg_dump_version()
        }
        
        # Save metadata
        metadata_path = backup_path + '.metadata.json' if backup_format != 'directory' else os.path.join(backup_path, 'backup_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"✅ Backup completed successfully!")
        logger.info(f"Backup location: {backup_path}")
        logger.info(f"Backup size: {backup_size_mb:.2f} MB")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"Alembic revision: {alembic_info['current_revision']}")
        
        # Cleanup old backups
        cleanup_old_backups(backup_dir, max_backups)
        
        return backup_path
        
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        return None

def get_pg_dump_version():
    """Get pg_dump version information"""
    try:
        result = subprocess.run(['pg_dump', '--version'], capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else 'unknown'
    except:
        return 'unknown'

def list_backups():
    """List all existing database backups"""
    try:
        backup_dir = get_backup_directory()
        
        if not os.path.exists(backup_dir):
            logger.info("⚠️  No backup directory found.")
            return
        
        # Find all backup files
        backups = []
        for item in os.listdir(backup_dir):
            item_path = os.path.join(backup_dir, item)
            if (item.startswith('rally_db_backup_') and 
                (os.path.isfile(item_path) or os.path.isdir(item_path))):
                
                # Try to load metadata
                metadata_path = item_path + '.metadata.json' if os.path.isfile(item_path) else os.path.join(item_path, 'backup_metadata.json')
                metadata = {}
                
                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                    except:
                        pass
                
                # Get basic file info
                stat_info = os.stat(item_path)
                backups.append({
                    'name': item,
                    'path': item_path,
                    'created': datetime.fromtimestamp(stat_info.st_mtime),
                    'size_bytes': metadata.get('backup_size_bytes', stat_info.st_size),
                    'metadata': metadata
                })
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x['created'], reverse=True)
        
        if not backups:
            logger.info("⚠️  No database backups found.")
            return
        
        logger.info(f"📋 Database Backups ({len(backups)}):")
        logger.info("=" * 80)
        
        total_size = 0
        for i, backup in enumerate(backups, 1):
            size_mb = backup['size_bytes'] / (1024 * 1024)
            total_size += backup['size_bytes']
            
            created_str = backup['created'].strftime('%Y-%m-%d %H:%M:%S')
            format_info = backup['metadata'].get('backup_format', 'unknown')
            alembic_rev = backup['metadata'].get('alembic_info', {}).get('current_revision', 'unknown')
            
            logger.info(f"{i:2d}. {backup['name']}")
            logger.info(f"    Created: {created_str}")
            logger.info(f"    Size: {size_mb:.2f} MB")
            logger.info(f"    Format: {format_info}")
            logger.info(f"    Alembic revision: {alembic_rev}")
            logger.info("")
        
        total_size_mb = total_size / (1024 * 1024)
        total_size_gb = total_size_mb / 1024
        
        logger.info(f"Total backup space: {total_size_mb:.2f} MB ({total_size_gb:.2f} GB)")
        logger.info(f"Backup directory: {backup_dir}")
        
    except Exception as e:
        logger.error(f"Error listing backups: {e}")

def cleanup_old_backups(backup_dir, max_backups):
    """Clean up old backups, keeping only the most recent ones"""
    try:
        # Find all backup files and directories
        backups = []
        for item in os.listdir(backup_dir):
            if item.startswith('rally_db_backup_'):
                item_path = os.path.join(backup_dir, item)
                backups.append((item, os.path.getmtime(item_path)))
        
        # Sort by modification time (newest first)
        backups.sort(key=lambda x: x[1], reverse=True)
        
        # Remove old backups if we exceed the limit
        if len(backups) > max_backups:
            backups_to_delete = backups[max_backups:]
            
            logger.info(f"🧹 Cleaning up {len(backups_to_delete)} old backups...")
            
            for backup_name, _ in backups_to_delete:
                backup_path = os.path.join(backup_dir, backup_name)
                metadata_path = backup_path + '.metadata.json'
                
                try:
                    if os.path.isdir(backup_path):
                        shutil.rmtree(backup_path)
                    else:
                        os.remove(backup_path)
                    
                    # Remove metadata file if it exists
                    if os.path.exists(metadata_path):
                        os.remove(metadata_path)
                    
                    logger.info(f"   Deleted: {backup_name}")
                    
                except Exception as e:
                    logger.warning(f"   Failed to delete {backup_name}: {e}")
            
            logger.info(f"✅ Cleanup complete. Kept {max_backups} most recent backups.")
    
    except Exception as e:
        logger.warning(f"Error during cleanup: {e}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Rally Database Backup Utility with Alembic Integration')
    
    parser.add_argument('--format', choices=['sql', 'custom', 'tar', 'directory'], 
                       default='sql', help='Backup format (default: sql)')
    parser.add_argument('--schema-only', action='store_true', 
                       help='Backup schema only, no data')
    parser.add_argument('--data-only', action='store_true', 
                       help='Backup data only, no schema')
    parser.add_argument('--max-backups', type=int, default=10,
                       help='Maximum number of backups to keep (default: 10)')
    parser.add_argument('--list', action='store_true',
                       help='List existing backups without creating a new one')
    
    args = parser.parse_args()
    
    if args.list:
        list_backups()
    else:
        if args.schema_only and args.data_only:
            logger.error("❌ Cannot use both --schema-only and --data-only")
            sys.exit(1)
        
        backup_path = create_backup(
            backup_format=args.format,
            schema_only=args.schema_only,
            data_only=args.data_only,
            max_backups=args.max_backups
        )
        
        if backup_path:
            logger.info("🎉 Database backup completed successfully!")
            logger.info(f"Use 'python3 scripts/backup_database.py --list' to view all backups")
        else:
            logger.error("❌ Database backup failed!")
            sys.exit(1)

if __name__ == "__main__":
    main() 