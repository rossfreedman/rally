import openai
from config import OPENAI_API_KEY
import pandas as pd
from datetime import datetime
import os

def get_lineup_suggestion(available_players, series):
    # Read match results and player stats from Data folder
    match_results_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'match_scores_20250415.csv')
    player_stats_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'all_tennaqua_players.csv')
    
    try:
        # Read both CSVs
        matches_df = pd.read_csv(match_results_file)
        players_df = pd.read_csv(player_stats_file)
        
        # Filter player stats for only available players
        available_stats = players_df[players_df['First Name'].astype(str) + ' ' + 
                                   players_df['Last Name'].astype(str).isin(available_players)]
        
        # Convert to string representations
        recent_matches = matches_df.to_string()
        player_stats = available_stats.to_string()
    except Exception as e:
        print(f"Error reading CSV files: {str(e)}")
        recent_matches = "No recent match data available"
        player_stats = "No player stats available"

    # Construct the prompt
    prompt = f"""Based on these recent match results:
{recent_matches}

And these player statistics:
{player_stats}

For these available players in Series {series}:
{available_players}

Please suggest an optimal lineup considering:
1. Player PTI ratings and win percentages
2. Recent performance in matches
3. Player chemistry from past matches
4. Series level matchups

Format your response as:
Line 1:
[Player 1 Name] / [Player 2 Name] - [Brief explanation of pairing]
Line 2:
[Player 3 Name] / [Player 4 Name] - [Brief explanation of pairing]
Line 3:
[Player 5 Name] / [Player 6 Name] - [Brief explanation of pairing]

Include a brief strategic explanation for each pairing based on the data provided.
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a paddle tennis lineup expert. You analyze match history and player statistics to create optimal lineups."},
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating lineup: {str(e)}" 