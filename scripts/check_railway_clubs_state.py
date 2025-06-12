#!/usr/bin/env python3
import psycopg2
from urllib.parse import urlparse

RAILWAY_URL = 'postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway'
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

conn = psycopg2.connect(**conn_params)
cursor = conn.cursor()

print('CURRENT RAILWAY CLUBS:')
cursor.execute('SELECT id, name FROM clubs ORDER BY id')
clubs = cursor.fetchall()
for club_id, name in clubs:
    print(f'  ID {club_id}: {name}')

print(f'\nTOTAL CLUBS: {len(clubs)}')

# Check sequence value
cursor.execute("SELECT last_value FROM clubs_id_seq")
seq_val = cursor.fetchone()[0]
print(f'CLUBS SEQUENCE LAST VALUE: {seq_val}')

# Check max ID
cursor.execute('SELECT MAX(id) FROM clubs')
max_id = cursor.fetchone()[0]
print(f'MAX CLUB ID: {max_id}')

# Check for the specific clubs we want to add
clubs_to_check = ['Wilmette', 'Midtown', 'Ravinia Green', 'Old Willow']
print(f'\nCHECKING FOR TARGET CLUBS:')
for club_name in clubs_to_check:
    cursor.execute("SELECT id FROM clubs WHERE name = %s", (club_name,))
    result = cursor.fetchone()
    if result:
        print(f'  ✅ {club_name}: Already exists (ID: {result[0]})')
    else:
        print(f'  ❌ {club_name}: Missing')

conn.close() 