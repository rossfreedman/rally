#!/usr/bin/env python3
"""
Manual Staging Reset - Fixed for Railway
========================================
Simple reset script that only clears essential tables for staging ETL.
"""
import sys
import os
sys.path.append('/opt/render/project/src')
from database_config import get_db

print('=== MANUAL STAGING RESET ===')
with get_db() as conn:
    with conn.cursor() as cursor:
        try:
            # Step 1: Null players.team_id (this is safe)
            cursor.execute('UPDATE players SET team_id = NULL WHERE team_id IS NOT NULL')
            print('✓ Nulled players.team_id')
            
            # Step 2: Clear season tables
            tables = ['match_scores', 'schedule', 'series_stats', 'saved_lineups', 'captain_messages', 'poll_responses', 'poll_choices', 'polls', 'team_mapping_backup']
            for table in tables:
                try:
                    cursor.execute(f'DELETE FROM {table}')
                    rows = cursor.rowcount
                    print(f'✓ Cleared {table} ({rows} rows)')
                except Exception as e:
                    print(f'⚠ Skipped {table}: {e}')
            
            # Step 3: Delete teams
            cursor.execute('DELETE FROM teams')
            teams_deleted = cursor.rowcount
            print(f'✓ Deleted {teams_deleted} teams')
            
            conn.commit()
            print('🎉 STAGING RESET COMPLETE!')
            print('✅ Ready for fresh ETL import')
            
        except Exception as e:
            print(f'❌ Reset failed: {e}')
            conn.rollback()
            raise
