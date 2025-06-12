#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
from database_utils import execute_query, execute_query_one

print("🔍 INVESTIGATING PTI DATA LINKING")
print("=" * 60)

# 1. Check player_history table structure
print("1. Checking player_history table structure:")
schema_query = '''
    SELECT column_name, data_type, is_nullable 
    FROM information_schema.columns 
    WHERE table_name = 'player_history' 
    ORDER BY ordinal_position
'''
columns = execute_query(schema_query)
for col in columns:
    print(f"   {col['column_name']:15} {col['data_type']:15} {'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'}")

# 2. Check sample player_history records
print(f"\n2. Sample player_history records:")
sample_query = '''
    SELECT * FROM player_history 
    WHERE player_id IS NOT NULL 
    ORDER BY date DESC 
    LIMIT 5
'''
sample_records = execute_query(sample_query)
if sample_records:
    for i, record in enumerate(sample_records):
        print(f"   Record {i+1}: player_id={record.get('player_id')}, date={record.get('date')}, end_pti={record.get('end_pti')}")
else:
    print("   No records with non-null player_id found!")

# 3. Check if there's a different player identifier being used
print(f"\n3. Checking for alternative player identifiers:")
alt_columns_query = '''
    SELECT DISTINCT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'player_history' 
    AND column_name ILIKE '%player%'
'''
alt_columns = execute_query(alt_columns_query)
for col in alt_columns:
    print(f"   Found column: {col['column_name']}")

# 4. Check records by different criteria
print(f"\n4. Checking records by different criteria:")

# Check for records with NULL player_id but other identifiers
null_player_query = '''
    SELECT COUNT(*) as count FROM player_history WHERE player_id IS NULL
'''
null_count = execute_query_one(null_player_query)
print(f"   Records with NULL player_id: {null_count['count']}")

# Check for records with player_id
not_null_player_query = '''
    SELECT COUNT(*) as count FROM player_history WHERE player_id IS NOT NULL
'''
not_null_count = execute_query_one(not_null_player_query)
print(f"   Records with non-NULL player_id: {not_null_count['count']}")

# 5. Try to find Ross's data by looking for similar patterns
print(f"\n5. Looking for Ross Freedman's data:")

# Check if there are records that might belong to Ross but with different linking
ross_search_query = '''
    SELECT ph.*, p.first_name, p.last_name, p.tenniscores_player_id
    FROM player_history ph
    LEFT JOIN players p ON ph.player_id = p.id
    WHERE p.first_name = 'Ross' AND p.last_name = 'Freedman'
    ORDER BY ph.date DESC
    LIMIT 5
'''
ross_records = execute_query(ross_search_query)
if ross_records:
    print(f"   Found {len(ross_records)} records for Ross:")
    for record in ross_records:
        print(f"     Date: {record['date']}, PTI: {record.get('end_pti')}")
else:
    print("   No records found by name join")

# 6. Check if there might be a different player table being used
print(f"\n6. Looking for alternative player data sources:")

# Check all tables that might contain player information
tables_query = '''
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_name ILIKE '%player%' 
    AND table_schema = 'public'
'''
tables = execute_query(tables_query)
for table in tables:
    print(f"   Table: {table['table_name']}")

# 7. Check if PTI data might be in the raw match data somehow
print(f"\n7. Checking for PTI in other locations:")
pti_columns_query = '''
    SELECT table_name, column_name 
    FROM information_schema.columns 
    WHERE column_name ILIKE '%pti%'
    ORDER BY table_name, column_name
'''
pti_columns = execute_query(pti_columns_query)
if pti_columns:
    for col in pti_columns:
        print(f"   {col['table_name']}.{col['column_name']}")
else:
    print("   No PTI columns found in other tables")

# 8. Check the specific range of dates for recent data
print(f"\n8. Checking recent player_history data:")
recent_query = '''
    SELECT date, COUNT(*) as records
    FROM player_history 
    WHERE date >= '2024-01-01'
    GROUP BY date
    ORDER BY date DESC
    LIMIT 10
'''
recent_data = execute_query(recent_query)
if recent_data:
    print("   Recent dates with PTI data:")
    for row in recent_data:
        print(f"     {row['date']}: {row['records']} records")
else:
    print("   No recent PTI data found") 