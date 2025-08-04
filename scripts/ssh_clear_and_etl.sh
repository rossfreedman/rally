#!/bin/bash
"""
SSH Script to Clear Match Scores and Run ETL on Staging
=======================================================

This script connects to the staging server via SSH and:
1. Clears the match_scores table to remove duplicates
2. Runs the ETL import to get clean data
3. Verifies the fix
"""

echo "🚀 Starting staging database cleanup via SSH..."

# SSH into staging server and run commands
ssh rally-staging.up.railway.app << 'EOF'

echo "📊 Checking current match_scores count..."
psql $DATABASE_URL -c "SELECT COUNT(*) FROM match_scores;"

echo "🗑️  Clearing match_scores table..."
psql $DATABASE_URL -c "DELETE FROM match_scores;"

echo "✅ Match scores cleared. Running ETL import..."

# Run the ETL import
cd /app
python data/etl/database_import/import_all_jsons_to_database.py

echo "📊 Checking final match_scores count..."
psql $DATABASE_URL -c "SELECT COUNT(*) FROM match_scores;"

echo "🔍 Checking Ross Freedman's matches..."
psql $DATABASE_URL -c "
SELECT 
    p.first_name,
    p.last_name,
    p.tenniscores_player_id,
    COUNT(ms.id) as total_matches,
    COUNT(CASE WHEN ms.match_date >= '2024-08-01' AND ms.match_date <= '2025-03-31' THEN 1 END) as current_season_matches
FROM players p
LEFT JOIN match_scores ms ON (
    ms.home_player_1_id = p.tenniscores_player_id OR 
    ms.home_player_2_id = p.tenniscores_player_id OR 
    ms.away_player_1_id = p.tenniscores_player_id OR 
    ms.away_player_2_id = p.tenniscores_player_id
)
WHERE p.first_name = 'Ross' AND p.last_name = 'Freedman'
GROUP BY p.id, p.first_name, p.last_name, p.tenniscores_player_id
ORDER BY total_matches DESC;
"

echo "✅ Staging database cleanup completed!"
echo "🌐 Check https://rally-staging.up.railway.app/mobile/analyze-me to verify the fix"

EOF

echo "✅ SSH commands completed!" 