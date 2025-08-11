#!/usr/bin/env python3
"""
Fix Lisa Wagner's team assignment to Tennaqua 12
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Get database URL from Railway environment
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    print("🔗 Connecting to staging database...")
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    cursor = conn.cursor()
    
    print("=== FIXING LISA WAGNER TEAM ASSIGNMENT ===")
    
    # Check Lisa's current assignment
    cursor.execute("""
        SELECT p.id, p.first_name, p.last_name, p.team_id, p.club_id, p.series_id
        FROM players p
        WHERE p.tenniscores_player_id = 'cnswpl_2070e1ed22049df7'
    """)
    lisa_before = cursor.fetchone()
    print(f"Before: Lisa Wagner - team_id: {lisa_before['team_id']}, club_id: {lisa_before['club_id']}, series_id: {lisa_before['series_id']}")
    
    # Get Tennaqua 12 team info
    cursor.execute("""
        SELECT t.id, t.team_name, t.club_id, t.series_id
        FROM teams t
        WHERE t.id = 52638
    """)
    tennaqua12 = cursor.fetchone()
    print(f"Tennaqua 12 team: ID {tennaqua12['id']}, club_id: {tennaqua12['club_id']}, series_id: {tennaqua12['series_id']}")
    
    # Update Lisa's team assignment
    cursor.execute("""
        UPDATE players 
        SET team_id = %s, club_id = %s, series_id = %s
        WHERE tenniscores_player_id = 'cnswpl_2070e1ed22049df7'
    """, [tennaqua12['id'], tennaqua12['club_id'], tennaqua12['series_id']])
    
    # Verify the update
    cursor.execute("""
        SELECT p.id, p.first_name, p.last_name, p.team_id, p.club_id, p.series_id
        FROM players p
        WHERE p.tenniscores_player_id = 'cnswpl_2070e1ed22049df7'
    """)
    lisa_after = cursor.fetchone()
    print(f"After: Lisa Wagner - team_id: {lisa_after['team_id']}, club_id: {lisa_after['club_id']}, series_id: {lisa_after['series_id']}")
    
    conn.commit()
    conn.close()
    print("✅ Lisa Wagner team assignment updated successfully")
else:
    print("❌ DATABASE_URL not found")
