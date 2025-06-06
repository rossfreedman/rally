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

    @app.route('/api/debug-session')
    def debug_session():
        """Debug endpoint to show session data"""
        try:
            return jsonify({
                'session_has_user': 'user' in session,
                'session_user': session.get('user', 'No user in session'),
                'session_keys': list(session.keys()) if session else 'No session'
            })
        except Exception as e:
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
            # Get filter parameters
            series_filter = request.args.get('series', '').strip()
            first_name_filter = request.args.get('first_name', '').strip().lower()
            last_name_filter = request.args.get('last_name', '').strip().lower()
            pti_min = request.args.get('pti_min', type=float)
            pti_max = request.args.get('pti_max', type=float)

            # Use the mobile service to get club players data
            from app.services.mobile_service import get_club_players_data
            
            result = get_club_players_data(
                user=session['user'],
                series_filter=series_filter if series_filter else None,
                first_name_filter=first_name_filter if first_name_filter else None,
                last_name_filter=last_name_filter if last_name_filter else None,
                pti_min=pti_min,
                pti_max=pti_max
            )
            
            return jsonify(result)

        except Exception as e:
            print(f"\nERROR getting club players: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return jsonify({'error': str(e)}), 500

    @app.route('/api/test-tennaqua-players')
    def test_tennaqua_players():
        """Test endpoint to simulate what the logged-in user should see at Tennaqua"""
        try:
            # Simulate user session data for Ross at Tennaqua, Chicago 22
            user_club = "Tennaqua"
            
            print(f"\n=== TESTING TENNAQUA PLAYERS ===")
            print(f"Simulating user club: '{user_club}'")
            
            # Load player data
            players_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'players.json')
            with open(players_path, 'r') as f:
                all_players = json.load(f)

            # Debug: Show unique clubs in data and check for Tennaqua
            clubs_in_data = set()
            tennaqua_count = 0
            for player in all_players:
                clubs_in_data.add(player['Club'])
                if player['Club'] == user_club:
                    tennaqua_count += 1
            
            print(f"Total players in file: {len(all_players)}")
            print(f"Players with club '{user_club}': {tennaqua_count}")
            print(f"All clubs in data: {sorted(list(clubs_in_data))}")
            
            # Show some specific club comparisons for debugging
            user_club_lower = user_club.lower().strip()
            exact_matches = [club for club in clubs_in_data if club.lower().strip() == user_club_lower]
            partial_matches = [club for club in clubs_in_data if user_club_lower in club.lower() or club.lower() in user_club_lower]
            
            print(f"Exact club matches for '{user_club}': {exact_matches}")
            print(f"Partial club matches for '{user_club}': {partial_matches}")
            print(f"User club normalized: '{user_club_lower}'")

            # Filter players by club using the same logic as the real route
            filtered_players = []
            club_series = set()

            # Debug: Show club matching attempts
            print(f"Attempting to match user club '{user_club}' (normalized: '{user_club_lower}')")
            
            for player in all_players:
                player_club = player['Club'].strip()
                player_club_lower = player_club.lower()
                
                # Debug: Log first few club comparisons
                if len(filtered_players) < 3:
                    print(f"Comparing: player['Club']='{player_club}' (normalized: '{player_club_lower}') == user_club='{user_club}' (normalized: '{user_club_lower}') ? {player_club_lower == user_club_lower}")
                
                # Try multiple matching strategies:
                club_match = (
                    player_club_lower == user_club_lower or
                    user_club_lower in player_club_lower or
                    player_club_lower in user_club_lower
                )
                
                if club_match:
                    club_series.add(player['Series'])
                    
                    # Add player to results (simplified version)
                    filtered_players.append({
                        'name': f"{player['First Name']} {player['Last Name']}",
                        'firstName': player['First Name'],
                        'lastName': player['Last Name'],
                        'series': player['Series'],
                        'pti': player['PTI'],
                        'wins': player['Wins'],
                        'losses': player['Losses'],
                        'winRate': player['Win %']
                    })

            print(f"Found {len(filtered_players)} players at {user_club}")
            print(f"Available series: {sorted(club_series)}")
            print("=== END TEST ===\n")

            return jsonify({
                'total_players_found': len(filtered_players),
                'available_series': sorted(club_series),
                'first_10_players': filtered_players[:10],
                'user_club': user_club,
                'debug_info': {
                    'exact_matches': exact_matches,
                    'partial_matches': partial_matches,
                    'total_in_file': len(all_players)
                }
            })

        except Exception as e:
            print(f"\nERROR in test: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return jsonify({'error': str(e)}), 500

    @app.route('/api/test-club-players/<club_name>')
    def test_club_players(club_name):
        """Test endpoint to check players for a specific club"""
        try:
            # Load player data
            players_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'players.json')
            with open(players_path, 'r') as f:
                all_players = json.load(f)
            
            # Count players at this club
            club_players = [p for p in all_players if p['Club'] == club_name]
            
            return jsonify({
                'club_name': club_name,
                'players_found': len(club_players),
                'first_5_players': club_players[:5] if club_players else [],
                'all_unique_clubs': sorted(list(set(p['Club'] for p in all_players)))
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500 