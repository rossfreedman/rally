#!/usr/bin/env python3
"""
Import APTA Chicago players with career stats to staging database
"""

import sys
import os
sys.path.append('.')

# Set staging database environment
os.environ['DATABASE_URL'] = 'postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway'

print('=== RUNNING APTA CHICAGO PLAYERS IMPORT FOR CAREER STATS ===')
print()

try:
    from data.etl.import.import_players import import_players
    
    print('Starting APTA Chicago players import...')
    result = import_players('APTA_CHICAGO')
    print(f'Import result: {result}')
    print('✅ APTA Chicago players import completed successfully')
    
except Exception as e:
    print(f'❌ Error during import: {e}')
    import traceback
    traceback.print_exc()
