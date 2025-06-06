#!/usr/bin/env python3
"""
PTI vs Opponent Analysis Scatter Plot

This script analyzes a paddle tennis player's match results relative to their opponents' average PTI.
It creates a scatter plot showing the relationship between opponent strength and player performance.
Uses Plotly for consistency with existing Rally app charts.
"""

import json
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import argparse

def load_json_data(filepath: str) -> List[Dict]:
    """Load JSON data from file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File {filepath} not found")
        return []
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {filepath}")
        return []

def parse_date(date_str: str) -> datetime:
    """Parse date string into datetime object."""
    # Handle different date formats
    formats = ['%m/%d/%Y', '%d-%b-%y', '%Y-%m-%d']
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # If no format matches, try to parse manually
    print(f"Warning: Could not parse date: {date_str}")
    return None

def find_player_in_players_json(players_data: List[Dict], player_name: str) -> Optional[float]:
    """Find a player's PTI in the players.json data."""
    full_name = player_name.strip()
    
    for player in players_data:
        first_name = player.get('First Name', '').strip()
        last_name = player.get('Last Name', '').strip()
        player_full_name = f"{first_name} {last_name}".strip()
        
        if player_full_name == full_name:
            pti_str = player.get('PTI', '0')
            try:
                return float(pti_str)
            except (ValueError, TypeError):
                return None
    
    return None

def get_opponents_from_match(match: Dict, target_player: str) -> List[str]:
    """Extract opponent names from a match record."""
    opponents = []
    
    home_player_1 = match.get('Home Player 1', '').strip()
    home_player_2 = match.get('Home Player 2', '').strip()
    away_player_1 = match.get('Away Player 1', '').strip()
    away_player_2 = match.get('Away Player 2', '').strip()
    
    all_players = [home_player_1, home_player_2, away_player_1, away_player_2]
    
    # Find which team the target player is on
    target_on_home = target_player in [home_player_1, home_player_2]
    target_on_away = target_player in [away_player_1, away_player_2]
    
    if target_on_home:
        # Target is on home team, opponents are away team
        opponents = [away_player_1, away_player_2]
    elif target_on_away:
        # Target is on away team, opponents are home team
        opponents = [home_player_1, home_player_2]
    
    # Filter out empty names
    opponents = [opp for opp in opponents if opp]
    
    return opponents

def determine_match_result(match: Dict, target_player: str) -> str:
    """Determine if the target player won or lost the match."""
    home_player_1 = match.get('Home Player 1', '').strip()
    home_player_2 = match.get('Home Player 2', '').strip()
    away_player_1 = match.get('Away Player 1', '').strip()
    away_player_2 = match.get('Away Player 2', '').strip()
    
    winner = match.get('Winner', '').lower()
    
    target_on_home = target_player in [home_player_1, home_player_2]
    target_on_away = target_player in [away_player_1, away_player_2]
    
    if target_on_home and winner == 'home':
        return 'win'
    elif target_on_away and winner == 'away':
        return 'win'
    else:
        return 'loss'

