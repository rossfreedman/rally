#!/usr/bin/env python3
"""
Comprehensive validation of career stats import
"""

import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db

def main():
    print('🔍 COMPREHENSIVE CAREER STATS VALIDATION')
    print('=' * 60)
    
    # Load updated players.json
    with open('data/leagues/APTA_CHICAGO/players.json', 'r') as f:
        json_players = json.load(f)
    
    print(f'📊 JSON file: {len(json_players):,} players')
    
    # Connect to database
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get database players
        cursor.execute('''
            SELECT p.tenniscores_player_id, p.first_name, p.last_name, 
                   p.career_wins, p.career_losses, p.career_win_percentage,
                   p.captain_status, p.pti
            FROM players p 
            JOIN leagues l ON p.league_id = l.id 
            WHERE l.league_name = 'APTA Chicago'
            ORDER BY p.career_wins DESC NULLS LAST
        ''')
        db_players = cursor.fetchall()
    
    print(f'📊 Database: {len(db_players):,} players')
    
    # Create lookup for JSON players
    json_lookup = {}
    for player in json_players:
        player_id = player.get('Player ID')
        if player_id:
            json_lookup[player_id] = player
    
    print(f'📊 JSON lookup: {len(json_lookup):,} players')
    
    # Validation statistics
    matched_players = 0
    career_stats_matches = 0
    captain_matches = 0
    pti_matches = 0
    
    career_wins_discrepancies = []
    captain_discrepancies = []
    pti_discrepancies = []
    
    print('\n🔄 VALIDATING PLAYER DATA...')
    
    for db_player in db_players:
        player_id, first_name, last_name, db_wins, db_losses, db_win_pct, db_captain, db_pti = db_player
        
        if player_id in json_lookup:
            matched_players += 1
            json_player = json_lookup[player_id]
            
            # Check career stats
            json_wins = json_player.get('Career Wins', 0)
            json_losses = json_player.get('Career Losses', 0)
            json_win_pct_str = json_player.get('Career Win %', '0.0%')
            
            # Parse win percentage
            try:
                json_win_pct = float(json_win_pct_str.replace('%', ''))
            except:
                json_win_pct = 0.0
            
            # Check captain status
            json_captain = json_player.get('Captain', 'No')
            db_captain_str = 'Yes' if db_captain == 'Yes' else 'No'
            
            # Check PTI
            json_pti_str = json_player.get('PTI', '0')
            try:
                json_pti = float(json_pti_str)
            except:
                json_pti = 0.0
            
            # Compare career stats
            if (int(json_wins) == int(db_wins) if db_wins else 0 and 
                int(json_losses) == int(db_losses) if db_losses else 0):
                career_stats_matches += 1
            else:
                career_wins_discrepancies.append({
                    'name': f'{first_name} {last_name}',
                    'id': player_id,
                    'json': f'{json_wins}W-{json_losses}L',
                    'db': f'{db_wins}W-{db_losses}L'
                })
            
            # Compare captain status
            if json_captain == db_captain_str:
                captain_matches += 1
            else:
                captain_discrepancies.append({
                    'name': f'{first_name} {last_name}',
                    'id': player_id,
                    'json': json_captain,
                    'db': db_captain_str
                })
            
            # Compare PTI (with small tolerance for floating point)
            db_pti_float = float(db_pti) if db_pti else 0.0
            if abs(json_pti - db_pti_float) < 0.1:
                pti_matches += 1
            else:
                pti_discrepancies.append({
                    'name': f'{first_name} {last_name}',
                    'id': player_id,
                    'json': json_pti,
                    'db': db_pti
                })
    
    # Print validation results
    print(f'\n📊 VALIDATION RESULTS:')
    print(f'   Matched players: {matched_players:,} / {len(db_players):,}')
    print(f'   Career stats matches: {career_stats_matches:,} / {matched_players:,}')
    print(f'   Captain status matches: {captain_matches:,} / {matched_players:,}')
    print(f'   PTI matches: {pti_matches:,} / {matched_players:,}')
    
    # Show discrepancies
    if career_wins_discrepancies:
        print(f'\n⚠️  CAREER WINS DISCREPANCIES ({len(career_wins_discrepancies)}):')
        for disc in career_wins_discrepancies[:5]:
            name = disc["name"]
            json_val = disc["json"]
            db_val = disc["db"]
            print(f'   {name}: JSON={json_val}, DB={db_val}')
        if len(career_wins_discrepancies) > 5:
            print(f'   ... and {len(career_wins_discrepancies) - 5} more')
    
    if captain_discrepancies:
        print(f'\n⚠️  CAPTAIN STATUS DISCREPANCIES ({len(captain_discrepancies)}):')
        for disc in captain_discrepancies[:5]:
            name = disc["name"]
            json_val = disc["json"]
            db_val = disc["db"]
            print(f'   {name}: JSON={json_val}, DB={db_val}')
        if len(captain_discrepancies) > 5:
            print(f'   ... and {len(captain_discrepancies) - 5} more')
    
    if pti_discrepancies:
        print(f'\n⚠️  PTI DISCREPANCIES ({len(pti_discrepancies)}):')
        for disc in pti_discrepancies[:5]:
            name = disc["name"]
            json_val = disc["json"]
            db_val = disc["db"]
            print(f'   {name}: JSON={json_val}, DB={db_val}')
        if len(pti_discrepancies) > 5:
            print(f'   ... and {len(pti_discrepancies) - 5} more')
    
    # Overall assessment
    total_checks = matched_players * 3  # career stats, captain, PTI
    total_matches = career_stats_matches + captain_matches + pti_matches
    match_percentage = (total_matches / total_checks * 100) if total_checks > 0 else 0
    
    print(f'\n🎯 OVERALL ASSESSMENT:')
    print(f'   Data consistency: {match_percentage:.1f}%')
    
    if match_percentage >= 95:
        print('   ✅ EXCELLENT - Data is highly consistent')
    elif match_percentage >= 90:
        print('   ✅ GOOD - Data is mostly consistent')
    elif match_percentage >= 80:
        print('   ⚠️  FAIR - Some discrepancies found')
    else:
        print('   ❌ POOR - Significant discrepancies found')
    
    # Show top career winners from database
    print(f'\n🏆 TOP CAREER WINNERS IN DATABASE:')
    for i, db_player in enumerate(db_players[:10]):
        player_id, first_name, last_name, db_wins, db_losses, db_win_pct, db_captain, db_pti = db_player
        if db_wins and db_wins > 0:
            print(f'   {i+1}. {first_name} {last_name}: {db_wins}W-{db_losses}L ({db_win_pct:.1f}%) - Captain: {db_captain}')

if __name__ == "__main__":
    main()