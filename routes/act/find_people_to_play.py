from flask import jsonify, request, session, render_template
from datetime import datetime
import os
import json
from utils.db import execute_query
from utils.logging import log_user_activity
from utils.auth import login_required

def init_find_people_to_play_routes(app):
    @app.route('/mobile/find-people-to-play')
    @login_required
    def serve_mobile_find_people_to_play():
        """Serve the mobile Find People to Play page"""
        try:
            session_data = {
                'user': session['user'],
                'authenticated': True
            }
            log_user_activity(session['user']['email'], 'page_visit', page='mobile_find_people_to_play')
            return render_template('mobile/find_people_to_play.html', session_data=session_data)
        except Exception as e:
            print(f"Error serving find people to play page: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/club-players')
    @login_required
    def get_club_players():
        """Get all players at the user's club with optional filtering"""
        try:
            # Get user's club from session
            user_club = session['user'].get('club')
            if not user_club:
                return jsonify({'error': 'User club not found'}), 400

            # Get filter parameters
            series_filter = request.args.get('series', '').strip()
            first_name_filter = request.args.get('first_name', '').strip().lower()
            last_name_filter = request.args.get('last_name', '').strip().lower()
            pti_min = request.args.get('pti_min', type=float)
            pti_max = request.args.get('pti_max', type=float)

            print(f"\n=== DEBUG: get_club_players ===")
            print(f"User club: {user_club}")
            print(f"Filters - Series: {series_filter}, First: {first_name_filter}, Last: {last_name_filter}, PTI: {pti_min}-{pti_max}")

            # Load player data
            players_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'players.json')
            with open(players_path, 'r') as f:
                all_players = json.load(f)

            # Calculate PTI range from ALL players in the file (for slider bounds)
            all_pti_values = []
            for player in all_players:
                try:
                    pti_value = float(player['PTI'])
                    all_pti_values.append(pti_value)
                except (ValueError, TypeError):
                    continue
            
            # Set PTI range based on all players in the system
            pti_range = {'min': 0, 'max': 100}
            if all_pti_values:
                pti_range = {
                    'min': min(all_pti_values),
                    'max': max(all_pti_values)
                }

            # Filter players by club and other criteria
            filtered_players = []
            club_series = set()  # Track all series at this club

            for player in all_players:
                # Only include players from the same club as the user
                if player['Club'] == user_club:
                    club_series.add(player['Series'])
                    
                    try:
                        pti_value = float(player['PTI'])
                    except (ValueError, TypeError):
                        continue

                    # Apply filters
                    if series_filter and player['Series'] != series_filter:
                        continue
                    
                    if first_name_filter and first_name_filter not in player['First Name'].lower():
                        continue
                        
                    if last_name_filter and last_name_filter not in player['Last Name'].lower():
                        continue
                        
                    if pti_min is not None and pti_value < pti_min:
                        continue
                        
                    if pti_max is not None and pti_value > pti_max:
                        continue

                    # Add player to results
                    player_name = f"{player['First Name']} {player['Last Name']}"
                    filtered_players.append({
                        'name': player_name,
                        'firstName': player['First Name'],
                        'lastName': player['Last Name'],
                        'series': player['Series'],
                        'pti': player['PTI'],
                        'wins': player['Wins'],
                        'losses': player['Losses'],
                        'winRate': player['Win %']
                    })

            # Sort players by PTI (ascending - lower PTI is better)
            filtered_players.sort(key=lambda x: float(x['pti']))

            print(f"Found {len(filtered_players)} players at {user_club}")
            print(f"Available series: {sorted(club_series)}")
            print(f"PTI range (from all players): {pti_range}")
            print("=== END DEBUG ===\n")

            return jsonify({
                'players': filtered_players,
                'available_series': sorted(club_series, key=lambda x: int(x.split()[-1]) if x.split()[-1].isdigit() else 999),
                'pti_range': pti_range
            })

        except Exception as e:
            print(f"\nERROR getting club players: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return jsonify({'error': str(e)}), 500 