def create_scatter_plot_data(player_name: str, data_dir: str = 'data') -> pd.DataFrame:
    """Create the data structure for the scatter plot."""
    
    # Load data files
    print(f"Loading data for {player_name}...")
    player_history = load_json_data(f'{data_dir}/player_history.json')
    match_history = load_json_data(f'{data_dir}/match_history.json')
    players_data = load_json_data(f'{data_dir}/players.json')
    
    if not all([player_history, match_history, players_data]):
        print("Error: Could not load all required data files")
        return pd.DataFrame()
    
    # Find the target player's history
    target_player_history = None
    for player in player_history:
        if player.get('name') == player_name:
            target_player_history = player
            break
    
    if not target_player_history:
        print(f"Error: Could not find {player_name} in player history")
        return pd.DataFrame()
    
    matches = target_player_history.get('matches', [])
    print(f"Found {len(matches)} matches for {player_name}")
    
    # Build the scatter plot data
    scatter_data = []
    
    for match in matches:
        match_date_str = match.get('date')
        player_end_pti = match.get('end_pti')
        
        if not match_date_str or player_end_pti is None:
            continue
        
        match_date = parse_date(match_date_str)
        if not match_date:
            continue
        
        # Find corresponding match in match_history
        # Convert date format for matching
        match_date_formatted = match_date.strftime('%d-%b-%y').lower()
        
        corresponding_match = None
        for hist_match in match_history:
            hist_date = hist_match.get('Date', '').lower()
            if hist_date == match_date_formatted:
                # Check if target player is in this match
                all_players = [
                    hist_match.get('Home Player 1', ''),
                    hist_match.get('Home Player 2', ''),
                    hist_match.get('Away Player 1', ''),
                    hist_match.get('Away Player 2', '')
                ]
                if player_name in all_players:
                    corresponding_match = hist_match
                    break
        
        if not corresponding_match:
            print(f"Warning: Could not find match record for {player_name} on {match_date_str}")
            continue
        
        # Get opponents
        opponents = get_opponents_from_match(corresponding_match, player_name)
        if len(opponents) < 2:
            print(f"Warning: Could not find 2 opponents for match on {match_date_str}")
            continue
        
        # Get opponent PTIs
        opponent_ptis = []
        for opponent in opponents:
            opponent_pti = find_player_in_players_json(players_data, opponent)
            if opponent_pti is not None:
                opponent_ptis.append(opponent_pti)
        
        if len(opponent_ptis) < 2:
            print(f"Warning: Could not find PTI for all opponents on {match_date_str}")
            continue
        
        # Calculate average opponent PTI
        opponent_avg_pti = sum(opponent_ptis) / len(opponent_ptis)
        
        # Determine match result
        match_result = determine_match_result(corresponding_match, player_name)
        
        # Add to scatter data
        scatter_data.append({
            'match_date': match_date,
            'match_date_str': match_date_str,
            'player_end_pti': player_end_pti,
            'opponent_avg_pti': opponent_avg_pti,
            'match_result': match_result,
            'opponent_names': ', '.join(opponents),
            'opponent_ptis': opponent_ptis
        })
    
    df = pd.DataFrame(scatter_data)
    print(f"Successfully processed {len(df)} matches with complete data")
    return df

def create_scatter_plot(df: pd.DataFrame, player_name: str, save_path: str = None):
    """Create the scatter plot visualization using Plotly."""
    
    if df.empty:
        print("No data to plot")
        return
    
    # Separate wins and losses
    wins = df[df['match_result'] == 'win']
    losses = df[df['match_result'] == 'loss']
    
    # Create the figure
    fig = go.Figure()
    
    # Add wins scatter
    if not wins.empty:
        fig.add_trace(go.Scatter(
            x=wins['opponent_avg_pti'],
            y=wins['player_end_pti'],
            mode='markers',
            name=f'Wins ({len(wins)})',
            marker=dict(
                color='green',
                size=10,
                opacity=0.7,
                line=dict(width=2, color='darkgreen')
            ),
            customdata=wins[['match_date_str', 'opponent_names']],
            hovertemplate=(
                '<b>WIN</b><br>'
                'Date: %{customdata[0]}<br>'
                'Opponents: %{customdata[1]}<br>'
                'Opponent Avg PTI: %{x:.1f}<br>'
                f'{player_name} PTI: %{{y:.1f}}<br>'
                '<extra></extra>'
            )
        ))
    
    # Add losses scatter
    if not losses.empty:
        fig.add_trace(go.Scatter(
            x=losses['opponent_avg_pti'],
            y=losses['player_end_pti'],
            mode='markers',
            name=f'Losses ({len(losses)})',
            marker=dict(
                color='red',
                size=10,
                opacity=0.7,
                line=dict(width=2, color='darkred')
            ),
            customdata=losses[['match_date_str', 'opponent_names']],
            hovertemplate=(
                '<b>LOSS</b><br>'
                'Date: %{customdata[0]}<br>'
                'Opponents: %{customdata[1]}<br>'
                'Opponent Avg PTI: %{x:.1f}<br>'
                f'{player_name} PTI: %{{y:.1f}}<br>'
                '<extra></extra>'
            )
        ))
    
    # Add reference line (45-degree line where player PTI = opponent PTI)
    min_pti = min(df['opponent_avg_pti'].min(), df['player_end_pti'].min())
    max_pti = max(df['opponent_avg_pti'].max(), df['player_end_pti'].max())
    
    fig.add_trace(go.Scatter(
        x=[min_pti, max_pti],
        y=[min_pti, max_pti],
        mode='lines',
        name='Equal PTI Reference',
        line=dict(color='black', width=2, dash='dash'),
        opacity=0.5,
        hoverinfo='skip'
    ))
    
    # Add trend line
    if len(df) > 1:
        z = np.polyfit(df['opponent_avg_pti'], df['player_end_pti'], 1)
        trend_x = df['opponent_avg_pti'].sort_values()
        trend_y = np.polyval(z, trend_x)
        
        fig.add_trace(go.Scatter(
            x=trend_x,
            y=trend_y,
            mode='lines',
            name=f'Trend Line (slope: {z[0]:.2f})',
            line=dict(color='blue', width=3),
            opacity=0.8,
            hoverinfo='skip'
        ))
    
    # Update layout
    fig.update_layout(
        title=dict(
            text=f'{player_name}: Performance vs Opponent Strength<br>'
                 f'<sub>Total: {len(df)} | Wins: {len(wins)} | Losses: {len(losses)} | '
                 f'Win Rate: {len(wins)/len(df)*100:.1f}%</sub>',
            x=0.5,
            font=dict(size=16)
        ),
        xaxis=dict(
            title='Average Opponent PTI',
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray'
        ),
        yaxis=dict(
            title=f'{player_name} End PTI',
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray'
        ),
        plot_bgcolor='white',
        showlegend=True,
        legend=dict(
            x=0.02,
            y=0.98,
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='gray',
            borderwidth=1
        ),
        width=900,
        height=600,
        margin=dict(l=80, r=80, t=100, b=80)
    )
    
    # Add annotations for statistics
    stats_text = (
        f'Avg Player PTI: {df["player_end_pti"].mean():.1f}<br>'
        f'Avg Opponent PTI: {df["opponent_avg_pti"].mean():.1f}<br>'
        f'PTI Range: {df["player_end_pti"].min():.1f} - {df["player_end_pti"].max():.1f}'
    )
    
    fig.add_annotation(
        x=0.98,
        y=0.02,
        xref='paper',
        yref='paper',
        text=stats_text,
        showarrow=False,
        align='right',
        bgcolor='rgba(173, 216, 230, 0.8)',
        bordercolor='gray',
        borderwidth=1,
        font=dict(size=10)
    )
    
    # Save or show the plot
    if save_path:
        if save_path.endswith('.html'):
            fig.write_html(save_path)
        else:
            fig.write_image(save_path, width=900, height=600, scale=2)
        print(f"Plot saved to {save_path}")
    else:
        fig.show()
    
    return fig

