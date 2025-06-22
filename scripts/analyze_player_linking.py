#!/usr/bin/env python3

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))
from database_utils import execute_query, execute_query_one

print("🔗 ANALYZING PLAYER & PLAYER_HISTORY LINKING")
print("=" * 70)

# 1. Confirm the foreign key relationship
print("1. Confirming foreign key constraints:")
fk_query = """
    SELECT 
        tc.constraint_name,
        tc.table_name, 
        kcu.column_name, 
        ccu.table_name AS foreign_table_name,
        ccu.column_name AS foreign_column_name 
    FROM 
        information_schema.table_constraints AS tc 
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY' 
    AND tc.table_name = 'player_history'
"""
foreign_keys = execute_query(fk_query)
for fk in foreign_keys:
    print(
        f"   {fk['constraint_name']}: {fk['table_name']}.{fk['column_name']} → {fk['foreign_table_name']}.{fk['foreign_column_name']}"
    )

# 2. Analyze the data mismatch
print(f"\n2. Data population analysis:")

# Count records in each table
players_count_query = "SELECT COUNT(*) as count FROM players"
history_count_query = "SELECT COUNT(*) as count FROM player_history"
linked_count_query = (
    "SELECT COUNT(*) as count FROM player_history WHERE player_id IS NOT NULL"
)

players_count = execute_query_one(players_count_query)["count"]
history_count = execute_query_one(history_count_query)["count"]
linked_count = execute_query_one(linked_count_query)["count"]

print(f"   Players table: {players_count:,} records")
print(f"   Player_history table: {history_count:,} records")
print(f"   Linked records (non-NULL player_id): {linked_count:,} records")
print(
    f"   Unlinked records: {history_count - linked_count:,} records ({((history_count - linked_count) / history_count * 100):.1f}%)"
)

# 3. Analyze potential linking strategies
print(f"\n3. Analyzing potential linking strategies:")

# Strategy A: Link by series name
print(f"\n   Strategy A: Link by series name")
series_match_query = """
    SELECT 
        s.name as series_name,
        COUNT(p.id) as players_in_series,
        COUNT(DISTINCT ph.series) as history_series_variants
    FROM series s
    LEFT JOIN players p ON p.series_id = s.id
    LEFT JOIN player_history ph ON (
        ph.series = s.name OR 
        ph.series = REPLACE(s.name, ' ', ': ') OR
        ph.series LIKE '%' || s.name || '%'
    )
    WHERE s.name IS NOT NULL
    GROUP BY s.name
    HAVING COUNT(p.id) > 0
    ORDER BY COUNT(p.id) DESC
    LIMIT 10
"""
series_matches = execute_query(series_match_query)
if series_matches:
    print(f"     Top series with players:")
    for match in series_matches:
        print(
            f"       {match['series_name']}: {match['players_in_series']} players, {match['history_series_variants']} history variants"
        )

# Strategy B: Link by PTI value correlation
print(f"\n   Strategy B: Link by PTI value correlation")
pti_correlation_query = """
    SELECT 
        p.id as player_id,
        p.first_name,
        p.last_name,
        p.pti as current_pti,
        s.name as series_name,
        COUNT(ph.id) as matching_history_records
    FROM players p
    LEFT JOIN series s ON p.series_id = s.id
    LEFT JOIN player_history ph ON (
        ph.end_pti = p.pti AND
        (ph.series = s.name OR ph.series = REPLACE(s.name, ' ', ': '))
    )
    WHERE p.pti IS NOT NULL
    GROUP BY p.id, p.first_name, p.last_name, p.pti, s.name
    HAVING COUNT(ph.id) > 0
    ORDER BY COUNT(ph.id) DESC
    LIMIT 10
"""
pti_correlations = execute_query(pti_correlation_query)
if pti_correlations:
    print(f"     Players with PTI matches in history:")
    for corr in pti_correlations:
        print(
            f"       {corr['first_name']} {corr['last_name']} (PTI: {corr['current_pti']}): {corr['matching_history_records']} history records"
        )

