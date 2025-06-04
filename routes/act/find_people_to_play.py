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

    @app.route('/api/debug-club-data')
    @login_required
    def debug_club_data():
        """Debug endpoint to show user club and available clubs in players.json"""
        try:
            user_club = session['user'].get('club')
            
            # Load player data
            players_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'players.json')
            with open(players_path, 'r') as f:
                all_players = json.load(f)
            
            # Get all unique clubs and series
            clubs_in_data = set()
            chicago_6_clubs = set()
            for player in all_players:
                clubs_in_data.add(player['Club'])
                if player['Series'] == 'Chicago 6':
                    chicago_6_clubs.add(player['Club'])
            
            return jsonify({
                'user_club_in_session': user_club,
                'all_clubs_in_players_json': sorted(list(clubs_in_data)),
                'chicago_6_clubs': sorted(list(chicago_6_clubs)),
                'session_user': session['user']
            })
        except Exception as e:
            print(f"Debug endpoint error: {str(e)}")
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
            print(f"User club: '{user_club}'")
            print(f"User club type: {type(user_club)}")
            print(f"Filters - Series: {series_filter}, First: {first_name_filter}, Last: {last_name_filter}, PTI: {pti_min}-{pti_max}")

            # Load player data
            players_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'players.json')
            with open(players_path, 'r') as f:
                all_players = json.load(f)

            # Debug: Show unique clubs in data and check for Chicago 6
            clubs_in_data = set()
            chicago_6_count = 0
            user_club_count = 0
            for player in all_players:
                clubs_in_data.add(player['Club'])
                if player['Series'] == 'Chicago 6':
                    chicago_6_count += 1
                if player['Club'] == user_club:
                    user_club_count += 1
            
            print(f"Total players in file: {len(all_players)}")
            print(f"Chicago 6 players in file: {chicago_6_count}")
            print(f"Players with user's club '{user_club}': {user_club_count}")
            print(f"All clubs in data: {sorted(list(clubs_in_data))}")

            # Load real contact information from CSV
            csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'club_directories', 'directory_tennaqua.csv')
            contact_info = {}
            
            if os.path.exists(csv_path):
                import csv
                with open(csv_path, 'r') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        if row['First'] and row['Last Name']:  # Skip empty rows
                            full_name = f"{row['First'].strip()} {row['Last Name'].strip()}"
                            contact_info[full_name.lower()] = {
                                'phone': row['Phone'].strip(),
                                'email': row['Email'].strip()
                            }
                print(f"Loaded {len(contact_info)} contact records from CSV")
            else:
                print(f"CSV file not found at: {csv_path}")

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
                # Debug: Log first few club comparisons
                if len(filtered_players) < 3:
                    print(f"Comparing: player['Club']='{player['Club']}' == user_club='{user_club}' ? {player['Club'] == user_club}")
                
                # Only include players from the same club as the user
                if player['Club'] == user_club:
                    club_series.add(player['Series'])
                    
                    # Handle PTI values - allow "N/A" and non-numeric values
                    try:
                        pti_value = float(player['PTI'])
                    except (ValueError, TypeError):
                        # For "N/A" or non-numeric PTI, set a default value that won't be filtered out
                        pti_value = 50.0  # Use middle value so it passes most PTI filters
                        print(f"Player {player['First Name']} {player['Last Name']} has non-numeric PTI '{player['PTI']}', using default value 50.0")

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

                    # Get real contact info from CSV
                    player_name = f"{player['First Name']} {player['Last Name']}"
                    player_contact = contact_info.get(player_name.lower(), {})
                    
                    # Add player to results
                    filtered_players.append({
                        'name': player_name,
                        'firstName': player['First Name'],
                        'lastName': player['Last Name'],
                        'series': player['Series'],
                        'pti': player['PTI'],  # Keep original PTI value for display
                        'wins': player['Wins'],
                        'losses': player['Losses'],
                        'winRate': player['Win %'],
                        'phone': player_contact.get('phone', ''),
                        'email': player_contact.get('email', '')
                    })

            # Sort players by PTI (ascending - lower PTI is better)
            # Handle "N/A" PTI values by treating them as a high number for sorting
            def get_sort_pti(player):
                try:
                    return float(player['pti'])
                except (ValueError, TypeError):
                    return 999.0  # Put "N/A" values at the end
            
            filtered_players.sort(key=get_sort_pti)

            print(f"Found {len(filtered_players)} players at {user_club}")
            print(f"Available series: {sorted(club_series)}")
            print(f"PTI range (from all players): {pti_range}")
            print("=== END DEBUG ===\n")

            return jsonify({
                'players': filtered_players,
                'available_series': sorted(club_series, key=lambda x: int(x.split()[-1]) if x.split()[-1].isdigit() else 999),
                'pti_range': pti_range,
                'debug': {
                    'user_club': user_club,
                    'total_players_in_file': len(all_players),
                    'players_at_user_club': user_club_count,
                    'all_clubs': sorted(list(clubs_in_data))
                }
            })

        except Exception as e:
            print(f"\nERROR getting club players: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return jsonify({'error': str(e)}), 500 