def main():
    """Main function to run the analysis."""
    parser = argparse.ArgumentParser(description='Create PTI vs Opponent Analysis Scatter Plot')
    parser.add_argument('--player', default='Daniel Sullivan', help='Player name to analyze')
    parser.add_argument('--data-dir', default='data', help='Directory containing JSON data files')
    parser.add_argument('--save', help='Path to save the plot (optional)')
    
    args = parser.parse_args()
    
    print(f"=== PTI vs Opponent Analysis for {args.player} ===")
    
    # Create the scatter plot data
    df = create_scatter_plot_data(args.player, args.data_dir)
    
    if df.empty:
        print("No data available for analysis")
        return
    
    # Display some sample data
    print("\nSample data:")
    print(df[['match_date_str', 'player_end_pti', 'opponent_avg_pti', 'match_result', 'opponent_names']].head())
    
    # Create and display the plot
    create_scatter_plot(df, args.player, args.save)
    
    # Print summary statistics
    print(f"\n=== Summary Statistics ===")
    print(f"Total matches analyzed: {len(df)}")
    print(f"Wins: {len(df[df['match_result'] == 'win'])}")
    print(f"Losses: {len(df[df['match_result'] == 'loss'])}")
    print(f"Win rate: {len(df[df['match_result'] == 'win'])/len(df)*100:.1f}%")
    print(f"Average player PTI: {df['player_end_pti'].mean():.1f}")
    print(f"Average opponent PTI: {df['opponent_avg_pti'].mean():.1f}")
    print(f"Player PTI range: {df['player_end_pti'].min():.1f} - {df['player_end_pti'].max():.1f}")
    print(f"Opponent PTI range: {df['opponent_avg_pti'].min():.1f} - {df['opponent_avg_pti'].max():.1f}")
    
    # Analysis insights
    wins = df[df['match_result'] == 'win']
    losses = df[df['match_result'] == 'loss']
    
    if not wins.empty and not losses.empty:
        avg_opp_pti_wins = wins['opponent_avg_pti'].mean()
        avg_opp_pti_losses = losses['opponent_avg_pti'].mean()
        
        print(f"\n=== Performance Insights ===")
        print(f"Average opponent PTI in wins: {avg_opp_pti_wins:.1f}")
        print(f"Average opponent PTI in losses: {avg_opp_pti_losses:.1f}")
        
        if avg_opp_pti_wins < avg_opp_pti_losses:
            print("✓ Player tends to win against weaker opponents")
        else:
            print("⚠ Player wins against stronger opponents on average")

if __name__ == "__main__":
    main() 