# 4. Deep dive into a specific case (Ross)
print(f"\n4. Case study: Ross Freedman linking analysis")
ross_analysis_query = """
    SELECT 
        p.id,
        p.first_name,
        p.last_name,
        p.pti,
        p.tenniscores_player_id,
        s.name as series_name,
        s.id as series_id
    FROM players p
    LEFT JOIN series s ON p.series_id = s.id
    WHERE p.tenniscores_player_id = 'nndz-WkMrK3didjlnUT09'
"""
ross_data = execute_query_one(ross_analysis_query)

if ross_data:
    print(f"   Ross's player record:")
    print(f"     ID: {ross_data['id']}")
    print(f"     PTI: {ross_data['pti']}")
    print(f"     Series: {ross_data['series_name']} (ID: {ross_data['series_id']})")

    # Find potential history matches
    print(f"\n   Potential player_history matches:")

    # Exact PTI matches
    exact_pti_query = """
        SELECT 
            id,
            date,
            end_pti,
            series,
            TO_CHAR(date, 'YYYY-MM-DD') as formatted_date
        FROM player_history
        WHERE end_pti = %s
        ORDER BY date DESC
        LIMIT 5
    """
    exact_matches = execute_query(exact_pti_query, [ross_data["pti"]])

    if exact_matches:
        print(f"     Exact PTI matches ({ross_data['pti']}):")
        for match in exact_matches:
            print(
                f"       ID {match['id']}: {match['formatted_date']} - Series: {match['series']}"
            )

    # Series name matches
    series_variants = [
        ross_data["series_name"],
        ross_data["series_name"].replace(" ", ": "),
        f"%{ross_data['series_name']}%",
    ]

    for variant in series_variants:
        series_query = """
            SELECT 
                id,
                date,
                end_pti,
                series,
                TO_CHAR(date, 'YYYY-MM-DD') as formatted_date
            FROM player_history
            WHERE series ILIKE %s
            ORDER BY date DESC
            LIMIT 3
        """
        series_matches = execute_query(series_query, [variant])

        if series_matches:
            print(f"     Series matches for '{variant}':")
            for match in series_matches:
                print(
                    f"       ID {match['id']}: {match['formatted_date']} - PTI: {match['end_pti']}"
                )

# 5. Propose concrete fixing strategies
print(f"\n5. Proposed data fixing strategies:")

print(f"\n   Strategy 1: Exact PTI + Series matching")
print(f"   - Link records where player.pti exactly matches player_history.end_pti")
print(f"   - AND series names match (with variant handling)")
print(f"   - Most reliable for recent data")

print(f"\n   Strategy 2: Series-based bulk linking")
print(f"   - For each series, distribute history records among players")
print(f"   - Use chronological order and PTI proximity")
print(f"   - Good for historical data")

print(f"\n   Strategy 3: Match-date correlation")
print(f"   - Link based on match dates from match_scores table")
print(f"   - Find player_history records near match dates")
print(f"   - Most accurate but complex")

# 6. Generate specific SQL for Ross
print(f"\n6. Specific fix for Ross Freedman:")
if ross_data and exact_matches:
    print(f"   Recommended linkage:")
    best_match = exact_matches[0]  # Most recent exact PTI match

    print(
        f"     Link player_history.id = {best_match['id']} to players.id = {ross_data['id']}"
    )
    print(
        f"     Record: {best_match['formatted_date']} - PTI: {best_match['end_pti']} - Series: {best_match['series']}"
    )

    print(f"\n   SQL command:")
    print(f"   UPDATE player_history")
    print(f"   SET player_id = {ross_data['id']}")
    print(f"   WHERE id = {best_match['id']};")

    # Also link other exact PTI matches for this player
    print(f"\n   Link all exact PTI matches:")
    print(f"   UPDATE player_history")
    print(f"   SET player_id = {ross_data['id']}")
    print(f"   WHERE end_pti = {ross_data['pti']}")
    print(f"   AND series IN ('Chicago 22', 'Chicago: 22');")

print(f"\n💡 RECOMMENDATION:")
print(f"   Start with Strategy 1 (Exact PTI + Series) for high-confidence links")
print(f"   This will establish the linking pattern and validate the approach")
print(f"   Then expand to other strategies for remaining records")
